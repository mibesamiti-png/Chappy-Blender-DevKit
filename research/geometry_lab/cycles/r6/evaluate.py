"""R6: independent CGAL + R4/R5 analytic shape evaluation of native Blender output.

This is separate from Blender generation to keep CGAL out of its Python runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from importlib.metadata import version

import numpy as np
from cbdk_geometry import Mesh
from cycles.r5.run import _assess
from cycles.r6.fixtures import cases

ROOT = Path(__file__).resolve().parents[2]
METHODS = ("r5_radial", "native_0_path", "native_3_linear",
           "native_3_path", "native_3_surface")


def evaluate(raw):
    if not raw.get("synthetic_only") or raw.get("scene_preserved") is not True:
        raise ValueError("missing synthetic provenance or scene cleanup evidence")
    lookup = {case["name"]: case for case in cases()}
    expected = {(name, method) for name in lookup for method in METHODS}
    seen = set()
    rows = []
    for item in raw["cases"]:
        name, method = item["name"], item["method"]
        if (name, method) not in expected or (name, method) in seen:
            raise ValueError("unknown or duplicate R6 case/method")
        seen.add((name, method))
        row = {key: value for key, value in item.items() if key not in ("vertices", "faces")}
        if item["generation_status"] != "generated":
            row["status"] = "generation_error"
        else:
            try:
                mesh = Mesh(item["vertices"], item["faces"])
                row.update(_assess(mesh, lookup[name]))
            except Exception as exc:
                # Treat independent oracle failure as unverified, NEVER a clean mesh.
                row.update(status="oracle_unavailable",
                           reason=type(exc).__name__ + ": " + str(exc))
        rows.append(row)
        print("R6_RESULT", json.dumps(
            {k: v for k, v in row.items()
             if k in ("name", "split", "method", "status", "reason", "sampled_loft_rms", "sampled_loft_max", "intersection_pairs")},
            ensure_ascii=False), flush=True)
    if seen != expected:
        raise ValueError("missing R6 combinations: " + str(sorted(expected-seen)))

    splits = ["seen", "holdout"]
    summary = {
        split: {
            method: dict(passed=sum(r["status"] == "passed" for r in rows
                                    if r["split"] == split and r["method"] == method),
                         failed=sum(r["status"] == "failed" for r in rows
                                    if r["split"] == split and r["method"] == method),
                         unavailable=sum(r["status"] not in ("passed", "failed") for r in rows
                                         if r["split"] == split and r["method"] == method),
                         total=sum(r["split"] == split and r["method"] == method for r in rows))
            for method in METHODS
        } for split in splits
    }
    fresh = summary["holdout"]
    best_native = max(fresh[m]["passed"] for m in METHODS if m.startswith("native_3_"))
    has_unverified = any(r["status"] not in ("passed", "failed") for r in rows)
    delta = fresh["r5_radial"]["passed"] - best_native
    conclusion = ("comparison_inconclusive" if has_unverified
                  else "r5_native_advantage" if delta >= 1
                  else "no_r5_advantage_over_standard")
    hashes = {
        filename: hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        for filename in ("cycles/r6/fixtures.py", "cycles/r6/blender_run.py",
                         "cycles/r6/evaluate.py", "cbdk_geometry/radial_loft.py")
    }
    return {
        "cycle": "R6", "synthetic_only": True, "blender": raw["blender"],
        "build_hash": raw["build_hash"], "numpy_blender": raw["numpy_blender"],
        "cgal": version("cgal"), "method_order": list(METHODS),
        "source_sha256": hashes, "generator_source_sha256": raw["source_sha256"],
        "cases": rows, "summary": summary, "best_single_3cut_native": best_native,
        "fresh_holdout_delta_vs_best_native": delta, "conclusion": conclusion,
        "caveats": [
            "Native includes edit-mode context+mesh construction+triangulation; R5 is detached Python mesh",
            "Blender 4.4.3 only; no real objects, UV, normals, or UI time comparison",
            "R6 freshly authored synthetic holdout, not third-party blind",
            "Original R4/R5 centroid oracle ignores upper-ring phase for lobed analytic shape",
        ],
        "approved": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_path = Path(args.input)
    raw = json.loads(input_path.read_text())
    result = evaluate(raw)
    result["input_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x") as dest:
        json.dump(result, dest, indent=2, ensure_ascii=False)
    print("R6_SUMMARY", json.dumps({
        "summary": result["summary"],
        "best_single_3cut_native": result["best_single_3cut_native"],
        "delta": result["fresh_holdout_delta_vs_best_native"],
        "conclusion": result["conclusion"]
    }, ensure_ascii=False), flush=True)
    if result["conclusion"] == "comparison_inconclusive":
        raise SystemExit("R6 independent comparison had unverified cases; see artifact")
