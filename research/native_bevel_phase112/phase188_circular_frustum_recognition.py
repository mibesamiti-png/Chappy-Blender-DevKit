"""Research only: distinguish circular cylinder and coaxial circular frustum hypotheses.
Two convex cap regions, corresponding angular samples, oriented side coverage.
No arbitrary feature extraction, automatic modification, or cone-apex support.
"""
import json,sys,time,itertools,math
from collections import Counter
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase185_triangulated_caps import regions,cap_variant
from phase182_cylinder_recognition import basis,REL
from phase180_cylinder_surface_contracts import cylinder,ring
from phase181_adaptive_cylinder_refinement import points
from phase184_triangulated_cylinder_recognition import variant
from phase187_irregular_side_patches import analyze as cylinder_analyze
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature
from phase173_alternate_diagonal import cycle,splits
from phase160_operation_contracts import measure
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def circle(V,region,u,v):
    X=V[list(region['boundary'])];mean=X.mean(0)
    xy=np.column_stack(((X-mean)@u,(X-mean)@v))
    scale=float(np.max(np.linalg.norm(xy,axis=1)))
    if scale<=0:return None
    q=xy/scale;M=np.column_stack((2*q,np.ones(len(q))))
    sol,_,rank,sv=np.linalg.lstsq(M,np.sum(q*q,axis=1),rcond=None)
    if rank!=3 or sv[-1]/sv[0]<1e-8:return None
    r2=float(sol[2]+sol[:2]@sol[:2])
    if r2<=0:return None
    radius=scale*math.sqrt(r2);center=mean+scale*(sol[0]*u+sol[1]*v)
    error=float(np.max(np.abs(np.linalg.norm(xy-sol[:2]*scale,axis=1)-radius)))
    return center,radius,error
def hypothesis(V,F,a,b):
    n=len(a['boundary'])
    if n!=len(b['boundary']):return None,'cap_count'
    axis=-a['normal'];u=V[a['boundary'][1]]-V[a['boundary'][0]]
    u-=axis*float(u@axis);u/=np.linalg.norm(u);v=np.cross(axis,u)
    ca=circle(V,a,u,v);cb=circle(V,b,u,v)
    if ca is None or cb is None:return None,'circle_fit'
    c0,r0,e0=ca;c1,r1,e1=cb;eps=REL*max(r0,r1)
    if max(e0,e1)>eps:return None,'not_circular'
    d=c1-c0;h=float(d@axis)
    if h<=eps or float(np.linalg.norm(d-h*axis))>eps:return None,'not_coaxial'
    # Exclude ambiguous almost-equal taper from claiming an exact cylinder.
    delta=abs(r1-r0)
    if delta<=eps:kind='cylinder'
    elif delta>=4*eps:kind='frustum'
    else:return None,'ambiguous_taper'
    order=tuple(reversed(a['boundary']));top=b['boundary']
    A=V[list(order)];B=V[list(top)]
    qa=(A-c0)/r0;qb=(B-c1)/r1
    D=np.linalg.norm(qa[:,None,:]-qb[None,:,:],axis=2);j=np.argmin(D,axis=1)
    error=float(np.max(D[np.arange(n),j]))
    if len(set(map(int,j)))!=n or error>2*REL:return None,'angular_correspondence'
    high=tuple(top[int(k)] for k in j)
    if cycle(high)!=cycle(top):return None,'cap_orientation'
    if set(order)|set(high)!=set(range(len(V)))-(a['inner']|b['inner']):return None,'extra_vertices'
    theta=np.arctan2(qa@v,qa@u);gaps=(np.roll(theta,-1)-theta)%(2*math.pi)
    if not (np.all(gaps>0) and np.all(gaps<math.pi) and abs(float(gaps.sum())-2*math.pi)<1e-7):
        return None,'angular_coverage'
    actual=Counter(cycle(f) for i,f in enumerate(F) if i not in a['ids']|b['ids'])
    pairs=0;quads=0;plane_max=0.
    for i in range(n):
        k=(i+1)%n;q=(order[i],order[k],high[k],high[i]);X=V[list(q)]
        normal=np.cross(X[1]-X[0],X[3]-X[0]);length=float(np.linalg.norm(normal))
        if length<=eps*eps:return None,'degenerate_side'
        plane=float(np.max(np.abs((X-X[0])@(normal/length))));plane_max=max(plane_max,plane)
        if plane>eps:return None,'nonplanar_side'
        choices=[Counter([cycle(q)])]+[Counter(cycle(t) for t in s) for s in splits(q)]
        hits=[c for c in choices if all(actual[t]>=k for t,k in c.items())]
        if len(hits)!=1:return None,'side_coverage'
        chosen=hits[0];actual.subtract(chosen)
        if len(chosen)==1:quads+=1
        else:pairs+=1
    if any(actual.values()):return None,'extra_faces'
    return dict(kind=kind,radii=sorted([r0,r1]),height=h,axis=axis.tolist(),
        center=((c0+c1)*.5).tolist(),radial_error=max(e0,e1),angular_error=error,
        max_plane_error=plane_max,tolerance=eps,ring_vertices=n,quad_count=quads,triangle_pairs=pairs,
        taper_angle=math.degrees(math.atan2(delta,h))), 'verified'
