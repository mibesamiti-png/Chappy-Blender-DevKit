"""Research only: bounded angular refinement of explicit unit-radius cylinder profiles.
Keep original ring coordinates exactly, compare adaptive and uniform segment counts.
No arbitrary curve reconstruction or authorization to modify protected cap topology.
"""
import json,math,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase180_cylinder_surface_contracts import ring,cylinder,profile
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase167_protected_local_bevel import signature
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
TAU=2*math.pi
CASES=[
 ('coarse8','regular8',.01,128,'ideal',False,'goal_met',24),
 ('coarse16','regular16',.01,128,'ideal',False,'goal_met',32),
 ('fine32','regular32',.01,128,'ideal',False,'goal_met',32),
 ('uneven','uneven',.01,128,'ideal',False,'goal_met',27),
 ('tight','regular8',.001,128,'ideal',False,'goal_met',72),
 ('budget','regular8',.001,64,'ideal',False,'budget_exhausted',8),
 ('cap_locked','regular8',.01,128,'ideal',True,'needs_permission',8),
 ('cap_locked_fine','regular32',.01,128,'ideal',True,'goal_met',32),
 ('preserve','regular8',.01,128,'preserve',False,'preserved',8),
 ('unknown','uneven',.01,128,'unknown',False,'preserved',8),
 ('wrong_radius','wrong_radius',.01,128,'ideal',False,'needs_review',8),
]
def points(name):
    if name=='uneven':
        return [(math.cos(TAU*t),math.sin(TAU*t)) for t in (0.,.03,.15,.30,.45,.60,.75,.90)]
    if name=='wrong_radius':return ring(8,.98)
    return ring(int(name.removeprefix('regular')))
def intervals(xy,tol):
    limit=2*math.acos(1-tol)
    angles=[math.atan2(y,x) for x,y in xy]
    gaps=[(b-a)%TAU for a,b in zip(angles,angles[1:]+angles[:1])]
    assert all(0<g<math.pi for g in gaps) and abs(sum(gaps)-TAU)<1e-10
    # Ideal angular bound, with native output independently rechecked.
    divisions=[max(1,math.ceil(g/limit)) for g in gaps]
    return angles,gaps,divisions
def refine(xy,angles,gaps,divisions):
    out=[];original_indices=[]
    for i,(a,g,k) in enumerate(zip(angles,gaps,divisions)):
        original_indices.append(len(out));out.append(xy[i])
        for j in range(1,k):
            t=a+g*j/k;out.append((math.cos(t),math.sin(t)))
    return out,original_indices
def execute(base,tol,budget,intent,locked):
    V,F=arrays(base);n=len(V)//2;xy=[v[:2] for v in V[:n]];bh=signature(V,F)
    a=profile(base,n,(-1.,1.));assert a['valid']
    row=dict(status='needs_review',selected_n=n,source_error=a['max_radial_error'],
        final_error=a['max_radial_error'],source_volume=a['volume'],final_volume=a['volume'],
        original_vertices_exact=True,attempts=0,uniform_n=None,planned_n=None,divisions=[],
        input_unchanged=True)
    if intent in ('preserve','unknown'):
        row['status']='preserved'
    elif max(abs(math.hypot(x,y)-1.) for x,y in xy)>1e-6:
        row['status']='needs_review'
    elif a['max_radial_error']<=tol:
        row['status']='goal_met'
    elif locked:
        row['status']='needs_permission'
    else:
        angles,gaps,divisions=intervals(xy,tol)
        total=sum(divisions);uniform=n*max(divisions)
        row.update(planned_n=total,uniform_n=uniform,divisions=divisions)
        if total>budget:
            row['status']='budget_exhausted'
        else:
            out,ids=refine(xy,angles,gaps,divisions)
            m=mesh(*cylinder(out),'p181_candidate')
            try:
                b=profile(m,len(out),(-1.,1.));W,G=arrays(m)
                exact=all(W[k]==V[i] and W[len(out)+k]==V[n+i] for i,k in enumerate(ids))
                row.update(attempts=1,candidate_error=b['max_radial_error'],candidate_valid=b['valid'],
                    original_vertices_exact=exact)
                if exact and b['valid'] and b['max_radial_error']<=tol:
                    row.update(status='goal_met',selected_n=len(out),final_error=b['max_radial_error'],
                        final_volume=b['volume'])
            finally:bpy.data.meshes.remove(m)
    row['input_unchanged']=signature(*arrays(base))==bh
    return row
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    rows=[]
    for name,shape,tol,budget,intent,locked,expected,expected_n in CASES:
        m=mesh(*cylinder(points(shape)),'p181_source')
        try:
            r=execute(m,tol,budget,intent,locked)
            row=dict(name=name,shape=shape,tolerance=tol,budget=budget,intent=intent,
                cap_locked=locked,expected=expected,expected_n=expected_n,
                matched=r['status']==expected and r['selected_n']==expected_n,**r)
            assert row['input_unchanged'] and row['original_vertices_exact']
            assert row['selected_n']<=budget
            if locked or intent!='ideal' or expected in ('budget_exhausted','needs_review'):assert not row['attempts']
            rows.append(row);print('PHASE181_ROW',json.dumps(row,allow_nan=False),flush=True)
        finally:bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start,
        scope='unit cylinder, explicit axis and radius, bounded angular subdivisions; not global optimality')
    P.mkdir(exist_ok=True);(P/'phase181_adaptive_cylinder_refinement.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    summary=dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        goal_met=sum(r['status']=='goal_met' for r in rows),attempts=sum(r['attempts'] for r in rows),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
    print('PHASE181_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
    assert len(rows)==11 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
