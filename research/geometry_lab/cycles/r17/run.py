"""R17 frozen comparison: R16 vs guarded distortion refinement."""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
from cbdk_geometry.quality_router import conditional_flip_loft
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from cycles.r7.evaluate import assess
from cycles.r14.audit import uv_audit,incidence,controls
from cycles.r16.cut_uv import solve,source_loop
from cycles.r17.fixtures import cases
from cycles.r17.refine import refine,seam_set

def metrics(v,f,uv):
    q=uv_audit(v,f,uv); q.pop("signed_areas"); return q

def run(dev):
    controls(); rows=[]
    for case in cases():
        if dev and case["split"]!="development": continue
        r=dict(case=case["name"],split=case["split"])
        try:
            a=case["a"].astype(np.float32).astype(float); b=case["b"].astype(np.float32).astype(float)
            lo=source_loop(a,0.); hi=source_loop(b,1.)
            m=conditional_flip_loft(a,b)["mesh"]; v=m.vertices.copy(); f=m.faces.copy()
            base,meta=solve(v,f,lo,hi); start=time.perf_counter(); out,info=refine(v,f,base,meta["path"]); elapsed=time.perf_counter()-start
            old=metrics(v,f,base); new=metrics(v,f,out)
            # independent edge and pin comparison to original authored source UVs
            edges=incidence(f); lookup={tuple(p):i for i,p in enumerate(v.astype(np.float32).astype(float))}
            gaps=[]
            for x,y,ux,uy in lo+hi:
                i,j=lookup[x],lookup[y]; face=edges[tuple(sorted((i,j)))][0]
                for k,p in ((i,ux),(j,uy)): gaps.append(float(np.max(np.abs(out[face,np.flatnonzero(f[face]==k)[0]]-p))))
            seam={tuple(sorted(e)) for e in zip(meta["path"],meta["path"][1:])}
            pinned_vertices={k for e in seam|{e for e,refs in edges.items() if len(refs)==1} for k in e}
            mask=np.isin(f,list(pinned_vertices))
            pinned=bool(np.array_equal(out[mask],base[mask]))
            hit=len(mesh_hits(Mesh(v,f))); quality=assess(Mesh(v,f),case)["status"]
            unchanged=bool(np.array_equal(v,m.vertices) and np.array_equal(f,m.faces))
            gain=(old["anisotropy_p95"]-new["anisotropy_p95"])/old["anisotropy_p95"]
            passed=bool(max(gaps)<=1e-8 and pinned and seam_set(f,out)==seam_set(f,base)==seam and new["overlap_pairs"]==0 and new["mixed_winding_islands"]==0 and new["degenerate_uv"]==0 and new["islands"]==1 and new["anisotropy_p95"]<=old["anisotropy_p95"]+1e-8 and new["anisotropy_max"]<=old["anisotropy_max"]+1e-8 and hit==0 and unchanged)
            r.update(passed=passed,baseline=old,candidate=new,p95_gain=gain,source_gap=max(gaps),pinned_exact=pinned,seams=len(seam),cgal_pairs=hit,r10_quality=quality,geometry_unchanged=unchanged,seconds=elapsed,optimizer=info,vertices=v.tolist(),faces=f.tolist(),baseline_uv=base.tolist(),candidate_uv=out.tolist())
        except Exception as exc: r.update(passed=False,error=type(exc).__name__+": "+str(exc))
        rows.append(r)
        print("R17_ROW",json.dumps({k:v for k,v in r.items() if k not in ("vertices","faces","baseline_uv","candidate_uv")}),flush=True)
    fresh=[r for r in rows if r["split"]=="holdout"]; improved=sum(r.get("p95_gain",0)>=.05 for r in fresh)
    gate=bool(len(rows)==(4 if dev else 12) and all(r["passed"] for r in rows) and (dev or improved>=4))
    return dict(cycle="R17",approved=False,synthetic_only=True,detached_only=True,development_only=dev,rows=rows,gate=gate,fresh_improved_at_least_5pct=improved,source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ("cycles/r17/refine.py","cycles/r17/fixtures.py","cycles/r17/run.py")})

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--output",required=True); p.add_argument("--development-only",action="store_true"); a=p.parse_args()
    r=run(a.development_only); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f: json.dump(r,f,indent=2,allow_nan=False)
    print("R17_SUMMARY",json.dumps(dict(gate=r["gate"],passed=sum(x["passed"] for x in r["rows"]),total=len(r["rows"]),fresh_improved=r["fresh_improved_at_least_5pct"],source_sha256=r["source_sha256"])),flush=True)
    if not r["gate"]: raise SystemExit("R17 frozen gate failed")
