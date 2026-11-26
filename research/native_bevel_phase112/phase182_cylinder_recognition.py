"""Research only: recover a cylinder hypothesis from two n-gon caps and quad sides.
Arbitrary rigid orientation, unknown radius/axis/height; no mesh edits or inferred permission.
A restricted faceted cylinder recognizer, not general surface reconstruction.
"""
import json,math,sys,time
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature
from phase180_cylinder_surface_contracts import cylinder,ring
from phase181_adaptive_cylinder_refinement import points
from phase160_operation_contracts import measure
from phase173_alternate_diagonal import cycle
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
REL=1e-5
def recognize(m):
    V,F=arrays(m);V=np.asarray(V,dtype=float);caps=[f for f in F if len(f)>=8]
    def fail(reason,**evidence):return dict(recognized=False,reason=reason,**evidence)
    if len(caps)!=2 or len(caps[0])!=len(caps[1]):return fail('cap_structure')
    a,b=caps;n=len(a)
    if len(V)!=2*n or len(F)!=n+2 or set(a)&set(b) or set(a)|set(b)!=set(range(len(V))):return fail('ring_structure')
    A=V[list(a)];B=V[list(b)];ma=A.mean(0);mb=B.mean(0);d=mb-ma;h=float(np.linalg.norm(d))
    scale=float(np.max(np.linalg.norm(V-V.mean(0),axis=1)));eps=REL*scale
    if scale<=0 or h<=eps:return fail('degenerate_axis')
    axis=d/h
    pa=float(np.max(np.abs((A-ma)@axis)));pb=float(np.max(np.abs((B-mb)@axis)))
    if max(pa,pb)>eps:return fail('nonparallel_caps',plane_error=max(pa,pb))
    # Match the two rings by translation along their candidate axis.
    distances=np.linalg.norm(A[:,None,:]+d-B[None,:,:],axis=2)
    j=np.argmin(distances,axis=1);pair_error=float(np.max(distances[np.arange(n),j]))
    if len(set(map(int,j)))!=n or pair_error>eps:return fail('nontranslated_rings',pair_error=pair_error)
    u=A[0]-ma;u=u-axis*np.dot(u,axis);un=float(np.linalg.norm(u))
    if un<=eps:return fail('degenerate_basis')
    u/=un;v=np.cross(axis,u)
    xy=np.column_stack(((A-ma)@u,(A-ma)@v))
    M=np.column_stack((2*xy,np.ones(n)));rhs=np.sum(xy*xy,axis=1)
    sol,_,rank,sval=np.linalg.lstsq(M,rhs,rcond=None)
    if rank!=3 or sval[-1]/sval[0]<1e-8:return fail('ill_conditioned_circle')
    center=sol[:2];r2=float(sol[2]+center@center)
    if r2<=0:return fail('invalid_radius')
    radius=math.sqrt(r2);q=xy-center
    radial=float(np.max(np.abs(np.linalg.norm(q,axis=1)-radius)))
    if radial>eps:return fail('not_circular',radius=radius,radial_error=radial)
    # Winding and topology must describe one complete extrusion.
    ordered=tuple(reversed(a));mapping={a[i]:b[int(j[i])] for i in range(n)}
    expected=[cycle(tuple(mapping[i] for i in ordered))]
    expected.extend(cycle((i,k,mapping[k],mapping[i])) for i,k in zip(ordered,ordered[1:]+ordered[:1]))
    actual=[cycle(f) for f in F if f!=a]
    if sorted(expected)!=sorted(actual):return fail('side_connectivity')
    theta=np.arctan2(q[:,1],q[:,0]);gaps=(theta-np.roll(theta,-1))%(2*math.pi)
    if not (np.all(gaps>0) and np.all(gaps<math.pi) and abs(float(gaps.sum())-2*math.pi)<1e-7):
        return fail('invalid_angular_coverage')
    audit=measure(m,'cube');top=audit['metrics']
    if not audit['clean'] or top['boundary_edges'] or top['euler']!=2:
        return fail('mesh_audit',nonincident_overlap=audit['nonincident_overlap'],degenerate=audit['degenerate'])
    c0=ma+center[0]*u+center[1]*v
    c=c0+d*.5
    return dict(recognized=True,reason='two_ring_cylinder',radius=radius,height=h,axis=axis.tolist(),
        center=c.tolist(),radial_error=radial,plane_error=max(pa,pb),pair_error=pair_error,
        tolerance=eps,ring_vertices=n,max_angular_gap=float(gaps.max()),
        ideal_radial_error=radius*(1-math.cos(float(gaps.max())*.5)))
