"""Independent R14 + CGAL measurement of R16 detached cut chart."""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
from cbdk_geometry.quality_router import conditional_flip_loft
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from cycles.r7.evaluate import assess
from cycles.r14.audit import uv_audit,incidence,controls
from cycles.r16.fixtures import cases
from cycles.r16.cut_uv import solve,source_loop,Reject

def baseline(v,f,a,b,lower,upper):
    ca=a[:,:2].mean(axis=0); cb=b[:,:2].mean(axis=0)
    t=np.clip((v[:,2]-a[:,2].mean())/(b[:,2].mean()-a[:,2].mean()),0,1)
    center=ca[None,:]*(1-t[:,None])+cb[None,:]*t[:,None]
    ang=np.mod(np.arctan2(v[:,1]-center[:,1],v[:,0]-center[:,0]),2*np.pi)/(2*np.pi)
    out=np.stack((ang,t),axis=1)[f]
    lookup={tuple(p):i for i,p in enumerate(v.astype(np.float32).astype(float))}
    edges=incidence(f)
    for x,y,ux,uy in lower+upper:
        i,j=lookup[x],lookup[y]; fi=edges[tuple(sorted((i,j)))][0]
        for k,p in ((i,ux),(j,uy)): out[fi,np.flatnonzero(f[fi]==k)[0]]=p
    return out

def seam_count(v,f,uv):
    edges=incidence(f); count=0; length=0.
    for (a,b),refs in edges.items():
        if len(refs)!=2: continue
        i,j=refs; p=dict(zip(f[i],uv[i])); q=dict(zip(f[j],uv[j]))
        if max(np.max(np.abs(p[k]-q[k])) for k in (a,b))>1e-5: count+=1; length+=float(np.linalg.norm(v[a]-v[b]))
    return count,length

def metrics(v,f,uv):
    r=uv_audit(v,f,uv); r.pop("signed_areas"); r["seams"],r["seam_length"]=seam_count(v,f,uv); return r

def run(dev):
    controls(); rows=[]; negatives=[]
    for case in cases():
        if dev and case["split"]!="development": continue
        name=case["name"]; a=case["a"].astype(np.float32).astype(float); b=case["b"].astype(np.float32).astype(float)
        lower=source_loop(a,0.); upper=source_loop(b,1.)
        row=dict(case=name,split=case["split"])
        try:
            m=conditional_flip_loft(a,b)["mesh"]; v=m.vertices.copy(); f=m.faces.copy()
            row["baseline"]=metrics(v,f,baseline(v,f,a,b,lower,upper))
            uv,meta=solve(v,f,lower,upper); row["candidate"]=metrics(v,f,uv); row["solver"]=meta
            row["cgal_pairs"]=len(mesh_hits(Mesh(v,f))); row["r10_quality"]=assess(Mesh(v,f),case)["status"]
            q=row["candidate"]; row["geometry_unchanged"]=bool(np.array_equal(v,m.vertices) and np.array_equal(f,m.faces))
            row["passed"]=bool(meta["boundary_error"]<=1e-8 and q["overlap_pairs"]==0 and q["mixed_winding_islands"]==0 and q["degenerate_uv"]==0 and q["islands"]==1 and q["seams"]==meta["seam_edges"] and row["cgal_pairs"]==0 and row["geometry_unchanged"])
            row["vertices"]=v.tolist(); row["faces"]=f.tolist(); row["corner_uv"]=uv.tolist()
        except Exception as exc: row.update(passed=False,error=type(exc).__name__+": "+str(exc))
        rows.append(row)
        print("R16_ROW",json.dumps({k:row.get(k) for k in ("case","split","passed","error","baseline","candidate","solver","cgal_pairs","r10_quality")}),flush=True)
        if len(rows)==1 and "vertices" in row:
            bad=list(lower); x,y,u,w=bad[0]
            variations=[("missing_edge",bad[:-1]),("contradictory_pin",[(x,y,(.1,0),w)]+bad[1:]),("wrapped_boundary",[(x,y,u,(.95,0))]+bad[1:]),("nonfinite_pin",[(x,y,(float("nan"),0),w)]+bad[1:])]
            for label,wrong in variations:
                try: solve(v,f,wrong,upper); negatives.append(dict(case=label,rejected=False))
                except Reject as exc: negatives.append(dict(case=label,rejected=True,reason=str(exc)))
    gate=bool(len(rows)==(4 if dev else 12) and all(r["passed"] for r in rows) and len(negatives)==4 and all(r["rejected"] for r in negatives))
    return dict(cycle="R16",approved=False,synthetic_only=True,detached_only=True,development_only=dev,rows=rows,negative_controls=negatives,gate=gate)

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--output",required=True); p.add_argument("--development-only",action="store_true"); a=p.parse_args()
    r=run(a.development_only)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f: json.dump(r,f,indent=2,allow_nan=False)
    print("R16_SUMMARY",json.dumps(dict(gate=r["gate"],passed=sum(x["passed"] for x in r["rows"]),total=len(r["rows"]),negative_controls=r["negative_controls"])),flush=True)
    if not r["gate"]: raise SystemExit("R16 gate failed; preserve negative findings")
