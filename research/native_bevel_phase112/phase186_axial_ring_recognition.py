"""Research only: recognize multi-ring cylindrical extrusions with triangulated caps.
Validate every axial layer and its oriented side coverage before constructing a proxy.
Fixed convex cylindrical family; not general feature recognition or mesh modification.
"""
import json,sys,time,itertools,math
from collections import Counter
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
def hypothesis(V,F,a,b):
    V=np.asarray(V,dtype=float);q=a['boundary'];t=b['boundary'];n=len(q)
    if len(t)!=n:return None,'cap_count'
    A=V[list(q)];B=V[list(t)];ma=A.mean(0);mb=B.mean(0);d=mb-ma;h=float(np.linalg.norm(d))
    scale=float(np.max(np.linalg.norm(V-V.mean(0),axis=1)));eps=REL*scale
    if h<=eps:return None,'axis'
    axis=d/h
    if abs(float(axis@a['normal'])+1)>1e-7 or abs(float(axis@b['normal'])-1)>1e-7:return None,'cap_normals'
    order=tuple(reversed(q));A=V[list(order)]
    drop=a['inner']|b['inner'];keep=[i for i in range(len(V)) if i not in drop]
    heights={i:float((V[i]-ma)@axis) for i in keep}
    groups=[]
    for i in sorted(keep,key=lambda i:heights[i]):
        if not groups or heights[i]-heights[groups[-1][0]]>eps:groups.append([])
        groups[-1].append(i)
    if len(groups)<2 or any(len(g)!=n for g in groups):return None,'layer_count'
    if set(groups[0])!=set(q) or set(groups[-1])!=set(t):return None,'end_layers'
    layers=[];levels=[];max_error=0.
    for g in groups:
        z=float(np.mean([heights[i] for i in g]));levels.append(z)
        D=np.linalg.norm(A[:,None,:]+z*axis-V[g][None,:,:],axis=2)
        j=np.argmin(D,axis=1);error=float(np.max(D[np.arange(n),j]));max_error=max(max_error,error)
        if len(set(map(int,j)))!=n or error>eps:return None,'layer_translation'
        layers.append(tuple(g[int(k)] for k in j))
    if cycle(layers[-1])!=cycle(t):return None,'cap_orientation'
    actual=Counter(cycle(f) for i,f in enumerate(F) if i not in a['ids']|b['ids'])
    pairs=0;quads=0
    for low,high in zip(layers,layers[1:]):
        for i in range(n):
            j=(i+1)%n;q4=(low[i],low[j],high[j],high[i])
            options=[Counter([cycle(q4)])]+[Counter(cycle(t) for t in s) for s in splits(q4)]
            hits=[c for c in options if all(actual[k]>=v for k,v in c.items())]
            if len(hits)!=1:return None,'side_coverage'
            chosen=hits[0];actual.subtract(chosen)
            if len(chosen)==1:quads+=1
            else:pairs+=1
    if any(actual.values()):return None,'extra_faces'
    # Both end rings and all intermediate ring samples are verified before this proxy.
    W=[tuple(V[i]) for i in layers[0]+layers[-1]]
    _,G=cylinder([(0.,0.)]*n)
    proxy=mesh(W,G,'p186_proxy')
    try:
        r=recognize(proxy)
        if not r['recognized']:return None,r['reason']
        return dict(result=r,layers=len(layers),levels=levels,max_layer_error=max_error,
                    tolerance=eps,quad_count=quads,triangle_pairs=pairs,
                    cap_interior_vertices=len(drop)), 'verified'
    finally:bpy.data.meshes.remove(proxy)
def analyze(m):
    V,F=arrays(m);bh=signature(V,F)
    a=measure(m,'cube');top=a['metrics'];hits=[];reasons=[]
    if a['clean'] and top['boundary_edges']==0 and top['euler']==2:
        rr=regions(m)
        for a,b in itertools.combinations(rr,2):
            if a['ids']&b['ids'] or set(a['boundary'])&set(b['boundary']):continue
            if float(a['normal']@b['normal'])> -1+1e-7:continue
            r,reason=hypothesis(V,F,a,b);reasons.append(reason)
            if r is not None:hits.append(r)
    else:reasons.append('mesh_audit')
    out=hits[0] if len(hits)==1 else dict(result=dict(recognized=False,reason='ambiguous' if hits else 'no_valid_cylinder'))
    out.update(hypotheses=len(hits),reasons=reasons,input_unchanged=signature(*arrays(m))==bh,persistent_edit=False)
    return out