def basis(axis):
    w=np.asarray(axis,dtype=float);w/=np.linalg.norm(w)
    t=np.array([1.,0.,0.]) if abs(w[0])<.9 else np.array([0.,1.,0.])
    u=np.cross(t,w);u/=np.linalg.norm(u);return np.column_stack((u,np.cross(w,u),w))
CASES=[
 ('regular8',8,1.,2.,(0,0,1),(0,0,0),None,False),
 ('translated',16,2.5,3.,(0,0,1),(4,-3,2),None,True),
 ('tilted',16,.75,4.,(1,2,3),(2,1,-2),None,True),
 ('horizontal',32,1.2,1.5,(1,0,0),(-1,2,3),None,True),
 ('uneven',8,1.7,2.2,(2,-1,3),(3,2,-1),'uneven',True),
 ('short',16,2.,.15,(1,1,1),(0,0,0),None,True),
 ('ellipse',16,1.,2.,(0,0,1),(0,0,0),'ellipse',True),
 ('cone',16,1.,2.,(0,0,1),(0,0,0),'cone',True),
 ('twist',16,1.,2.,(0,0,1),(0,0,0),'twist',True),
 ('warped',16,1.,2.,(0,0,1),(0,0,0),'warped',True),
 ('missing_side',16,1.,2.,(0,0,1),(0,0,0),'missing',True),
 ('radial_outlier',16,1.,2.,(0,0,1),(0,0,0),'outlier',True),
]
def make_case(n,r,h,axis,c,defect):
    xy=points('uneven') if defect=='uneven' else ring(n)
    V,F=cylinder(xy,(-h*.5,h*.5));W=[]
    for i,(x,y,z) in enumerate(V):
        x*=r;y*=r
        if defect=='ellipse':x*=1.2
        if defect=='cone' and i>=n:x*=.8;y*=.8
        if defect=='twist' and i>=n:
            x,y=x*math.cos(.12)-y*math.sin(.12),x*math.sin(.12)+y*math.cos(.12)
        if defect=='warped' and i==n:z+=.02
        if defect=='outlier' and i%n==0:x*=1.03;y*=1.03
        W.append(tuple(basis(axis)@np.array([x,y,z])+np.asarray(c)))
    if defect=='missing':F.pop(2)
    return mesh(W,F,'p182_cylinder')
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    rows=[]
    for name,n,r,h,axis,c,defect,shuffle in CASES:
        m=make_case(n,r,h,axis,c,defect);q=None
        try:
            original=signature(*arrays(m));q=reindex(m,331) if shuffle else m.copy()
            before=signature(*arrays(q));result=recognize(q)
            expected=defect in (None,'uneven');accurate=None
            if result['recognized']:
                unit=np.asarray(axis,dtype=float);unit/=np.linalg.norm(unit)
                accurate=bool(abs(result['radius']-r)<=1e-5 and abs(result['height']-h)<=1e-5
                    and np.linalg.norm(np.asarray(result['center'])-c)<=1e-5
                    and abs(abs(float(np.dot(result['axis'],unit)))-1)<=1e-8)
            row=dict(name=name,expected=expected,result=result,parameters_accurate=accurate,
                matched=result['recognized']==expected and (not expected or accurate is True),
                input_unchanged=signature(*arrays(q))==before,source_unchanged=signature(*arrays(m))==original,
                persistent_edit=False)
            assert row['input_unchanged'] and row['source_unchanged']
            rows.append(row);print('PHASE182_ROW',json.dumps(row,allow_nan=False),flush=True)
        finally:
            if q is not None:bpy.data.meshes.remove(q)
            bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase182_cylinder_recognition.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    summary=dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        recognized=sum(r['result']['recognized'] for r in rows),rejected=sum(not r['result']['recognized'] for r in rows),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
    print('PHASE182_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
    assert len(rows)==12 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
