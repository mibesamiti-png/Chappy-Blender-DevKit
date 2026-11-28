"""Prepare frozen R10/R16/R17 baseline charts for R21."""
import argparse,json
from pathlib import Path
import numpy as np
from cbdk_geometry import Mesh
from cbdk_geometry.quality_router import conditional_flip_loft
from cycles.r7.evaluate import assess
from cycles.r14.audit import uv_audit,incidence
from cycles.r16.cut_uv import solve,source_loop
from cycles.r17.refine import refine,seam_set
from cycles.r21.fixtures import cases

def prepare(c):
    a=c["a"].astype(np.float32).astype(float); b=c["b"].astype(np.float32).astype(float)
    lo,hi=source_loop(a,0.),source_loop(b,1.)
    m=conditional_flip_loft(a,b)["mesh"]; v,f=m.vertices,m.faces
    base,meta=solve(v,f,lo,hi); uv,info=refine(v,f,base,meta["path"])
    q=uv_audit(v,f,uv); old=uv_audit(v,f,base)
    if assess(Mesh(v,f),c)["status"]!="passed" or q["overlap_pairs"] or q["mixed_winding_islands"] or q["degenerate_uv"] or q["islands"]!=1 or q["anisotropy_p95"]>old["anisotropy_p95"]+1e-8 or q["anisotropy_max"]>old["anisotropy_max"]+1e-8: raise ValueError("invalid baseline")
    return dict(case=c["name"],vertices=v.tolist(),faces=f.tolist(),candidate_uv=uv.tolist(),seams=meta["seam_edges"])

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--output",required=True); a=p.parse_args()
    rows=[]
    for c in cases():
        try: r=prepare(c); r["status"]="prepared"
        except Exception as e: r=dict(case=c["name"],status="error",error=type(e).__name__+": "+str(e))
        rows.append(r); print("R21_PREP",r["case"],r["status"],r.get("error",""),flush=True)
    path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as f: json.dump(dict(cycle="R21",stage="baseline",approved=False,rows=rows),f,allow_nan=False)
