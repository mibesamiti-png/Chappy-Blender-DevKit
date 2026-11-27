"""Research only: use recognized cylinder parameters for bounded adaptive refinement.
Two-cap synthetic cylinder family; retain original coordinates in an isolated candidate.
Recognition alone never authorizes edits. Radial bound includes endpoint residuals.
"""
import json,math,sys,time
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase182_cylinder_recognition import CASES,make_case,recognize
from phase170_reindexed_state_planner import reindex
from phase176_split_edge_normalization import mesh
from phase171_planar_topology_variants import arrays
from phase167_protected_local_bevel import signature
from phase180_cylinder_surface_contracts import cylinder
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
TAU=2*math.pi
def extract(m,r):
    V,F=arrays(m);V=np.asarray(V,dtype=float)
    caps=[f for f in F if len(f)>=8];a,b=caps
    axis=np.asarray(r['axis']);center=np.asarray(r['center']);radius=r['radius'];h=r['height']
    a=tuple(reversed(a));A=V[list(a)];B0=V[list(b)]
    d=np.linalg.norm(A[:,None,:]+axis*h-B0[None,:,:],axis=2)
    ids=np.argmin(d,axis=1);B=B0[ids];assert len(set(map(int,ids)))==len(a)
    c0=center-axis*h*.5;c1=center+axis*h*.5
    u=A[0]-c0;u-=axis*np.dot(u,axis);u/=np.linalg.norm(u);v=np.cross(axis,u)
    xy=np.column_stack(((A-c0)@u,(A-c0)@v))
    theta=np.arctan2(xy[:,1],xy[:,0]);gaps=(np.roll(theta,-1)-theta)%TAU
    assert np.all(gaps>0) and np.all(gaps<math.pi) and abs(float(gaps.sum())-TAU)<1e-7
    return A,B,c0,c1,u,v,theta,gaps
def bound(A,B,c0,c1,u,v,theta,gaps,r):
    ideal=r*(np.cos(theta)[:,None]*u+np.sin(theta)[:,None]*v)
    axis=np.cross(u,v)
    residual=[]
    for Q,c in ((A,c0),(B,c1)):
        D=Q-c-ideal;D-=np.outer(D@axis,axis)
        residual.append(float(np.max(np.linalg.norm(D,axis=1))))
    # Corresponding ideal side triangles lie between the chord and circular arc.
    # Any convex combination of endpoint errors is bounded by the max error.
    e=max(residual);sag=r*(1-math.cos(float(max(gaps))*.5))
    return dict(bound=sag+e,endpoint_error=e,sag=sag)
