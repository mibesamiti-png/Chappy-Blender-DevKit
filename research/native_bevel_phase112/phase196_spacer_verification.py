"""Phase 196: bounded spacer verification and cap-only preparation.
Independent double precision ray/triangle intersection; not exact predicates.
Cap merge is restricted to two planar single-loop convex regions of the
already verified synthetic spacer. No vertex movement or side-face changes.
"""
import numpy as np
import bpy
from collections import Counter
from phase171_planar_topology_variants import arrays
from phase192_bevel_surface_repeatability import snapshot
from phase194_independent_surface_distance import compare
from phase160_operation_contracts import measure

class Rays:
    def __init__(self,m):
        V,T=snapshot(m);A=V[T]
        self.a=A[:,0];self.e=A[:,1]-self.a;self.f=A[:,2]-self.a
        self.scale=np.linalg.norm(self.e,axis=1)*np.linalg.norm(self.f,axis=1)
    def cast(self,o,d,reach):
        d=np.asarray(d,dtype=float);d=d/np.linalg.norm(d)
        P=np.cross(d,self.f);det=np.sum(self.e*P,axis=1)
        good=np.abs(det)>1e-12*self.scale
        inv=np.divide(1.,det,out=np.zeros_like(det),where=good)
        S=np.asarray(o)-self.a;u=np.sum(S*P,axis=1)*inv
        Q=np.cross(S,self.e);v=(Q@d)*inv;t=np.sum(self.f*Q,axis=1)*inv
        ok=good&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>=0)&(t<=reach)
        return float(t[ok].min()) if np.any(ok) else None

def ray_controls():
    m=bpy.data.meshes.new('p196_ray_control')
    try:
        m.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[],[(0,1,2),(0,2,3)]);m.update()
        r=Rays(m)
        assert all(abs(r.cast(p,(0,0,-1),2)-1)<1e-12 for p in ((.5,.5,1),(0,0,1),(1,1,1),(.2,.7,1)))
        assert r.cast((1.1,.5,1),(0,0,-1),2) is None
        assert r.cast((.5,.5,1),(0,0,-1),.5) is None
        return True
    finally:bpy.data.meshes.remove(m)

def merge_caps(m,c,axis,h):
    V,F=arrays(m);P=np.asarray(V);z=(P-c)@axis
    tol=2e-6*max(1.,h,float(np.max(np.linalg.norm(P-c,axis=1))))
    selected=set();caps=[];counts=[]
    for sign in (-1,1):
        level=float(z.min() if sign<0 else z.max())
        ids={i for i,f in enumerate(F) if np.max(np.abs(z[list(f)]-level))<=tol}
        if not ids or ids&selected:return None,dict(reason='cap_not_found')
        selected|=ids;uses=Counter()
        for i in ids:
            f=F[i]
            uses.update(zip(f,f[1:]+f[:1]))
        boundary=[]
        for (a,b),n in uses.items():
            opposite=uses[b,a]
            if n!=1 or opposite>1:return None,dict(reason='cap_incidence')
            if opposite==0:boundary.append((a,b))
        nxt=dict(boundary)
        if len(nxt)!=len(boundary) or len(set(nxt.values()))!=len(boundary) or len(nxt)<3:
            return None,dict(reason='cap_boundary')
        start=min(nxt);cycle=[start]
        while nxt.get(cycle[-1]) not in cycle and nxt.get(cycle[-1]) is not None:
            cycle.append(nxt[cycle[-1]])
        if len(cycle)!=len(nxt) or nxt.get(cycle[-1])!=start:return None,dict(reason='cap_loop')
        X=P[cycle];E=np.roll(X,-1,axis=0)-X
        if np.any(np.cross(E,np.roll(E,-1,axis=0))@axis*sign<=0):
            return None,dict(reason='cap_convexity')
        # Single existing ngon does not need preparation.
        caps.append(tuple(cycle));counts.append(len(ids))
    if counts==[1,1]:return None,dict(reason='already_ngons')
    G=[f for i,f in enumerate(F) if i not in selected]+caps
    used=sorted({i for f in G for i in f});remap={i:j for j,i in enumerate(used)}
    n=bpy.data.meshes.new('p196_cap_prepared')
    try:
        n.from_pydata([V[i] for i in used],[],[tuple(remap[i] for i in f) for f in G]);n.update()
        a=measure(n,'cube');b=measure(m,'cube')
        d=compare(snapshot(m),snapshot(n),1.)
        ok=(a['clean'] and a['metrics']['euler']==2 and not a['metrics']['boundary_edges']
            and abs(a['volume']-b['volume'])<=1e-6*max(1.,b['volume'])
            and d['max_distance']<=tol)
        info=dict(reason='prepared' if ok else 'preparation_rejected',cap_faces_before=counts,
            cap_faces_after=2,removed_interior_vertices=len(V)-len(used),
            unchanged_side_faces=len(F)-len(selected),surface_distance=d['max_distance'],audit=a)
        if ok:return n,info
        bpy.data.meshes.remove(n);return None,info
    except Exception:
        bpy.data.meshes.remove(n);raise
