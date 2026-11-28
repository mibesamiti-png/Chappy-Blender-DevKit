"""R10: independent CGAL, conditional routing invariants, timing and gate."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from statistics import mean, median

from cbdk_geometry import Mesh
from cycles.r7.evaluate import assess
from cycles.r10.fixtures import cases

ROOT = Path(__file__).resolve().parents[2]
METHODS = ("conditional_r10", "tapered_r8", "flipped_r9", "native_3_linear")


def evaluate(raw):
    if raw.get("cycle") != "R10" or not raw.get("synthetic_only") or not raw.get("scene_preserved"):
        raise ValueError("R10 requires synthetic Blender provenance/cleanup")
    fixtures = {case["name"]: case for case in cases()}
    needed = {(name, method) for name in fixtures for method in METHODS}
    seen = set()
    rows = []
    for case in raw["cases"]:
        name, method = case["name"], case["method"]
        if (name, method) not in needed or (name, method) in seen:
            raise ValueError("unknown or repeated R10 case/method")
        seen.add((name, method))
        result = {key: value for key, value in case.items() if key not in ("vertices", "faces")}
        if case["generation_status"] != "generated":
            result["status"] = "generation_error"
        else:
            try:
                result.update(assess(Mesh(case["vertices"], case["faces"]), fixtures[name]))
            except Exception as error:
                result.update(status="oracle_unavailable",
                              reason=type(error).__name__ + ": " + str(error))
        rows.append(result)
        print("R10_RESULT", json.dumps({
            key: value for key, value in result.items()
            if key in ("name", "split", "method", "path", "status", "reason",
                       "cgal_intersection_pairs", "median_seconds")
        }), flush=True)
    if seen != needed:
        raise ValueError("missing R10 case/method combinations")

    by = {(x["name"], x["method"]): x for x in rows}
    raw_by = {(x["name"], x["method"]): x for x in raw["cases"]}
    summary = {}
    for split in ("development", "holdout"):
        summary[split] = {}
        for method in METHODS:
            sample = [x for x in rows if x["split"] == split and x["method"] == method]
            summary[split][method] = {
                "passed": sum(x["status"] == "passed" for x in sample),
                "failed": sum(x["status"] == "failed" for x in sample),
                "unavailable": sum(x["status"] not in ("passed", "failed") for x in sample),
                "total": len(sample),
                "cgal_hits": sum(x.get("cgal_intersection_pairs", 0) for x in sample),
            }
    dev = [x["name"] for x in fixtures.values() if x["split"] == "development"]
    holdout = [x["name"] for x in fixtures.values() if x["split"] == "holdout"]

    # Oracle outcomes cannot be invented: exact names must be present.
    previous_successes = [name for name in dev if by[(name, "flipped_r9")]["status"] == "passed"]
    prior_outcome_match = all(
        by[(name, "conditional_r10")]["status"] ==
        by[(name, "flipped_r9")]["status"] for name in dev)
    prior_success_preserved = all(
        by[(name, "conditional_r10")]["status"] == "passed" for name in previous_successes)
    rescued_known = by[("r8_slender_opposite", "conditional_r10")]["status"] == "passed"
    newly_rescued = [
        name for name in holdout
        if by[(name, "tapered_r8")]["status"] == "failed"
        and by[(name, "conditional_r10")]["status"] == "passed"
    ]
    regressions = [
        name for name in holdout
        if by[(name, "tapered_r8")]["status"] == "passed"
        and by[(name, "conditional_r10")]["status"] != "passed"
    ]

    fast, repair = [], []
    invariant_violations = []
    for name in fixtures:
        r10 = raw_by[(name, "conditional_r10")]
        r8 = raw_by[(name, "tapered_r8")]
        r9 = raw_by[(name, "flipped_r9")]
        if any(x.get("generation_status") != "generated" for x in (r10, r8, r9)):
            invariant_violations.append((name, "generation unavailable"))
            continue
        q = by[(name, "tapered_r8")]["quality"]["min_triangle_quality"]
        expected_path = "fast" if q >= .1 else "repair"
        actual = r10.get("path")
        target = r8 if expected_path == "fast" else r9
        if actual != expected_path:
            invariant_violations.append((name, "wrong dispatch path"))
        if r10["vertices"] != r8["vertices"] or len(r10["faces"]) != len(r8["faces"]):
            invariant_violations.append((name, "vertex or triangle count changed"))
        if r10["faces"] != target["faces"] or r10["vertices"] != target["vertices"]:
            invariant_violations.append((name, "output differs from exact frozen baseline"))
        if name in holdout:
            if expected_path == "fast":
                fast.append(name)
            else:
                repair.append(name)

    all_comparable = all(r["status"] in ("passed", "failed") for r in rows)
    safe = all(
        r["status"] in ("passed", "failed") and
        r.get("cgal_intersection_pairs") == 0 and
        r.get("topology_valid") and
        r.get("original_vertices_preserved") and
        r.get("original_boundary_edges_preserved")
        for r in rows if r["method"] == "conditional_r10")

    def ratios(names):
        if not names:
            return {"median_r10_seconds": None, "median_r9_seconds": None,
                    "r10_over_r9": None}
        a = [by[(name, "conditional_r10")]["median_seconds"] for name in names]
        b = [by[(name, "flipped_r9")]["median_seconds"] for name in names]
        return {"median_r10_seconds": median(a),
                "median_r9_seconds": median(b),
                "r10_over_r9": median(a) / median(b)}

    fast_stats = ratios(fast)
    all_r10_mean = mean(by[(name, "conditional_r10")]["median_seconds"] for name in holdout)
    all_r9_mean = mean(by[(name, "flipped_r9")]["median_seconds"] for name in holdout)
    all_ratio = all_r10_mean / all_r9_mean
    h = summary["holdout"]
    holdout_pass_gate = (h["conditional_r10"]["passed"] >= 5
                         and h["conditional_r10"]["passed"] >= h["tapered_r8"]["passed"]
                         and len(newly_rescued) >= 1 and len(regressions) == 0)
    speed_gate = (len(fast) >= 3 and fast_stats["r10_over_r9"] <= .65 and
                  all_ratio <= .8)
    gate = bool(all_comparable and safe and not invariant_violations and
                prior_outcome_match and prior_success_preserved and rescued_known and
                holdout_pass_gate and speed_gate)
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for path in ("cbdk_geometry/quality_router.py", "cycles/r10/fixtures.py",
                           "cycles/r10/blender_run.py", "cycles/r10/evaluate.py")}
    return dict(
        cycle="R10", synthetic_only=True, blender=raw["blender"],
        build_hash=raw["build_hash"], cgal=version("cgal"),
        generator_source_sha256=raw["source_sha256"], source_sha256=hashes,
        cases=rows, summary=summary, old_r9_passes_preserved=prior_success_preserved,
        old_r9_outcomes_identical=prior_outcome_match,
        old_reverse_slender_rescued=rescued_known,
        new_holdout_rescued_from_r8=newly_rescued, holdout_regressions=regressions,
        fast_cases=fast, repair_cases=repair,
        timing_fast=fast_stats, timing_all_mean_ratio_r10_over_r9=all_ratio,
        invariant_violations=invariant_violations,
        all_independent_oracles_available=all_comparable,
        all_r10_outputs_topology_cgal_safe=safe,
        holdout_gate_met=bool(holdout_pass_gate),
        speed_gate_met=bool(speed_gate),
        research_gate_met=gate, approved=False,
        decision=("inconclusive_oracle" if not all_comparable else
                  "promising_unapproved" if gate else "not_preferred_gate_failed"),
        limitation="Synthetic author-designed XY-star-shaped and Z-separated cases only, not production/UV/normal safe")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    options = p.parse_args()
    source = Path(options.input)
    result = evaluate(json.loads(source.read_text()))
    result["raw_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    target = Path(options.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x") as file:
        json.dump(result, file, indent=2)
    print("R10_SUMMARY", json.dumps({
        k: result[k] for k in (
            "summary", "fast_cases", "repair_cases", "new_holdout_rescued_from_r8",
            "holdout_regressions", "timing_fast", "timing_all_mean_ratio_r10_over_r9",
            "old_r9_outcomes_identical", "invariant_violations", "speed_gate_met",
            "research_gate_met", "decision")
    }), flush=True)
    if result["decision"] == "inconclusive_oracle":
        raise SystemExit("R10 independent comparison had missing oracles/results")
