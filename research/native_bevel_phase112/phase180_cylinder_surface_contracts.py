"""Research only: distinguish exact faceted surface preservation from cylinder approximation.
Fixed synthetic extruded regular polygons, explicit goals, disposable meshes.
No general curved-surface equivalence or user mesh inference.
"""
import json,math,sys,time
from pathlib import Path
from fractions import Fraction
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase160_operation_contracts import measure
from phase167_protected_local_bevel import signature
from phase173_alternate_diagonal import convex_planar
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
TOL=.01
SIZES=(8,16,32,64)
def ring(n,r=1.):
    return [(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n)) for i in range(n)]
def cylinder(xy,zs=(-1.,1.),tri=False):
    n=len(xy);V=[(x,y,z) for z in zs for x,y in xy]
    F=[tuple(reversed(range(n))),tuple(range((len(zs)-1)*n,len(zs)*n))]
    for k in range(len(zs)-1):
        for i in range(n):
            a=k*n+i;b=k*n+(i+1)%n;c=b+n;d=a+n
            F.extend([(a,b,c),(a,c,d)] if tri else [(a,b,c,d)])
    return V,F
def radial_error(xy):
    # Exact formula in real arithmetic for straight extruded side segments:
    # minimum radius attained at closest point on a segment; maximum at a vertex.
    minimum=math.inf;maximum=max(math.hypot(x,y) for x,y in xy)
    for a,b in zip(xy,xy[1:]+xy[:1]):
        dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy
        assert ll>0
        t=max(0.,min(1.,-(a[0]*dx+a[1]*dy)/ll))
        minimum=min(minimum,math.hypot(a[0]+t*dx,a[1]+t*dy))
    return dict(min_radius=minimum,max_radius=maximum,max_radial_error=max(abs(1-minimum),abs(maximum-1)))
def exact_axial(base,candidate,tri):
    V,F=arrays(base);n=len(V)//2
    xy=[v[:2] for v in V[:n]]
    W,G=arrays(candidate);expectedV,expectedF=cylinder(xy,(-1.,0.,1.),tri)
    checks=dict(vertices_exact=W==expectedV,faces_exact=G==expectedF,
                source_exact=V==cylinder(xy)[0] and F==cylinder(xy)[1],
                side_quads_convex_planar=all(convex_planar(V,f) for f in F[2:]))
    return dict(passed=all(checks.values()),checks=checks)
def profile(m,n,zs):
    V,F=arrays(m);expectedV,expectedF=cylinder([v[:2] for v in V[:n]],zs)
    # Candidate faces can be triangles for the exact axial variant.
    triF=cylinder([v[:2] for v in V[:n]],zs,True)[1]
    extruded=V==expectedV and (F==expectedF or F==triF)
    xy=[v[:2] for v in V[:n]]
    convex=all((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])>0
               for a,b,c in zip(xy,xy[1:]+xy[:1],xy[2:]+xy[:2]))
    center_inside=all(a[0]*b[1]-a[1]*b[0]>0 for a,b in zip(xy,xy[1:]+xy[:1]))
    a=measure(m,'cube');q=a['metrics']
    expected_volume=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(xy,xy[1:]+xy[:1]))*(zs[-1]-zs[0])/2
    checks=dict(extruded=extruded,convex=convex,center_inside=center_inside,clean=a['clean'],
        closed=q['boundary_edges']==0 and q['euler']==2,volume=abs(a['volume']-expected_volume)<=1e-5)
    return dict(valid=all(checks.values()),checks=checks,volume=a['volume'],vertices=q['vertices'],
                faces=q['faces'],**radial_error(xy))
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    rows=[];decisions=[];controls=[]
    for n in SIZES:
        base=mesh(*cylinder(ring(n)),'p180_source')
        try:
            V,F=arrays(base);bh=signature(V,F);xy=[v[:2] for v in V[:n]]
            original=profile(base,n,(-1.,1.));assert original['valid']
            opts=[('keep',xy,(-1.,1.),False),('axial_quads',xy,(-1.,0.,1.),False),
                  ('axial_triangles',xy,(-1.,0.,1.),True),('radial_double',ring(2*n),(-1.,1.),False),
                  ('wrong_radius',ring(n,.98),(-1.,1.),False)]
            cases=[]
            for name,points,zs,tri in opts:
                m=mesh(*cylinder(points,zs,tri),'p180_candidate')
                try:
                    a=profile(m,len(points),zs)
                    cert=exact_axial(base,m,tri) if name.startswith('axial') else None
                    same=signature(*arrays(m))==bh if name=='keep' else bool(cert and cert['passed'])
                    row=dict(n=n,name=name,profile=a,certificate=cert,
                        preserve_facets=a['valid'] and same,
                        ideal_cylinder=a['valid'] and a['max_radial_error']<=TOL,
                        volume_delta=a['volume']-original['volume'],
                        input_unchanged=signature(*arrays(base))==bh)
                    assert row['input_unchanged']
                    rows.append(row);cases.append(row);print('PHASE180_ROW',json.dumps(row,allow_nan=False),flush=True)
                finally:bpy.data.meshes.remove(m)
            for goal in ('preserve_facets','ideal_cylinder','unknown'):
                order=['keep'] if goal in ('preserve_facets','unknown') else ['keep','radial_double']
                selected=next((k for k in order if goal=='unknown' or next(r for r in cases if r['name']==k)[goal]),None)
                expected='keep' if goal!='ideal_cylinder' or n>=32 else 'radial_double' if n==16 else None
                d=dict(n=n,goal=goal,selected=selected,expected=expected,matched=selected==expected,
                    status='preserved' if goal=='unknown' else 'goal_met' if selected else 'needs_review')
                decisions.append(d);print('PHASE180_DECISION',json.dumps(d,allow_nan=False),flush=True)
            if n==16:
                for defect in ('shift_middle','missing_face','reversed_face'):
                    W,G=cylinder(xy,(-1.,0.,1.))
                    if defect=='shift_middle':
                        x,y,z=W[n];W[n]=(x+.005,y,z)
                    elif defect=='missing_face':G.pop(2)
                    else:G[2]=tuple(reversed(G[2]))
                    m=mesh(W,G,'p180_defect')
                    try:
                        cert=exact_axial(base,m,False)
                        d=dict(defect=defect,rejected=not cert['passed'],certificate=cert)
                        assert d['rejected'];controls.append(d);print('PHASE180_CONTROL',json.dumps(d,allow_nan=False),flush=True)
                    finally:bpy.data.meshes.remove(m)
            assert signature(*arrays(base))==bh
        finally:bpy.data.meshes.remove(base)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,decisions=decisions,controls=controls,
        radial_tolerance=TOL,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase180_cylinder_surface_contracts.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    summary=dict(candidates=len(rows),valid=sum(r['profile']['valid'] for r in rows),
        exact_preserve=sum(r['preserve_facets'] for r in rows),ideal=sum(r['ideal_cylinder'] for r in rows),
        decisions=len(decisions),matched=sum(r['matched'] for r in decisions),controls=sum(r['rejected'] for r in controls),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
    print('PHASE180_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
    assert len(rows)==20 and len(decisions)==12 and len(controls)==3 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
