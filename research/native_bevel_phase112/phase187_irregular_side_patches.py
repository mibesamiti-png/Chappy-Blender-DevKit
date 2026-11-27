"""Research only: recognize faceted cylinders with irregular side tessellation.
Validate oriented planar patches, rectangular boundary coverage and topology.
Fixed convex extrusions; approximate numerical certificate, no persistent edits.
"""
import json,sys,time,itertools
from collections import defaultdict
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase185_triangulated_caps import regions,cap_variant
from phase182_cylinder_recognition import recognize,basis,REL
from phase180_cylinder_surface_contracts import ring,cylinder
from phase181_adaptive_cylinder_refinement import points
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature
from phase173_alternate_diagonal import cycle,splits
from phase160_operation_contracts import measure
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def coverage(intervals,length,eps):
    end=0.
    for a,b in sorted(intervals):
        if b<=a or abs(a-end)>eps:return False
        end=b
    return bool(intervals and abs(end-length)<=eps)
def patch_check(V,F,ids,origin,u,axis,w,h,eps,tris):
    Q=V-origin;xy=np.column_stack((Q@u,Q@axis))
    uses=defaultdict(list);area=0.
    for i in ids:
        f=F[i]
        for a,b in zip(f,f[1:]+f[:1]):uses[tuple(sorted((a,b)))].append((a,b))
        for a,b,c in tris[i]:
            ab=xy[b]-xy[a];ac=xy[c]-xy[a]
            ar=float(ab[0]*ac[1]-ab[1]*ac[0])
            if ar<=0:return False,'orientation',0.
            area+=ar
    if any(len(e)>2 or len(e)==2 and e[0]!=e[1][::-1] for e in uses.values()):return False,'incidence',0.
    intervals=[[] for _ in range(4)]
    for e in uses.values():
        if len(e)!=1:continue
        a,b=e[0];x,y=xy[a];X,Y=xy[b]
        candidates=[]
        if max(abs(y),abs(Y))<=eps and X>x:candidates.append((0,x,X))
        if max(abs(x-w),abs(X-w))<=eps and Y>y:candidates.append((1,y,Y))
        if max(abs(y-h),abs(Y-h))<=eps and X<x:candidates.append((2,w-x,w-X))
        if max(abs(x),abs(X))<=eps and Y<y:candidates.append((3,h-y,h-Y))
        if len(candidates)!=1:return False,'boundary_edge',0.
        k,l,r=candidates[0];intervals[k].append((l,r))
    if not all(coverage(v,L,eps*2) for v,L in zip(intervals,(w,h,w,h))):return False,'boundary_coverage',0.
    error=abs(area-2*w*h)
    if error>4*eps*(w+h):return False,'area',error
    return True,'verified',error
def hypothesis(m,V,F,a,b):
    q=a['boundary'];t=b['boundary'];n=len(q)
    if len(t)!=n:return None,'cap_count'
    A=V[list(reversed(q))];B=V[list(t)];d=B.mean(0)-A.mean(0);h=float(np.linalg.norm(d))
    eps=REL*float(np.max(np.linalg.norm(V-V.mean(0),axis=1)))
    if h<=eps:return None,'axis'
    axis=d/h
    if abs(float(axis@a['normal'])+1)>1e-7 or abs(float(axis@b['normal'])-1)>1e-7:return None,'cap_normals'
    D=np.linalg.norm(A[:,None,:]+d-B[None,:,:],axis=2)
    j=np.argmin(D,axis=1)
    if len(set(map(int,j)))!=n or float(np.max(D[np.arange(n),j]))>eps:return None,'cap_translation'
    if cycle(tuple(t[int(k)] for k in j))!=cycle(t):return None,'cap_orientation'
    frames=[]
    for i in range(n):
        edge=A[(i+1)%n]-A[i];edge-=axis*float(edge@axis);w=float(np.linalg.norm(edge))
        if w<=eps:return None,'short_edge'
        u=edge/w;normal=np.cross(u,axis)
        frames.append((A[i],u,normal,w))
    assigned=[[] for _ in frames]
    for i,f in enumerate(F):
        if i in a['ids']|b['ids']:continue
        hits=[]
        for k,(o,u,normal,w) in enumerate(frames):
            P=V[list(f)]-o;x=P@u;y=P@axis
            if np.max(np.abs(P@normal))<=eps and min(x)>=-eps and max(x)<=w+eps and min(y)>=-eps and max(y)<=h+eps:
                hits.append(k)
        if len(hits)!=1:return None,'side_assignment'
        assigned[hits[0]].append(i)
    m.calc_loop_triangles();tris=defaultdict(list)
    for tri in m.loop_triangles:tris[tri.polygon_index].append(tuple(tri.vertices))
    errors=[]
    for ids,(o,u,normal,w) in zip(assigned,frames):
        ok,reason,error=patch_check(V,F,ids,o,u,axis,w,h,eps,tris)
        if not ok:return None,reason
        errors.append(error)
    W=[tuple(v) for v in A]+[tuple(B[k]) for k in j];_,G=cylinder([(0.,0.)]*n)
    proxy=mesh(W,G,'p187_proxy')
    try:
        r=recognize(proxy)
        if not r['recognized']:return None,r['reason']
        return dict(result=r,side_patches=n,side_faces=sum(map(len,assigned)),
                    max_area_error=max(errors),tolerance=eps,cap_interior_vertices=len(a['inner']|b['inner'])),'verified'
    finally:bpy.data.meshes.remove(proxy)