CASES=[
 ('regular',8,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),None),
 ('tilted',16,.75,4.,(1,2,3),(2,1,-2),(-1.,-.5,.25,1.),None),
 ('uneven',8,1.7,2.2,(2,-1,3),(3,2,-1),(-1.,-.8,-.1,.9,1.),'uneven'),
 ('horizontal',32,1.2,1.5,(1,0,0),(-1,2,3),(-1.,-.25,.5,1.),None),
 ('short',16,2.,.15,(1,1,1),(0,0,0),(-1.,0.,1.),None),
 ('dense',16,1.3,3.,(3,1,-2),(-2,1,4),tuple(np.linspace(-1,1,9)),None),
 ('bulge',16,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),'bulge'),
 ('twist',16,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),'twist'),
 ('offset',16,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),'offset'),
 ('ellipse',16,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),'ellipse'),
 ('missing',16,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),'missing'),
 ('reversed',16,1.,2.,(0,0,1),(0,0,0),(-1.,0.,1.),'reversed'),
]
def build(n,r,h,axis,c,levels,defect,mode):
    xy=points('uneven') if defect=='uneven' else ring(n)
    V,F=cylinder(xy,tuple(h*z*.5 for z in levels));W=[]
    M=basis(axis)
    for i,(x,y,z) in enumerate(V):
        x*=r;y*=r;layer=i//n
        if defect=='ellipse':x*=1.1
        if layer==1:
            if defect=='bulge':x*=1.03;y*=1.03
            if defect=='offset':x+=.03
            if defect=='twist':x,y=x*math.cos(.12)-y*math.sin(.12),x*math.sin(.12)+y*math.cos(.12)
        W.append(tuple(M@np.asarray([x,y,z])+np.asarray(c)))
    G=list(F[:2])
    for j,f in enumerate(F[2:]):
        if mode=='quad' or mode=='mixed' and j%2==0:G.append(f)
        else:G.extend(splits(f)[j%2])
    if defect=='missing':G.pop(2)
    if defect=='reversed':G[2]=tuple(reversed(G[2]))
    m=mesh(W,G,'p186_source')
    try:return cap_variant(m,'center' if mode=='mixed' else 'corner_fan') if mode!='quad' else m.copy()
    finally:bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for name,n,r,h,axis,c,levels,defect in CASES:
        for mode in ('quad','tri','mixed'):
            m=build(n,r,h,axis,c,levels,defect,mode);q=None
            try:
                q=reindex(m,1807);out=analyze(q);a=out['result']
                expected=defect in (None,'uneven');accurate=False
                if a['recognized']:
                    unit=np.asarray(axis,dtype=float);unit/=np.linalg.norm(unit)
                    accurate=bool(abs(a['radius']-r)<=1e-5 and abs(a['height']-h)<=1e-5
                        and np.linalg.norm(np.asarray(a['center'])-c)<=1e-5
                        and abs(abs(float(np.dot(a['axis'],unit)))-1)<=1e-8 and out['layers']==len(levels))
                row=dict(name=name,mode=mode,expected=expected,accurate=accurate,
                    matched=a['recognized']==expected and (not expected or accurate),**out)
                assert row['input_unchanged'] and not row['persistent_edit']
                rows.append(row);print('PHASE186_ROW',json.dumps(row,allow_nan=False),flush=True)
            finally:
                if q is not None:bpy.data.meshes.remove(q)
                bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase186_axial_ring_recognition.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE186_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        recognized=sum(r['result']['recognized'] for r in rows),preserved=sum(r['input_unchanged'] for r in rows),
        elapsed=out['elapsed']),allow_nan=False),flush=True)
    assert len(rows)==36 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
