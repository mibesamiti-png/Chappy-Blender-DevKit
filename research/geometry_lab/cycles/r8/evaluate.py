"""R8 independent CGAL/shape gate, using unchanged R7 analytic assessor."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from cbdk_geometry import Mesh
from cycles.r7.evaluate import assess
from cycles.r8.fixtures import cases

ROOT=Path(__file__).resolve().parents[2]
METHODS=("tapered_r8","warped_r7","native_3_linear")


def evaluate(raw):
    if raw.get("cycle")!="R8" or not raw.get("synthetic_only") or not raw.get("scene_preserved"):
        raise ValueError("R8 synthetic provenance and cleanup required")
    fixtures={x["name"]:x for x in cases()}
    needed={(name,method) for name in fixtures for method in METHODS}
    observed=set()
    rows=[]
    for rec in raw["cases"]:
        name,method=rec["name"],rec["method"]
        if (name,method) not in needed or (name,method) in observed:
            raise ValueError("unknown or repeated R8 case/method")
        observed.add((name,method))
        r={k:v for k,v in rec.items() if k not in ("vertices","faces")}
        if rec["generation_status"]!="generated":
            r["status"]="generation_error"
        else:
            try:
                m=Mesh(rec["vertices"],rec["faces"])
                r.update(assess(m,fixtures[name]))
            except Exception as exc:
                # Oracle failures remain unverified; no silent success.
                r.update(status="oracle_unavailable",
                         reason=type(exc).__name__+": "+str(exc))
        rows.append(r)
        print("R8_RESULT",json.dumps({k:v for k,v in r.items()
              if k in ("name","method","split","status","reason",
                       "analytic_3d_loft_rms","cgal_intersection_pairs")}),flush=True)
    if observed!=needed:raise ValueError("missing R8 combinations")
    summary={}
    for split in ("development","holdout"):
        summary[split]={}
        for method in METHODS:
            subset=[x for x in rows if x["split"]==split and x["method"]==method]
            summary[split][method]=dict(
                passed=sum(x["status"]=="passed" for x in subset),
                failed=sum(x["status"]=="failed" for x in subset),
                unavailable=sum(x["status"] not in ("passed","failed") for x in subset),
                total=len(subset),
                crossings=sum(x.get("cgal_intersection_pairs",0) for x in subset))
    bycase={(x["name"],x["method"]):x for x in rows}
    prior_wins=[c["name"] for c in fixtures.values()
                if c["split"]=="development" and c["name"]!="r7_slender_offset"
                and bycase[(c["name"],"warped_r7")]["status"]=="passed"]
    no_regress=all(bycase[(name,"tapered_r8")]["status"]=="passed" for name in prior_wins)
    seen=bycase[("r7_slender_offset","tapered_r8")]
    rescued=(seen["status"]=="passed" and seen["quality"]["min_triangle_quality"]>=.1)
    improving=[]
    for name,c in fixtures.items():
        if c["split"]!="holdout":continue
        after=bycase[(name,"tapered_r8")]
        before=bycase[(name,"warped_r7")]
        if after["status"] in ("passed","failed") and before["status"] in ("passed","failed"):
            delta=(after["quality"]["min_triangle_quality"]-
                   before["quality"]["min_triangle_quality"])
            if delta>=.015: improving.append(name)
    unverified=any(x["status"] not in ("passed","failed") for x in rows)
    safe=all(x.get("cgal_intersection_pairs")==0 and x.get("topology_valid")
             and x.get("original_boundary_edges_preserved")
             for x in rows if x["method"]=="tapered_r8" and x["status"] in ("passed","failed"))
    h=summary["holdout"]
    count_ok=h["tapered_r8"]["passed"]>=max(4,h["warped_r7"]["passed"])
    gate=not unverified and safe and no_regress and rescued and count_ok and len(improving)>=2
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in ("cbdk_geometry/tapered_loft.py","cycles/r8/fixtures.py",
                      "cycles/r8/blender_run.py","cycles/r8/evaluate.py")}
    return dict(cycle="R8",synthetic_only=True,blender=raw["blender"],cgal=version("cgal"),
                source_sha256=hashes,generator_source_sha256=raw["source_sha256"],
                cases=rows,summary=summary,
                old_slender_rescued=bool(rescued),
                original_r7_passes_preserved=bool(no_regress),
                holdout_cases_with_min_quality_improvement_ge_0015=improving,
                holdout_not_worse_than_frozen_r7=bool(count_ok),
                r8_generated_meshes_safe=bool(safe),
                research_gate_met=bool(gate),approved=False,
                conclusion="promising_specialized_density_taper" if gate
                  else ("inconclusive_oracle" if unverified else "not_adopted_gate_failed"),
                caveat="Researcher-authored synthetic shape target; no user model/UV/normal or arbitrary orientation")
                

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    path=Path(args.input)
    result=evaluate(json.loads(path.read_text()))
    result["input_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f:json.dump(result,f,indent=2)
    print("R8_SUMMARY",json.dumps({k:result[k] for k in
        ("summary","old_slender_rescued","original_r7_passes_preserved",
         "holdout_cases_with_min_quality_improvement_ge_0015",
         "research_gate_met","conclusion")}),flush=True)
    if result["conclusion"]=="inconclusive_oracle":
        raise SystemExit("R8 oracle/generator unavailable: comparison not validated")
