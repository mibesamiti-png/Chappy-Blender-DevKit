"""Phase 189: preserve geometric end roles after reindexing and tessellation.
Frozen Phase 188 classifier; read-only endpoint binding, not a machining tool.
A cylinder has an undirected axis and no intrinsic small/large end.
"""
import json,time,math,sys
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase188_circular_frustum_recognition import classify,build,CASES
from phase182_cylinder_recognition import REL
from phase171_planar_topology_variants import arrays
from phase170_reindexed_state_planner import reindex
from phase167_protected_local_bevel import signature

ROOT=Path(__file__).resolve().parent
FRESH=[
 ('fresh_forward',12,.35,1.2,1.7,(3,-2,1),(-1,2,3),None,'frustum'),
 ('fresh_reverse',24,1.6,.55,3.1,(-1,3,2),(2,-3,1),None,'frustum'),
 ('fresh_cylinder',12,.9,.9,1.3,(1,-2,4),(1,2,-1),None,'cylinder'),
 ('fresh_offset',12,.65,1.1,2.3,(2,1,-1),(-2,1,2),'offset','unknown'),
]
def bind(m,classifier=classify):
    V,F=arrays(m); before=signature(V,F)
    base=classifier(m)['result']; kind=base['kind']
    result=dict(kind=kind,directed_axis=None,small_end=None,large_end=None,
                axis_projector=None,reason='not_recognized')
    if kind in ('cylinder','frustum'):
        a=np.asarray(base['axis'],dtype=float)
        a/=np.linalg.norm(a)
        c=np.asarray(base['center'],dtype=float)
        h=float(base['height'])
        result['axis_projector']=np.outer(a,a).tolist()
        if kind=='cylinder':
            result['reason']='intrinsic_end_symmetry'
        else:
            r0,r1=base['radii']; eps=REL*r1
            X=np.asarray(V,dtype=float)-c
            z=X@a
            radial=np.linalg.norm(X-z[:,None]*a,axis=1)
            ends=[]
            for sign in (-1,1):
                mask=np.abs(z-sign*h*.5)<=2*eps
                if np.count_nonzero(mask)<3:break
                ends.append(dict(center=(c+sign*h*.5*a).tolist(),
                                 radius=float(np.max(radial[mask]))))
            ends.sort(key=lambda e:e['radius'])
            if (len(ends)==2 and
                abs(ends[0]['radius']-r0)<=eps and abs(ends[1]['radius']-r1)<=eps
                and ends[1]['radius']-ends[0]['radius']>2*eps):
                direction=np.asarray(ends[1]['center'])-np.asarray(ends[0]['center'])
                direction/=np.linalg.norm(direction)
                result.update(directed_axis=direction.tolist(),small_end=ends[0],
                              large_end=ends[1],reason='small_to_large')
            else:
                result['reason']='endpoint_binding_unverified'
    return dict(result=result,input_unchanged=signature(*arrays(m))==before,
                persistent_edit=False)

def matches(r,r0,r1,h,axis,c,expected):
    if r['kind']!=expected:return False
    if expected=='unknown':
        return all(r[k] is None for k in ('directed_axis','small_end','large_end','axis_projector'))
    a=np.asarray(axis,dtype=float);a/=np.linalg.norm(a)
    if np.max(np.abs(np.asarray(r['axis_projector'])-np.outer(a,a)))>2e-6:return False
    if expected=='cylinder':
        return r['reason']=='intrinsic_end_symmetry' and all(r[k] is None for k in ('directed_axis','small_end','large_end'))
    direction=a if r1>r0 else -a
    if r['reason']!='small_to_large':return False
    for key,sign,rad in [('small_end',-1,min(r0,r1)),('large_end',1,max(r0,r1))]:
        e=r[key]
        if abs(e['radius']-rad)>1e-5:return False
        if np.linalg.norm(np.asarray(e['center'])-(np.asarray(c)+sign*h*.5*direction))>1e-5:return False
    return bool(np.dot(r['directed_axis'],direction)>1-1e-8)

def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();rows=[]
    for name,n,r0,r1,h,axis,c,defect,expected in CASES+FRESH:
        for mode in ('quad','diag_a','mixed'):
            m=build(n,r0,r1,h,axis,c,defect,mode)
            try:
                for seed in (1891,1892):
                    q=reindex(m,seed)
                    try:
                        out=bind(q)
                        row=dict(name=name,mode=mode,seed=seed,expected=expected,
                                 fresh=name.startswith('fresh_'),
                                 matched=bool(matches(out['result'],r0,r1,h,axis,c,expected)),**out)
                        rows.append(row)
                        print('PHASE189_ROW',json.dumps(row,allow_nan=False),flush=True)
                    finally:bpy.data.meshes.remove(q)
            finally:bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,
             elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True)
    (p/'phase189_directional_end_roles.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE189_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        fresh_matched=sum(r['matched'] for r in rows if r['fresh']),
        preserved=sum(r['input_unchanged'] for r in rows),elapsed=out['elapsed'])),flush=True)
    assert len(rows)==96 and all(r['matched'] and r['input_unchanged'] and not r['persistent_edit'] for r in rows)
if __name__=='__main__':main()
