"""Phase211-A: bounded static support feasibility, not a walking proof.
Four horizontal circular pads, ideal synchronized translations, fixed COM
projection and guard bands around stance transitions. Model units only.
No floor dynamics, cam packaging, return mechanism or force validation.
"""
import itertools,json,math,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase210_inverse_cam import law,audit
FEET=np.array([[4.,3.],[-4.,3.],[4.,-3.],[-4.,-3.]])
N=1440;PAD=.4;GUARD=1./360.;COM=.1
def cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def hull(p):
    p=sorted(map(tuple,p));lo=[];hi=[]
    for seq,out in ((p,lo),(p[::-1],hi)):
        for v in seq:
            while len(out)>=2 and cross(out[-2],out[-1],v)<=0:out.pop()
            out.append(v)
    return lo[:-1]+hi[:-1] if len(p)>1 else p
def margin(h,p):
    if not h:return -100.
    if len(h)==1:return -math.dist(h[0],p)
    inside=len(h)>=3;dist=float('inf')
    for i,a in enumerate(h):
        b=h[(i+1)%len(h)];dx=b[0]-a[0];dy=b[1]-a[1]
        t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
        inside=inside and cross(a,b,p)>=-1e-10
        dist=min(dist,math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))
    return dist if inside else -dist
def evaluate(duty,ph,guard=GUARD,n=N):
    u=(np.arange(n)[:,None]/n+np.array(ph)[None,:]/4.)%1.
    x=law(u*math.tau,'stride',duty)-1.2
    xy=np.broadcast_to(FEET,(n,4,2)).copy();xy[:,:,0]+=x
    mask=(u>=guard)&(u<=duty-guard)
    points=[(a,b) for a in (-COM,COM) for b in (-COM,COM)]
    counts=np.bincount(mask.sum(axis=1),minlength=5)
    nominal=float('inf');robust=float('inf')
    for i in range(n):
        h=hull(xy[i][mask[i]])
        nominal=min(nominal,margin(h,(0.,0.)))
        robust=min(robust,*(margin(h,p)+PAD for p in points))
    separation=min(float(np.linalg.norm(xy[:,j]-xy[:,k],axis=1).min()) for j,k in itertools.combinations(range(4),2))
    return dict(phases=[int(v*90) for v in ph],duty=duty,guard_degrees=guard*360,
        samples=n,min_support=int(np.flatnonzero(counts)[0]),support_counts=counts.tolist(),
        min_point_margin=nominal,min_pad_margin=robust,min_pad_clearance=separation-2*PAD,
        support_gate=bool(counts[:3].sum()==0 and robust>=.2 and separation>2*PAD))
def main():
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[]
    for duty in (.75,.77,.80):
        profiles=[audit(k,r,duty=duty)[1] for k,r in [('lift',2.5),('stride',7.)]]
        orders=[evaluate(duty,(0,)+p) for p in itertools.permutations((1,2,3))]
        best=max(orders,key=lambda q:q['min_pad_margin'])
        gate=best['support_gate'] and all(p['passed'] for p in profiles)
        trials.append(dict(duty=duty,profiles=profiles,orders=orders,best=best,gate=gate))
        print('PHASE211A_TRIAL',json.dumps(dict(duty=duty,best=best,profiles=profiles,gate=gate),allow_nan=False),flush=True)
    chosen=next((q for q in trials if q['gate']),None)
    dense=evaluate(chosen['duty'],tuple(v//90 for v in chosen['best']['phases']),n=3600) if chosen else None
    nominal=evaluate(.75,(0,3,2,1),guard=0.)
    out=dict(complete=True,approved=False,static_gate=bool(dense and dense['support_gate']),
        selected_duty=chosen['duty'] if chosen else None,selected_phases=chosen['best']['phases'] if chosen else None,
        trials=trials,dense=dense,nominal_75=nominal,feet=FEET.tolist(),pad_radius=PAD,com_box_half_width=COM,
        packaging_certified=False,physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_support_design.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211A_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
