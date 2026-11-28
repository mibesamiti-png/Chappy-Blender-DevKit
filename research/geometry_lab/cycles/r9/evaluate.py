"""R9 independent CGAL oracle + frozen R7/R8 analytic acceptance gate."""
import argparse
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
from cbdk_geometry import Mesh
from cycles.r7.evaluate import assess
from cycles.r9.fixtures import cases

ROOT=Path(__file__).resolve().parents[2]
METHODS=("flipped_r9","tapered_r8","native_3_linear")


def evaluate(raw):
    if raw.get("cycle")!="R9" or not raw.get("synthetic_only") or not raw.get("scene_preserved"):
        raise ValueError("R9 synthetic-only/cleanup provenance is required")
    fixtures={c["name"]:c for c in cases()}
    expected={(name,m) for name in fixtures for m in METHODS}
    seen=set()
    rows=[]
    for item in raw["cases"]:
        name,method=item["name"],item["method"]
        if (name,method) not in expected or (name,method) in seen:
            raise ValueError("unexpected or duplicate R9 case")
        seen.add((name,method))
        r={k:v for k,v in item.items() if k not in ("vertices","faces")}
        if item["generation_status"]!="generated":
            r["status"]="generation_error"
        else:
            try:
                mesh=Mesh(item["vertices"],item["faces"])
                r.update(assess(mesh,fixtures[name]))
            except Exception as exc:
                r.update(status="oracle_unavailable",reason=type(exc).__name__+": "+str(exc))
        rows.append(r)
        print("R9_RESULT",json.dumps({k:v for k,v in r.items() if k in
            ("name","split","method","status","reason","analytic_3d_loft_rms",
             "cgal_intersection_pairs")}),flush=True)
    if seen!=expected:
        raise ValueError("missing R9 method/case pairs")
    by={(r["name"],r["method"]):r for r in rows}
    summary={}
    for split in ("development","holdout"):
        summary[split]={}
        for method in METHODS:
            group=[r for r in rows if r["split"]==split and r["method"]==method]
            summary[split][method]=dict(
                passed=sum(r["status"]=="passed" for r in group),
                failed=sum(r["status"]=="failed" for r in group),
                unavailable=sum(r["status"] not in ("passed","failed") for r in group),
                total=len(group),
                cgal_crossings=sum(r.get("cgal_intersection_pairs",0) for r in group))
    prior_successes=[c["name"] for c in fixtures.values()
                     if c["split"]=="development"
                     and by[(c["name"],"tapered_r8")]["status"]=="passed"]
    no_regression=all(by[(name,"flipped_r9")]["status"]=="passed"
                      for name in prior_successes)
    prior_reverse=by[("r8_slender_opposite","flipped_r9")]
    reverse_rescued=(prior_reverse["status"]=="passed" and
                     prior_reverse["quality"]["min_triangle_quality"]>=.1)
    gains=[]
    for case in fixtures.values():
        if case["split"]!="holdout":
            continue
        new=by[(case["name"],"flipped_r9")]
        old=by[(case["name"],"tapered_r8")]
        if new["status"] in ("passed","failed") and old["status"] in ("passed","failed"):
            gain=(new["quality"]["min_triangle_quality"]-
                  old["quality"]["min_triangle_quality"])
            if gain >= .02:
                gains.append(case["name"])
    errors=any(r["status"] not in ("passed","failed") for r in rows)
    safe=all(r["status"] in ("passed","failed") and
             r["cgal_intersection_pairs"]==0 and
             r["topology_valid"] and
             r["original_vertices_preserved"] and
             r["original_boundary_edges_preserved"]
             for r in rows if r["method"]=="flipped_r9")
    # Exact face/vertex count and coordinate equality versus R8 per case:
    # this compares the actual generator outputs; not merely tool metadata.
    same_geometry_budget=True
    for case in fixtures.values():
        name=case["name"]
        a=next(x for x in raw["cases"] if x["name"]==name and x["method"]=="flipped_r9")
        b=next(x for x in raw["cases"] if x["name"]==name and x["method"]=="tapered_r8")
        if a.get("generation_status")!="generated" or b.get("generation_status")!="generated":
            same_geometry_budget=False
        elif a["vertices"]!=b["vertices"] or len(a["faces"])!=len(b["faces"]):
            same_geometry_budget=False
    h=summary["holdout"]
    holdout_pass=(h["flipped_r9"]["passed"]>=4 and
                  h["flipped_r9"]["passed"]>=h["tapered_r8"]["passed"])
    gate=bool(not errors and safe and same_geometry_budget and no_regression and
              reverse_rescued and holdout_pass and len(gains)>=2)
    result=dict(cycle="R9",synthetic_only=True,blender=raw["blender"],
                build_hash=raw["build_hash"],cgal=version("cgal"),
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                    ("cbdk_geometry/flip_loft.py","cycles/r9/fixtures.py",
                     "cycles/r9/blender_run.py","cycles/r9/evaluate.py")},
                generator_source_sha256=raw["source_sha256"],
                cases=rows,summary=summary,old_reverse_slender_rescued=bool(reverse_rescued),
                old_r8_passes_preserved=bool(no_regression),
                new_min_quality_improved_ge_002=gains,
                exact_r8_vertex_coordinates_and_triangle_counts=bool(same_geometry_budget),
                all_r9_outputs_cgal_topology_clean=bool(safe),
                research_gate_met=gate,approved=False,
                decision=("comparison_inconclusive" if errors else
                          "promising_unapproved" if gate else "not_adopted_gate_failed"),
                caveat="Researcher-authored synthetic references only; all true 3D surface and UV claims unverified")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    src=Path(args.input)
    result=evaluate(json.loads(src.read_text()))
    result["raw_sha256"]=hashlib.sha256(src.read_bytes()).hexdigest()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f:json.dump(result,f,indent=2)
    print("R9_SUMMARY",json.dumps({key:result[key] for key in
        ("summary","old_reverse_slender_rescued","old_r8_passes_preserved",
         "new_min_quality_improved_ge_002","exact_r8_vertex_coordinates_and_triangle_counts",
         "all_r9_outputs_cgal_topology_clean","research_gate_met","decision")}),flush=True)
    if result["decision"]=="comparison_inconclusive":
        raise SystemExit("R9 oracle incomplete: do not mark research passing")
