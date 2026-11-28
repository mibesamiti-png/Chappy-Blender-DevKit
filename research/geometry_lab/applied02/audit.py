"""External independent pose and mesh audit."""
import argparse,json,math
from pathlib import Path
from collections import Counter
import numpy as np
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits

def welded(v,f):
    # Curve tessellation may duplicate cap boundary vertices; weld exact/near-exact
    # positions for topological audit only. Report merged count; do not edit file.
    _,ix,inv=np.unique(np.round(v,8),axis=0,return_index=True,return_inverse=True)
    return v[ix],inv[f],len(v)-len(ix)
def check_mesh(m):
    v=np.array(m["vertices"]);f=np.array(m["triangles"],int);v,f,merged=welded(v,f)
    e=Counter();directed=Counter()
    for t in f:
        for a,b in zip(t,np.roll(t,-1)):
            e[tuple(sorted((int(a),int(b))))]+=1;directed[int(a),int(b)]+=1
    closed=all(n==2 for n in e.values()) and all(directed[a,b]==directed[b,a] for a,b in directed)
    nondeg=bool(np.all(np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>1e-12))
    error=None;hits=None
    if closed and nondeg:
        try:hits=len(mesh_hits(Mesh(v,f)))
        except Exception as ex:error=str(ex)
    return dict(triangles=len(f),audit_welded_vertices=merged,closed=closed,nondegenerate=nondeg,cgal_hits=hits,error=error,passed=bool(closed and nondeg and hits==0 and error is None))
def pose_check(base,fold,label):
    s=1 if label=="R" else -1;ang=math.radians(s*85);c=math.cos(ang);q=math.sin(ang);rot=np.array([[c,-q,0],[q,c,0],[0,0,1]])
    pivot=np.array([s*.069,.005,.003]);rows={}
    for name,m in base.items():
        v=np.asarray(m["vertices"]);actual=np.asarray(fold[name]["vertices"])
        moving=m["parent"]=="Hinge_"+label;expected=(v-pivot)@rot.T+pivot if moving else v
        err=float(np.max(np.linalg.norm(actual-expected,axis=1)))
        move=float(np.max(np.linalg.norm(actual-v,axis=1)))
        rows[name]=dict(moving=moving,error_m=err,displacement_m=move,passed=bool(err<1e-6 and (move>1e-5 if moving else move<1e-6) and m["triangles"]==fold[name]["triangles"]))
    return rows
def symmetry(m):
    v=np.asarray(m["vertices"]);mirror=v.copy();mirror[:,0]*=-1
    return float(max(np.min(np.linalg.norm(v-x,axis=1)) for x in mirror))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dir",required=True);a=p.parse_args();d=Path(a.dir);r=json.loads((d/"raw.json").read_text());b=r["open"]
    base=sum(m["base_vertices"] for m in b.values());ctrl=sum(m["control_points"] for m in b.values())
    meshes={k:check_mesh(m) for k,m in b.items()};poses={l:pose_check(b,r["fold_"+l],l) for l in ("R","L")};sym={k:symmetry(b[k]) for k in ("Rim_master","Lens_master")}
    modifiers=all(b[k]["modifiers"]==["MIRROR","SOLIDIFY","BEVEL"] for k in sym)
    gate=bool(r["roundtrip_exact"] and base+ctrl<=600 and modifiers and max(sym.values())<1e-6 and all(m["passed"] for m in meshes.values()) and all(x["passed"] for arm in poses.values() for x in arm.values()))
    result=dict(approved=False,gate=gate,roundtrip_exact=r["roundtrip_exact"],base_mesh_vertices=base,bezier_controls=ctrl,evaluated_triangles=sum(m["triangles"] for m in meshes.values()),parts=len(b),modifier_stack_retained=modifiers,symmetry_max_m=sym,meshes=meshes,poses=poses,limitations=["per-object self-intersection only; no interpart folding clearance","simplified decorative hinge sleeve and pin, not validated mechanical joint","no UV or optics validation","no private input or visual superiority claim"])
    (d/"evaluation.json").write_text(json.dumps(result,indent=2));print("APPLIED02_SUMMARY",json.dumps(result),flush=True)
    if not gate:raise SystemExit("applied02 gate unmet")
