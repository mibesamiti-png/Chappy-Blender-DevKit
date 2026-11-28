"""R13 independent Python3.12 UV seam metrics + external CGAL on full Blender assembly."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
import numpy as np
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from cycles.r7.evaluate import assess
from cycles.r12.evaluate import independent_uv_metrics
from cycles.r13.fixtures import cases

ROOT=Path(__file__).resolve().parents[2]
ARMS=("r13_seam_optimized","r12_nearest_chart")


def evaluate(raw,development_only=False):
    if raw.get("cycle")!="R13" or not raw.get("synthetic_only") or raw.get("approved"):
        raise ValueError("R13 provenance invalid")
    fixtures={(x["name"],x["uv_mode"]):x for x in cases()
              if not development_only or x["split"]=="development"}
    expected={(name,mode,arm) for name,mode in fixtures for arm in ARMS}
    found=set()
    rows=[]
    raw_by={}
    for item in raw["cases"]:
        key=(item["case"],item["uv_mode"],item["arm"])
        if key not in expected or key in found:
            raise ValueError("unknown/repeated R13 method or fixture")
        found.add(key)
        raw_by[key]=item
        r={k:v for k,v in item.items() if k not in
           ("boundary_pair_uv_samples","bridge_corner_uvs","bridge_vertex_base_uv",
            "strip_vertices","strip_faces","joined_vertices","joined_triangles")}
        if item["status"]!="generated":
            r["audit_status"]="generation_error"
        else:
            try:
                measure=independent_uv_metrics(item)
                strip=Mesh(item["strip_vertices"],item["strip_faces"])
                assembled=Mesh(item["joined_vertices"],item["joined_triangles"])
                strip_hits=mesh_hits(strip)
                assembled_hits=mesh_hits(assembled)
                geom=assess(strip,fixtures[(item["case"],item["uv_mode"])])
                core=(item["original_source_signature_unchanged"]
                      and item["source_xyz_preserved"] and item["bridge_material_2"]
                      and item["bridge_face_count"]==item["expected_bridge_face_count"]
                      and item["source_to_bridge_shared_edges"]==item["expected_shared_edges"]
                      and item["outer_boundary_edges"]==item["expected_outer_boundary_edges"]
                      and item["nonmanifold_edges"]==0 and item["scene_restored"]
                      and item["bridge_uv_finite"]
                      and geom["status"]=="passed"
                      and geom["original_boundary_edges_preserved"]
                      and len(strip_hits)==0 and len(assembled_hits)==0
                      and measure["independent_signed_uv_area_max_error"]<=1e-5
                      and measure["independent_boundary_max_uv_error"]<=1e-5
                      and abs(measure["independent_boundary_max_uv_error"]-
                              item["source_boundary_max_uv_error"])<=1e-5
                      and measure["independent_seam_edges"]==item["internal_seam_edges"]
                      and measure["independent_interior_edges"]==item["internal_edges"]
                      and abs(measure["independent_seam_length"]-
                              item["internal_seam_length"])<=1e-5)
                r.update(measure,strip_cgal_pairs=len(strip_hits),
                         joined_cgal_pairs=len(assembled_hits),
                         strip_quality_passed=geom["status"]=="passed",
                         core_integrity=bool(core))
                r["audit_status"]="passed" if core else "failed"
            except Exception as exc:
                r.update(audit_status="oracle_unavailable",
                         reason=type(exc).__name__+": "+str(exc))
        rows.append(r)
        print("R13_RESULT",json.dumps({k:r.get(k) for k in
            ("case","split","uv_mode","arm","audit_status","reason",
             "independent_seam_edges","independent_seam_length",
             "independent_boundary_max_uv_error","joined_cgal_pairs")}),flush=True)
    if found!=expected:
        raise ValueError("R13 missing frozen cases or arms")
    by={(r["case"],r["uv_mode"],r["arm"]):r for r in rows}
    comparisons=[]
    invalid=[]
    fresh_noncontinuous=[]
    for name,mode in fixtures:
        new=by[(name,mode,"r13_seam_optimized")]
        old=by[(name,mode,"r12_nearest_chart")]
        a=raw_by[(name,mode,"r13_seam_optimized")]
        b=raw_by[(name,mode,"r12_nearest_chart")]
        if a.get("status")!="generated" or b.get("status")!="generated":
            invalid.append((name,"generation unavailable"))
            continue
        equal_geometry=(a["strip_vertices"]==b["strip_vertices"] and
                        a["strip_faces"]==b["strip_faces"] and
                        a["joined_vertices"]==b["joined_vertices"] and
                        a["joined_triangles"]==b["joined_triangles"])
        a_pairs=np.asarray(a["boundary_pair_uv_samples"],dtype=float)
        b_pairs=np.asarray(b["boundary_pair_uv_samples"],dtype=float)
        same_source=(a_pairs.shape==b_pairs.shape and
                     np.array_equal(a_pairs[:,0,:],b_pairs[:,0,:]))
        if not equal_geometry or not same_source:
            invalid.append((name,"geometry or original source UV differs between arms"))
        if new["audit_status"]!="passed" or old["audit_status"]!="passed":
            invalid.append((name,"independent candidate/baseline oracle failed"))
            continue
        a_count=new["independent_seam_edges"]
        b_count=old["independent_seam_edges"]
        a_len=new["independent_seam_length"]
        b_len=old["independent_seam_length"]
        c_reduction=(b_count-a_count)/(b_count or 1)
        l_reduction=(b_len-a_len)/(b_len or 1)
        no_regression=(a_count<=b_count and a_len<=b_len+1e-8)
        if not no_regression:
            invalid.append((name,"seam-count or seam-length regression"))
        if mode=="continuous":
            if a_count!=0 or b_count!=0:
                invalid.append((name,"continuous chart unexpectedly split"))
        else:
            if a_count<1 or new["independent_seam_fraction"]>.60:
                invalid.append((name,"noncontinuous seam budget failed"))
        row=dict(name=name,uv_mode=mode,split=fixtures[(name,mode)]["split"],
                 original_count=b_count,optimized_count=a_count,
                 original_length=b_len,optimized_length=a_len,
                 count_reduction=c_reduction,length_reduction=l_reduction,
                 no_regression=no_regression,
                 optimization_seconds=a.get("optimizer_info",{}).get("elapsed_seconds"))
        comparisons.append(row)
        if row["split"]=="holdout" and mode!="continuous":
            fresh_noncontinuous.append(row)
    fresh_reduced_both=[x["name"] for x in fresh_noncontinuous
                       if x["count_reduction"]>=.10 and x["length_reduction"]>=.10]
    summary={}
    for split in ("development","holdout"):
        summary[split]={}
        for arm in ARMS:
            sample=[r for r in rows if r["split"]==split and r["arm"]==arm]
            summary[split][arm]=dict(total=len(sample),
                                    passed=sum(r["audit_status"]=="passed" for r in sample),
                                    unavailable=sum(r["audit_status"] not in ("passed","failed")
                                                    for r in sample),
                                    failed=sum(r["audit_status"]=="failed" for r in sample),
                                    joined_cgal_pairs=sum(r.get("joined_cgal_pairs",0)
                                                          for r in sample))
    all_evaluated=all(r["audit_status"]=="passed" for r in rows)
    if development_only:
        gate=bool(all_evaluated and not invalid and
                  len(comparisons)==len(fixtures))
    else:
        gate=bool(all_evaluated and not invalid and
                  len(comparisons)==12 and
                  len(fresh_noncontinuous)==5 and
                  len(fresh_reduced_both)>=4 and
                  summary["holdout"]["r13_seam_optimized"]["passed"]==8)
    source={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in
            ("cbdk_geometry/seam_opt.py","cycles/r13/fixtures.py",
             "cycles/r13/blender_run.py","cycles/r13/evaluate.py")}
    return dict(cycle="R13",approved=False,synthetic_only=True,
                development_only=development_only,blender=raw["blender"],cgal=version("cgal"),
                source_sha256=source,blender_source_sha256=raw["source_sha256"],
                summary=summary,comparisons=comparisons,cases=rows,
                detailed_violations=invalid,
                fresh_noncontinuous_reduced_both_10pct=fresh_reduced_both,
                preregistered_research_gate_met=bool(gate),
                decision="research_seam_layout_candidate_passed_unapproved" if gate
                         else "not_preferred_gate_failed_or_inconclusive",
                caveat="Synthetic favorable collars, translational UV charts only; NOT artist-grade UV or normal smoothing")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--development-only",action="store_true")
    args=parser.parse_args()
    inp=Path(args.input)
    result=evaluate(json.loads(inp.read_text()),args.development_only)
    result["raw_sha256"]=hashlib.sha256(inp.read_bytes()).hexdigest()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f:json.dump(result,f,indent=2)
    print("R13_SUMMARY",json.dumps({k:result[k] for k in
          ("summary","fresh_noncontinuous_reduced_both_10pct",
           "detailed_violations","preregistered_research_gate_met","decision")}),flush=True)
    if not result["preregistered_research_gate_met"]:
        raise SystemExit("R13 frozen independent gate failed or results unverified")
