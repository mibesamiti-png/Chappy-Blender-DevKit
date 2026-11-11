"""R7: independent CGAL, topology, and authored 3D loft reference comparison.

Synthetic analytic loft reference is by equal original angular parameters,
not the candidate's ray mapping. This score is researcher-authored and not
proof of visual/production superiority.
"""
import argparse
import hashlib
import json
from collections import Counter
from importlib.metadata import version
from pathlib import Path
import numpy as np

from cbdk_geometry import Mesh, quality
from cycles.r2.oracle import mesh_hits
from cycles.r7.fixtures import cases, build

ROOT=Path(__file__).resolve().parents[2]
METHODS=("warped_r7", "native_3_linear", "native_0_path")


def _edge_key(vertices, e):
    return tuple(sorted((tuple(vertices[e[0]]), tuple(vertices[e[1]]))))


def analytic_error(mesh, case):
    # Independent dense parametric loft, with both source ring phases/warps.
    # Flat surface sampling: 384 points by 33 levels, not true Hausdorff.
    reference=build(case["spec"], density=384)
    lower=reference["a"]
    upper=reference["b"]
    u=np.linspace(0.0,1.0,33)
    goal=((1-u)[None,:,None]*lower[:,None,:]+u[None,:,None]*upper[:,None,:]).reshape(-1,3)
    p=mesh.vertices[mesh.faces].mean(axis=1)
    d=[]
    for i in range(0,len(p),48):
        block=p[i:i+48]
        squared=np.sum((block[:,None,:]-goal[None,:,:])**2,axis=2)
        d.extend(np.sqrt(squared.min(axis=1)).tolist())
    return float(np.sqrt(np.mean(np.square(d)))),float(max(d))


def assess(mesh,case):
    a=case["a"].astype(np.float32).astype(float)
    b=case["b"].astype(np.float32).astype(float)
    original=np.vstack((a,b))
    vertexset={tuple(v) for v in mesh.vertices}
    preserved=all(tuple(v) in vertexset for v in original)
    e=Counter(tuple(sorted((int(f[i]),int(f[(i+1)%3]))))
              for f in mesh.faces for i in range(3))
    boundary={_edge_key(mesh.vertices,pair) for pair,count in e.items() if count==1}
    expected={_edge_key(a,(i,(i+1)%len(a))) for i in range(len(a))}
    expected|={_edge_key(b,(i,(i+1)%len(b))) for i in range(len(b))}
    edge_preserved=boundary==expected
    q=quality(mesh)
    euler=len(mesh.vertices)-len(e)+len(mesh.faces)
    topo=(q["boundary_edges"]==len(original) and
          q["nonmanifold_edges"]==0 and q["components"]==1 and euler==0)
    hits=mesh_hits(mesh)
    rms,worst=analytic_error(mesh,case)
    valid=(preserved and edge_preserved and topo and len(hits)==0
           and q["min_triangle_quality"]>=.1 and rms<=.12 and worst<=.28)
    return dict(status="passed" if valid else "failed", original_vertices_preserved=bool(preserved),
                original_boundary_edges_preserved=bool(edge_preserved),
                topology_valid=bool(topo), euler=int(euler),
                cgal_intersection_pairs=len(hits), quality=q,
                analytic_3d_loft_rms=rms,analytic_3d_loft_max=worst,
                vertex_count=len(mesh.vertices),triangle_count=len(mesh.faces))


def evaluate(raw):
    if raw.get("cycle")!="R7" or not raw.get("synthetic_only") or not raw.get("scene_preserved"):
        raise ValueError("R7 synthetic and scene preservation provenance required")
    fixtures={case["name"]:case for case in cases()}
    expected={(name,method) for name in fixtures for method in METHODS}
    seen=set()
    rows=[]
    for candidate in raw["cases"]:
        name,method=candidate["name"],candidate["method"]
        if (name,method) not in expected or (name,method) in seen:
            raise ValueError("unexpected or duplicate R7 measurement")
        seen.add((name,method))
        r={k:v for k,v in candidate.items() if k not in ("vertices","faces")}
        if candidate["generation_status"]!="generated":
            r["status"]="generation_error"
        else:
            try:
                mesh=Mesh(candidate["vertices"],candidate["faces"])
                r.update(assess(mesh,fixtures[name]))
            except Exception as exc:
                r.update(status="oracle_unavailable",reason=type(exc).__name__+": "+str(exc))
        rows.append(r)
        print("R7_RESULT",json.dumps({k:v for k,v in r.items()
            if k in ("name","split","method","status","reason","analytic_3d_loft_rms",
                      "analytic_3d_loft_max","cgal_intersection_pairs")}),flush=True)
    if seen!=expected:
        raise ValueError("missing R7 case/method pairs")
    summary={}
    for split in ("development","holdout"):
        summary[split]={}
        for method in METHODS:
            subset=[r for r in rows if r["split"]==split and r["method"]==method]
            summary[split][method]=dict(
                passed=sum(r["status"]=="passed" for r in subset),
                failed=sum(r["status"]=="failed" for r in subset),
                unavailable=sum(r["status"] not in ("passed","failed") for r in subset),
                total=len(subset),
                crossing_pairs=sum(r.get("cgal_intersection_pairs",0) for r in subset))
    fresh=summary["holdout"]
    unverified=any(r["status"] not in ("passed","failed") for r in rows)
    safe=all(r.get("cgal_intersection_pairs")==0 and r.get("topology_valid")
             for r in rows if r["method"]=="warped_r7" and r["generation_status"]=="generated"
             and r["status"] in ("passed","failed"))
    delta=fresh["warped_r7"]["passed"]-fresh["native_3_linear"]["passed"]
    gate=not unverified and safe and fresh["warped_r7"]["passed"]>=4 and delta>=1
    result=dict(cycle="R7",synthetic_only=True,blender=raw["blender"],
                cgal=version("cgal"),generator_source_sha256=raw["source_sha256"],
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                 for p in ("cycles/r7/fixtures.py","cycles/r7/blender_run.py",
                           "cycles/r7/evaluate.py","cbdk_geometry/warped_loft.py")},
                cases=rows,summary=summary,advantage_delta=delta,
                r7_all_generated_meshes_safe=bool(safe),
                research_gate_met=bool(gate),
                decision="promising_research_candidate" if gate else
                    ("blocked_oracle_incomplete" if unverified else "not_preferred_to_native"),
                approved=False,caveat="Synthetic author-designed analytic target; no real/third-party/artist mesh evaluation")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    opts=parser.parse_args()
    path=Path(opts.input)
    raw=json.loads(path.read_text())
    result=evaluate(raw)
    result["raw_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    dest=Path(opts.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x") as fp:
        json.dump(result,fp,indent=2)
    print("R7_SUMMARY",json.dumps({
        "summary":result["summary"],
        "gate":result["research_gate_met"],
        "decision":result["decision"],
        "delta":result["advantage_delta"]}),flush=True)
    if result["decision"]=="blocked_oracle_incomplete":
        raise SystemExit("R7 contains unverified outputs, not accepted as clean")
