"""R12 independent UV-corner/geometric CGAL validation.

Actual Blender UV corner samples and triangle-corner UVs are independently
recomputed, no trust in runner's seam counters or boundary-error flag.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from importlib.metadata import version
from pathlib import Path
import numpy as np
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from cycles.r7.evaluate import assess
from cycles.r12.fixtures import cases

ROOT=Path(__file__).resolve().parents[2]
ARMS=("r12_chart_transfer","r11_baseline_uv")


def signed_area(a):
    p=np.asarray(a,dtype=float)
    return float(.5*np.linalg.det(np.stack((p[1]-p[0],p[2]-p[0]))))


def independent_uv_metrics(raw):
    faces=np.asarray(raw["strip_faces"],dtype=np.int64)
    verts=np.asarray(raw["strip_vertices"],dtype=float)
    corners=np.asarray(raw["bridge_corner_uvs"],dtype=float)
    base=np.asarray(raw["bridge_vertex_base_uv"],dtype=float)
    if corners.shape!=(len(faces),3,2) or base.shape!=(len(verts),2):
        raise ValueError("invalid per-face-corner UV output")
    if not np.isfinite(corners).all() or not np.isfinite(base).all():
        raise ValueError("nonfinite UV output")
    boundary=np.asarray(raw["boundary_pair_uv_samples"],dtype=float)
    if boundary.shape!=(raw["source_boundary_uv_pair_count"],2,2):
        raise ValueError("missing actual source-vs-bridge UV corner samples")
    if not np.isfinite(boundary).all():
        raise ValueError("nonfinite boundary UV samples")
    max_boundary=float(np.max(np.abs(boundary[:,0,:]-boundary[:,1,:])))
    area_diff=max(abs(signed_area(corners[i])-signed_area(base[faces[i]]))
                  for i in range(len(faces)))
    edges=defaultdict(list)
    for i,tri in enumerate(faces):
        for u,v in zip(tri,np.roll(tri,-1)):
            edges[tuple(sorted((int(u),int(v))))].append(i)
    seam_len=0.
    seams=0
    interior=0
    for (u,v),refs in edges.items():
        if len(refs)!=2:
            continue
        interior+=1
        p,q=refs
        source={int(t):corners[p,j] for j,t in enumerate(faces[p])}
        target={int(t):corners[q,j] for j,t in enumerate(faces[q])}
        gap=max(float(np.max(np.abs(source[t]-target[t]))) for t in (u,v))
        if gap>1e-5:
            seams+=1
            seam_len+=float(np.linalg.norm(verts[u]-verts[v]))
    return dict(
        independent_boundary_max_uv_error=max_boundary,
        independent_signed_uv_area_max_error=float(area_diff),
        independent_seam_edges=seams,
        independent_interior_edges=interior,
        independent_seam_fraction=seams/interior if interior else 0.,
        independent_seam_length=seam_len)


def evaluate(raw,development_only=False):
    if raw.get("cycle")!="R12" or not raw.get("synthetic_only"):
        raise ValueError("R12 requires frozen synthetic research provenance")
    fixtures={(c["name"],c["uv_mode"]):c for c in cases()
              if not development_only or c["split"]=="development"}
    expected={(name,mode,arm) for name,mode in fixtures for arm in ARMS}
    seen=set()
    results=[]
    for row in raw["cases"]:
        key=(row["case"],row["uv_mode"],row["arm"])
        if key not in expected or key in seen:
            raise ValueError("R12 unexpected or duplicate fixture/method")
        seen.add(key)
        record={k:v for k,v in row.items() if k not in
                ("boundary_pair_uv_samples","bridge_corner_uvs",
                 "bridge_vertex_base_uv","strip_vertices","strip_faces",
                 "joined_vertices","joined_triangles")}
        if row["status"]!="generated":
            record["audit_status"]="generation_error"
        else:
            try:
                measurements=independent_uv_metrics(row)
                strip=Mesh(row["strip_vertices"],row["strip_faces"])
                joined=Mesh(row["joined_vertices"],row["joined_triangles"])
                strip_cgal=mesh_hits(strip)
                joined_cgal=mesh_hits(joined)
                geom=assess(strip,fixtures[(row["case"],row["uv_mode"])])
                record.update(measurements,
                              strip_cgal_pairs=len(strip_cgal),
                              joined_cgal_pairs=len(joined_cgal),
                              strip_quality_passed=geom["status"]=="passed",
                              strip_original_boundary_edges_preserved=
                                geom["original_boundary_edges_preserved"])
                core=(row["original_source_signature_unchanged"]
                      and row["source_xyz_preserved"]
                      and row["bridge_material_2"]
                      and row["bridge_face_count"]==row["expected_bridge_face_count"]
                      and row["source_to_bridge_shared_edges"]==row["expected_shared_edges"]
                      and row["outer_boundary_edges"]==row["expected_outer_boundary_edges"]
                      and row["nonmanifold_edges"]==0
                      and row["scene_restored"]
                      and row["bridge_uv_finite"]
                      and geom["status"]=="passed"
                      and len(strip_cgal)==0 and len(joined_cgal)==0
                      and abs(measurements["independent_boundary_max_uv_error"]-
                              row["source_boundary_max_uv_error"])<=1e-5
                      and measurements["independent_seam_edges"]==row["internal_seam_edges"]
                      and measurements["independent_interior_edges"]==row["internal_edges"]
                      and measurements["independent_signed_uv_area_max_error"]<=1e-5)
                continuous=row["uv_mode"]=="continuous"
                if row["arm"]=="r12_chart_transfer":
                    pass_uv=(measurements["independent_boundary_max_uv_error"]<=1e-5
                             and (measurements["independent_seam_edges"]==0 if continuous
                                  else 0<measurements["independent_seam_fraction"]<=.60))
                else:
                    pass_uv=(measurements["independent_boundary_max_uv_error"]<=1e-5
                             if continuous else
                             measurements["independent_boundary_max_uv_error"]>=.1)
                record["audit_status"]="passed" if core and pass_uv else "failed"
                record["core_integrity"]=bool(core)
            except Exception as error:
                record.update(audit_status="oracle_unavailable",
                              reason=type(error).__name__+": "+str(error))
        results.append(record)
        print("R12_RESULT",json.dumps({k:record.get(k) for k in
              ("case","split","uv_mode","arm","audit_status","reason",
               "independent_boundary_max_uv_error","independent_seam_fraction",
               "strip_cgal_pairs","joined_cgal_pairs")}),flush=True)
    if seen!=expected:
        raise ValueError("R12 expected test configurations missing")
    raw_by={(r["case"],r["uv_mode"],r["arm"]):r for r in raw["cases"]}
    cross_arm_invariants=[]
    for name,mode in fixtures:
        cand=raw_by[(name,mode,"r12_chart_transfer")]
        old=raw_by[(name,mode,"r11_baseline_uv")]
        if cand.get("status")!="generated" or old.get("status")!="generated":
            cross_arm_invariants.append((name,"no completed data"))
            continue
        if (cand["strip_vertices"]!=old["strip_vertices"] or
            cand["strip_faces"]!=old["strip_faces"] or
            cand["joined_vertices"]!=old["joined_vertices"] or
            cand["joined_triangles"]!=old["joined_triangles"]):
            cross_arm_invariants.append((name,"3D geometry changed"))
        if cand["source_boundary_uv_pair_count"]!=old["source_boundary_uv_pair_count"]:
            cross_arm_invariants.append((name,"source UV pair count changed"))
    summary={}
    for split in ("development","holdout"):
        summary[split]={}
        for arm in ARMS:
            subset=[r for r in results if r["split"]==split and r["arm"]==arm]
            summary[split][arm]=dict(
                total=len(subset),
                passed=sum(r["audit_status"]=="passed" for r in subset),
                failed=sum(r["audit_status"]=="failed" for r in subset),
                unavailable=sum(r["audit_status"] not in ("passed","failed") for r in subset),
                joined_cgal_pairs=sum(r.get("joined_cgal_pairs",0) for r in subset))
    accepted=all(r["audit_status"]=="passed" for r in results)
    all_new=sum(r["split"]=="holdout" and r["arm"]=="r12_chart_transfer" and
                r["audit_status"]=="passed" for r in results)
    gate=(accepted and not cross_arm_invariants and
          (all_new==8 if not development_only else True))
    return dict(cycle="R12",development_only=development_only,approved=False,
                blender=raw["blender"],cgal=version("cgal"),
                results=results,summary=summary,
                candidate_passed_new=all_new,cross_arm_invariant_errors=cross_arm_invariants,
                preregistered_research_gate_met=bool(gate),
                decision=("research_scoped_chart_transfer_passed_not_approved" if gate
                          else "failed_or_inconclusive_no_adoption"),
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                               for p in ("cbdk_geometry/uv_charts.py",
                                         "cycles/r12/fixtures.py",
                                         "cycles/r12/blender_run.py",
                                         "cycles/r12/evaluate.py")},
                generator_source_sha256=raw["source_sha256"],
                limitation="Charts are constant translations; seams moved inside bridge, not removed, normals not addressed; synthetic collar only")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--development-only",action="store_true")
    args=p.parse_args()
    inp=Path(args.input)
    output=evaluate(json.loads(inp.read_text()),args.development_only)
    output["input_sha256"]=hashlib.sha256(inp.read_bytes()).hexdigest()
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x") as f:json.dump(output,f,indent=2)
    print("R12_SUMMARY",json.dumps({k:output[k] for k in
           ("summary","candidate_passed_new","cross_arm_invariant_errors",
            "preregistered_research_gate_met","decision")}),flush=True)
    if any(r["audit_status"]=="oracle_unavailable" for r in output["results"]):
        raise SystemExit("R12 oracle unavailable: research cannot be accepted")
