"""Phase209-B1: bounded four-bar stance search; no dynamics certification.
Use the actual convex rounded triangular outline (32 directions, R=.27)
and a fixed horizontal floor band above the global minimum of its bottom.
Retain failure to reach duty .75, rather than relax the target.
"""
import json,math,time
from pathlib import Path
from phase207_walking_machine import points,rng
import numpy as np
ROOT=Path(__file__).resolve().parent
N=120;R=.27;TOL=.035;TARGET=.75
BASE=[.6929126433990895,1.495141205001622,2.1626974924188103,1.4865368241155517,3.298077477756888,-1.0078676866004241]
def evaluate(z,n=N):
    r,d,l,m,u,v=z
    if not (.30<=r<=.90 and 1.1<=d<=2 and .8<=l<=3.8 and .8<=m<=3.8 and 0<=u<=4.5 and abs(v)<=2.8):return None
    if d-r<=abs(l-m)+.08 or d+r>=l+m-.08:return None
    q=points(z,np.arange(n)*math.tau/n)
    if q is None:return None
    B,C,F=q
    if np.any(F[:,1]>np.minimum(B[:,1],C[:,1])):return None
    if max(d,B[:,0].max(),C[:,0].max(),F[:,0].max())-min(0.,B[:,0].min(),C[:,0].min(),F[:,0].min())>4.26:return None
    phi=np.arctan2(C[:,1]-B[:,1],C[:,0]-B[:,0])
    j=np.rint((-math.pi/2-phi)*32/math.tau)
    y=F[:,1]+R*np.sin(phi+j*math.tau/32);x=F[:,0]
    lo=float(y.min());hi=float(y.max());mask=y<=lo+TOL
    if hi-lo<TOL+.35:return None
    best=None
    for i in np.flatnonzero(mask & ~np.roll(mask,1)):
        k=int(i)
        while k<i+n-1 and mask[(k+1)%n]:k+=1
        idx=np.arange(i,k+1)%n
        stroke=float(x[k%n]-x[i]);rev=float(np.maximum(0.,-np.diff(x[idx])).sum())
        if stroke<.7 or rev>.05:continue
        out=dict(z=list(z),phase=float(i*360/n),duty=len(idx)/n,stroke=stroke,lift=hi-lo-TOL,reverse=rev)
        if best is None or out['duty']>best['duty']:best=out
    return best
def main():
    start=time.perf_counter();random=rng(209);best=None;valid=0
    for i in range(24000):
        z=[.30+next(random)*.6,1.1+next(random)*.9,.8+next(random)*3,.8+next(random)*3,next(random)*4.5,-2.8+next(random)*5.6]
        q=evaluate(z)
        if q:
            valid+=1
            if best is None or q['duty']>best['duty']:best=q
    coarse=best
    for i in range(6000):
        if best is None:break
        scale=.25 if i<2000 else .10 if i<4000 else .035
        q=evaluate([x+(next(random)-.5)*scale for x in best['z']])
        if q and (q['duty'],q['stroke'])>(best['duty'],best['stroke']):best=q
    dense=evaluate(best['z'],3600) if best else None
    out=dict(complete=True,approved=False,physical_walk_certified=False,
        samples=N,dense_samples=3600,coarse_candidates=24000,refinement_candidates=6000,coarse_feasible=valid,
        floor_band=TOL,target_duty=TARGET,baseline=evaluate(BASE),coarse=coarse,best=best,dense=dense,
        target_met=bool(dense and dense['duty']>=TARGET),global_infeasibility_proven=False,
        elapsed=time.perf_counter()-start)
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    (dest/'phase209_stance_search.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE209B1_SUMMARY',json.dumps(out,allow_nan=False),flush=True)
    assert best is not None and dense is not None
if __name__=='__main__':main()