def execute(m,tol,budget,intent,locked):
    V,F=arrays(m);bh=signature(V,F);r=recognize(m)
    out=dict(recognition=r,status='needs_review',attempts=0,selected_n=None,planned_n=None,
        source_bound=None,final_bound=None,original_vertices_exact=True,input_unchanged=True)
    if not r['recognized']:
        if intent in ('unknown','preserve'):out['status']='preserved'
        return out
    A,B,c0,c1,u,v,theta,gaps=extract(m,r);radius=r['radius'];n=len(A)
    initial=bound(A,B,c0,c1,u,v,theta,gaps,radius)
    out.update(selected_n=n,source_bound=initial['bound'],final_bound=initial['bound'],source_error=initial)
    if intent in ('unknown','preserve'):out['status']='preserved'
    elif initial['bound']<=tol:out['status']='goal_met'
    elif locked:out['status']='needs_permission'
    elif tol<=initial['endpoint_error']+1e-6:out['status']='needs_review'
    else:
        usable=(tol-initial['endpoint_error']-1e-6)/radius
        limit=2*math.acos(max(-1.,1-usable))
        div=[max(1,math.ceil(float(g)/limit)) for g in gaps]
        total=sum(div);out.update(planned_n=total,uniform_n=n*max(div),divisions=div)
        if total>budget:out['status']='budget_exhausted'
        else:
            low=[];high=[];angles=[];old=[]
            for i,(t,g,k) in enumerate(zip(theta,gaps,div)):
                old.append(len(low));low.append(tuple(A[i]));high.append(tuple(B[i]));angles.append(float(t))
                for j in range(1,k):
                    a=float(t+g*j/k);p=radius*(math.cos(a)*u+math.sin(a)*v)
                    low.append(tuple(c0+p));high.append(tuple(c1+p));angles.append(a)
            _,faces=cylinder([(0.,0.)]*total)
            candidate=mesh(low+high,faces,'p183_candidate')
            try:
                W,G=arrays(candidate);W=np.asarray(W);theta2=np.asarray(angles);gap2=(np.roll(theta2,-1)-theta2)%TAU
                exact=all(np.array_equal(W[k],A[i]) and np.array_equal(W[k+total],B[i]) for i,k in enumerate(old))
                b=bound(W[:total],W[total:],c0,c1,u,v,theta2,gap2,radius)
                rr=recognize(candidate)
                dimensions=bool(rr['recognized'] and abs(rr['radius']-radius)<=1e-5 and abs(rr['height']-r['height'])<=1e-5
                    and np.linalg.norm(np.asarray(rr['center'])-np.asarray(r['center']))<=1e-5
                    and abs(abs(float(np.dot(rr['axis'],r['axis'])))-1)<=1e-8)
                out.update(attempts=1,candidate_recognition=rr,candidate_bound=b,original_vertices_exact=exact,dimensions_preserved=dimensions)
                if exact and dimensions and b['bound']<=tol:
                    out.update(status='goal_met',selected_n=total,final_bound=b['bound'])
            finally:bpy.data.meshes.remove(candidate)
    out['input_unchanged']=signature(*arrays(m))==bh
    return out
TESTS=[
 ('regular8','regular8',.01,128,'ideal',False,'goal_met'),
 ('translated','translated',.01,128,'ideal',False,'goal_met'),
 ('tilted','tilted',.01,128,'ideal',False,'goal_met'),
 ('horizontal','horizontal',.01,128,'ideal',False,'goal_met'),
 ('uneven','uneven',.01,128,'ideal',False,'goal_met'),
 ('short','short',.01,128,'ideal',False,'goal_met'),
 ('budget','regular8',.001,64,'ideal',False,'budget_exhausted'),
 ('locked','tilted',.01,128,'ideal',True,'needs_permission'),
 ('unknown','uneven',.01,128,'unknown',False,'preserved'),
 ('preserve','translated',.01,128,'preserve',False,'preserved'),
 ('ellipse','ellipse',.01,128,'ideal',False,'needs_review'),
 ('cone','cone',.01,128,'ideal',False,'needs_review'),
 ('twist','twist',.01,128,'ideal',False,'needs_review'),
 ('outlier','radial_outlier',.01,128,'ideal',False,'needs_review'),
]
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    rows=[];cases={c[0]:c for c in CASES}
    for label,name,tol,budget,intent,locked,expected in TESTS:
        _,n,r,h,axis,c,defect,_=cases[name]
        m=make_case(n,r,h,axis,c,defect);q=None
        try:
            bh=signature(*arrays(m));q=reindex(m,743);qh=signature(*arrays(q))
            result=execute(q,tol,budget,intent,locked)
            row=dict(name=label,fixture=name,tolerance=tol,budget=budget,intent=intent,locked=locked,
                expected=expected,matched=result['status']==expected,**result)
            assert signature(*arrays(q))==qh and signature(*arrays(m))==bh
            assert row['input_unchanged'] and row['original_vertices_exact']
            if expected!='goal_met':assert row['attempts']==0
            if row['status']=='goal_met':assert row['final_bound']<=tol and row['selected_n']<=budget
            rows.append(row);print('PHASE183_ROW',json.dumps(row,allow_nan=False),flush=True)
        finally:
            if q is not None:bpy.data.meshes.remove(q)
            bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase183_recognize_and_refine.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    summary=dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        goal_met=sum(r['status']=='goal_met' for r in rows),attempts=sum(r['attempts'] for r in rows),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])
    print('PHASE183_SUMMARY',json.dumps(summary,allow_nan=False),flush=True)
    assert len(rows)==14 and all(r['input_unchanged'] for r in rows)
if __name__=='__main__':main()