def classify(m):
    V,F=arrays(m);bh=signature(V,F);P=np.asarray(V,dtype=float)
    audit=measure(m,'cube');q=audit['metrics'];hits=[];reasons=[]
    if audit['clean'] and q['boundary_edges']==0 and q['euler']==2:
        rr=regions(m)
        for a,b in itertools.combinations(rr,2):
            if a['ids']&b['ids'] or set(a['boundary'])&set(b['boundary']):continue
            if float(a['normal']@b['normal'])> -1+1e-7:continue
            r,reason=hypothesis(P,F,a,b);reasons.append(reason)
            if r is not None:hits.append(r)
    else:reasons.append('mesh_audit')
    # Existing irregular-patch cylinder recognizer is independent evidence.
    old=cylinder_analyze(m)['result']
    if len(hits)==1 and hits[0]['kind']=='frustum' and not old['recognized']:
        result=hits[0]
    elif len(hits)==1 and hits[0]['kind']=='cylinder' and old['recognized']:
        result=hits[0]
    elif not hits and old['recognized']:
        result=dict(kind='cylinder',radii=[old['radius']]*2,height=old['height'],
                    axis=old['axis'],center=old['center'],fallback='irregular_patch')
    else:result=dict(kind='unknown')
    return dict(result=result,reasons=reasons,hypotheses=len(hits),cylinder_reference=old['recognized'],
        input_unchanged=signature(*arrays(m))==bh,persistent_edit=False)
CASES=[
 ('cylinder',16,1.,1.,2.,(0,0,1),(0,0,0),None,'cylinder'),
 ('taper',16,1.,.6,2.,(0,0,1),(0,0,0),None,'frustum'),
 ('reverse_taper',8,.4,1.3,3.,(1,2,3),(2,1,-2),None,'frustum'),
 ('uneven_taper',8,1.7,.8,2.2,(2,-1,3),(3,2,-1),'uneven','frustum'),
 ('short_taper',16,2.,1.5,.2,(1,1,1),(0,0,0),None,'frustum'),
 ('tilted_cylinder',16,.75,.75,4.,(1,2,3),(2,1,-2),None,'cylinder'),
 ('ellipse',16,1.,.7,2.,(0,0,1),(0,0,0),'ellipse','unknown'),
 ('twist',16,1.,.7,2.,(0,0,1),(0,0,0),'twist','unknown'),
 ('offset',16,1.,.7,2.,(0,0,1),(0,0,0),'offset','unknown'),
 ('bulge',16,1.,1.,2.,(0,0,1),(0,0,0),'bulge','unknown'),
 ('missing',16,1.,.7,2.,(0,0,1),(0,0,0),'missing','unknown'),
 ('reversed',16,1.,.7,2.,(0,0,1),(0,0,0),'reversed','unknown'),
]
def build(n,r0,r1,h,axis,c,defect,mode):
    xy=points('uneven') if defect=='uneven' else ring(n)
    zs=(-h*.5,0.,h*.5) if defect=='bulge' else (-h*.5,h*.5)
    V,F=cylinder(xy,zs);W=[];M=basis(axis)
    for i,(x,y,z) in enumerate(V):
        t=(z+h*.5)/h;r=(1-t)*r0+t*r1
        if defect=='bulge' and i//n==1:r*=1.03
        x*=r;y*=r
        if defect=='ellipse':x*=1.1
        if i>=n and defect=='offset':x+=.06
        if i>=n and defect=='twist':x,y=x*math.cos(.12)-y*math.sin(.12),x*math.sin(.12)+y*math.cos(.12)
        W.append(tuple(M@np.asarray([x,y,z])+np.asarray(c)))
    if defect=='missing':F.pop(2)
    if defect=='reversed':F[2]=tuple(reversed(F[2]))
    m=mesh(W,F,'p188_source');v=None
    try:
        v=variant(m,mode)
        return cap_variant(v,'center' if mode=='mixed' else 'corner_fan') if mode!='quad' else v.copy()
    finally:
        if v is not None:bpy.data.meshes.remove(v)
        bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for name,n,r0,r1,h,axis,c,defect,expected in CASES:
        for mode in ('quad','diag_a','mixed'):
            m=build(n,r0,r1,h,axis,c,defect,mode);q=None
            try:
                q=reindex(m,1881);out=classify(q);a=out['result'];accurate=None
                if a['kind']!='unknown':
                    unit=np.asarray(axis,dtype=float);unit/=np.linalg.norm(unit)
                    accurate=bool(np.max(np.abs(np.asarray(a['radii'])-sorted([r0,r1])))<=1e-5
                        and abs(a['height']-h)<=1e-5 and np.linalg.norm(np.asarray(a['center'])-c)<=1e-5
                        and abs(abs(float(np.dot(a['axis'],unit)))-1)<=1e-8)
                row=dict(name=name,mode=mode,expected=expected,accurate=accurate,
                    matched=a['kind']==expected and (expected=='unknown' or accurate is True),**out)
                assert row['input_unchanged'] and not row['persistent_edit']
                rows.append(row);print('PHASE188_ROW',json.dumps(row,allow_nan=False),flush=True)
            finally:
                if q is not None:bpy.data.meshes.remove(q)
                bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase188_circular_frustum_recognition.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE188_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        kinds=dict(Counter(r['result']['kind'] for r in rows)),preserved=sum(r['input_unchanged'] for r in rows),
        elapsed=out['elapsed']),allow_nan=False),flush=True)
    assert len(rows)==36 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