def analyze(m):
    V,F=arrays(m);bh=signature(V,F);P=np.asarray(V,dtype=float)
    audit=measure(m,'cube');top=audit['metrics'];hits=[];reasons=[]
    if audit['clean'] and top['boundary_edges']==0 and top['euler']==2:
        rr=regions(m)
        for a,b in itertools.combinations(rr,2):
            if a['ids']&b['ids'] or set(a['boundary'])&set(b['boundary']):continue
            if float(a['normal']@b['normal'])> -1+1e-7:continue
            r,reason=hypothesis(m,P,F,a,b);reasons.append(reason)
            if r is not None:hits.append(r)
    else:reasons.append('mesh_audit')
    out=hits[0] if len(hits)==1 else dict(result=dict(recognized=False,reason='ambiguous' if hits else 'no_valid_cylinder'))
    out.update(reasons=reasons,input_unchanged=signature(*arrays(m))==bh,persistent_edit=False)
    return out
CASES=[
 ('regular',8,1.,2.,(0,0,1),(0,0,0),None),
 ('tilted',16,.75,4.,(1,2,3),(2,1,-2),None),
 ('uneven',8,1.7,2.2,(2,-1,3),(3,2,-1),'uneven'),
 ('horizontal',32,1.2,1.5,(1,0,0),(-1,2,3),None),
 ('short',16,2.,.15,(1,1,1),(0,0,0),None),
 ('ellipse',16,1.,2.,(0,0,1),(0,0,0),'ellipse'),
 ('bulge',16,1.,2.,(0,0,1),(0,0,0),'bulge'),
 ('offset',16,1.,2.,(0,0,1),(0,0,0),'offset'),
 ('missing',16,1.,2.,(0,0,1),(0,0,0),'missing'),
 ('reversed',16,1.,2.,(0,0,1),(0,0,0),'reversed'),
 ('lifted',16,1.,2.,(0,0,1),(0,0,0),'lifted'),
]
def build(n,r,h,axis,c,defect,mode):
    xy=points('uneven') if defect=='uneven' else ring(n)
    V,F=cylinder(xy,(-h*.5,-h*.18,h*.22,h*.5));W=[]
    for i,(x,y,z) in enumerate(V):
        layer=i//n;x*=r;y*=r
        if defect=='ellipse':x*=1.1
        if layer in (1,2):z+=h*.07*((i% n)%5-2)/2
        if layer==1 and defect=='bulge':x*=1.03;y*=1.03
        if layer==1 and defect=='offset':x+=.03
        W.append(np.array([x,y,z]))
    G=list(F[:2]);first_center=None
    for k,f in enumerate(F[2:]):
        if mode=='jitter' or mode=='mixed' and k%2==0:G.extend(splits(f)[k%2])
        else:
            a,b,c1,d=[W[i] for i in f];p=.2*a+.3*b+.35*c1+.15*d
            idx=len(W);W.append(p)
            if first_center is None:first_center=idx
            G.extend((a,b,idx) for a,b in zip(f,f[1:]+f[:1]))
    if defect=='lifted':
        if first_center is None:W[n]+=np.array([.02,.01,0.])
        else:W[first_center]+=np.array([.02,.01,0.])
    if defect=='missing':G.pop(2)
    if defect=='reversed':G[2]=tuple(reversed(G[2]))
    M=basis(axis);m=mesh([tuple(M@p+np.asarray(c)) for p in W],G,'p187_source')
    try:return cap_variant(m,'center' if mode=='mixed' else 'corner_fan')
    finally:bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for name,n,r,h,axis,c,defect in CASES:
        for mode in ('jitter','fan','mixed'):
            m=build(n,r,h,axis,c,defect,mode);q=None
            try:
                q=reindex(m,1871);out=analyze(q);a=out['result']
                expected=defect in (None,'uneven');accurate=False
                if a['recognized']:
                    unit=np.asarray(axis,dtype=float);unit/=np.linalg.norm(unit)
                    accurate=bool(abs(a['radius']-r)<=1e-5 and abs(a['height']-h)<=1e-5 and
                        np.linalg.norm(np.asarray(a['center'])-c)<=1e-5 and abs(abs(float(np.dot(a['axis'],unit)))-1)<=1e-8)
                row=dict(name=name,mode=mode,vertices=len(q.vertices),faces=len(q.polygons),expected=expected,
                    accurate=accurate,matched=a['recognized']==expected and (not expected or accurate),**out)
                assert row['input_unchanged'] and not row['persistent_edit']
                rows.append(row);print('PHASE187_ROW',json.dumps(row,allow_nan=False),flush=True)
            finally:
                if q is not None:bpy.data.meshes.remove(q)
                bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase187_irregular_side_patches.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE187_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        recognized=sum(r['result']['recognized'] for r in rows),preserved=sum(r['input_unchanged'] for r in rows),
        elapsed=out['elapsed']),allow_nan=False),flush=True)
    assert len(rows)==33 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
