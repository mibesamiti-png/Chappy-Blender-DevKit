"""Research only: bounded state-driven native operations and corrected subdivision contract.
Same synthetic sheet/cube, explicit goals. Not general planning or CAD-solid certification.
"""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase160_operation_contracts import fixture,measure,close
from phase161_operation_sequences import add
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
EPS=1e-5
def snap(ob,name):
    bpy.context.view_layer.update()
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
    try:
        r=measure(m,name)
        V=np.array([tuple(v.co) for v in m.vertices],dtype='<f8')
        F=[tuple(f.vertices) for f in m.polygons]
        m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
        r['corner_count']=sum(map(len,F))
        r['face_arity_histogram']={str(k):sum(len(f)==k for f in F) for k in sorted(set(map(len,F)))}
        r['sha256']=hashlib.sha256(V.tobytes()+json.dumps(F).encode()).hexdigest()
        return r,(V,F,T)
    finally:ev.to_mesh_clear()
def surface_samples(g):
    V,F,T=g;A=V[np.asarray(T)]
    samples=np.concatenate([V,A.mean(1),(A[:,0]+A[:,1])*.5,(A[:,1]+A[:,2])*.5,(A[:,2]+A[:,0])*.5])
    return samples
def distance(a,b):
    V,F,T=b;tree=BVHTree.FromPolygons([Vector(v) for v in V],T,all_triangles=True,epsilon=0.)
    samples=surface_samples(a);d=[]
    for v in samples:
        result=tree.find_nearest(Vector(v));assert result[3] is not None
        d.append(result[3])
    return max(d),len(d)
def closed(r):
    q=r['metrics'];return r['clean'] and q['boundary_edges']==0 and q['euler']==2
def slab(r):
    return closed(r) and close(r['bounds'],[[-1,-1,-.2],[1,1,0]]) and .72<=r['volume']<=.8+EPS
def rounded(r,name):
    v=.8 if name=='sheet' else 8.
    bounds=[[-1,-1,-.2],[1,1,0]] if name=='sheet' else [[-1,-1,-1],[1,1,1]]
    return closed(r) and close(r['bounds'],bounds) and .9*v<=r['volume']<v-EPS and r['oblique_faces']>=12 and all(r['axis_dirs'])
def density(before,after,g0,g1):
    q=after['metrics'];b=before['metrics']
    a,n=distance(g0,g1);c,m=distance(g1,g0)
    evidence=dict(expected_faces=before['corner_count'],old_four_times_faces=4*b['faces'],
        actual_faces=q['faces'],source_arity=before['face_arity_histogram'],sampled_surface_error=max(a,c),samples=n+m,
        volume_error=abs(after['volume']-before['volume']))
    passed=bool(closed(after) and q['faces']==before['corner_count'] and q['quads']==q['faces']
         and q['boundary_loops']==b['boundary_loops'] and q['euler']==b['euler']
         and close(after['bounds'],before['bounds']) and evidence['volume_error']<=1e-4
         and evidence['sampled_surface_error']<=1e-4)
    return passed,evidence
def next_op(name,goal,state,done):
    if goal=='unknown' or done:return None
    if not state['clean']:return None
    if goal=='rounded_slab' and name=='sheet':
        if rounded(state,name):return None
        if slab(state):return 'bevel'
        if state['metrics']['boundary_edges']>0:return 'solidify'
    if goal=='dense_rounded_cube' and name=='cube':
        if not closed(state):return None
        return 'simple_subdivide' if rounded(state,name) else 'bevel'
    return None
def execute(name,goal,prefix=(),budget=2,probe_wrong=False):
    V,F=fixture(name);m=bpy.data.meshes.new('p162');m.from_pydata(V,[],F);m.update()
    ob=bpy.data.objects.new('p162',m);bpy.context.scene.collection.objects.link(ob)
    try:
        for op in prefix:add(ob,name,op)
        state,g=snap(ob,name);initial=state['sha256'];trace=[];done=goal=='rounded_slab' and rounded(state,name)
        def trial(op):
            nonlocal state,g,done
            before=state;before_g=g
            add(ob,name,op);mod=ob.modifiers[-1];candidate,cg=snap(ob,name)
            evidence={}
            if op=='solidify':ok=slab(candidate) and not slab(before)
            elif op=='bevel':ok=rounded(candidate,name) and not rounded(before,name)
            else:ok,evidence=density(before,candidate,before_g,cg);ok=ok and rounded(before,name)
            ok=bool(ok and candidate['sha256']!=before['sha256'])
            rollback=False
            if ok:
                state,g=candidate,cg
                done=(goal=='rounded_slab' and rounded(state,name)) or (goal=='dense_rounded_cube' and op=='simple_subdivide')
            else:
                ob.modifiers.remove(mod);restored,rg=snap(ob,name)
                rollback=restored['sha256']==before['sha256'];assert rollback
                state,g=restored,rg
            trace.append(dict(op=op,accepted=ok,rollback_exact=rollback,before_sha=before['sha256'],candidate_sha=candidate['sha256'],
                              faces=candidate['metrics']['faces'],clean=candidate['clean'],evidence=evidence))
            return ok
        # Explicit negative control; counts toward budget.
        if probe_wrong and budget>0:
            assert not trial('bevel') and state['sha256']==initial
        while len(trace)<budget and not done:
            op=next_op(name,goal,state,done)
            if op is None:break
            if not trial(op):break
        status='goal_met' if done else 'preserved' if goal=='unknown' else 'needs_review'
        return dict(name=name,goal=goal,prefix=list(prefix),budget=budget,probe_wrong=probe_wrong,status=status,
                    trace=trace,initial_sha=initial,final_sha=state['sha256'],source_faces=len(F),
                    final_faces=state['metrics']['faces'],final_clean=state['clean'])
    finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    cases=[('raw_sheet','sheet','rounded_slab',(),2,False),
           ('thick_sheet','sheet','rounded_slab',('solidify',),2,False),
           ('raw_cube','cube','dense_rounded_cube',(),2,False),
           ('rounded_cube','cube','dense_rounded_cube',('bevel',),2,False),
           ('unknown','sheet','unknown',(),2,False),
           ('budget_limit','sheet','rounded_slab',(),1,False),
           ('rollback','sheet','rounded_slab',(),3,True)]
    rows=[]
    for label,name,goal,prefix,budget,probe in cases:
        r=dict(label=label,**execute(name,goal,prefix,budget,probe));rows.append(r)
        print('PHASE162_ROW',json.dumps(r,allow_nan=False),flush=True)
    by={r['label']:r for r in rows}
    assert by['unknown']['status']=='preserved' and not by['unknown']['trace'] and by['unknown']['initial_sha']==by['unknown']['final_sha']
    assert by['budget_limit']['status']=='needs_review' and len(by['budget_limit']['trace'])==1
    assert by['rollback']['trace'][0]['rollback_exact'] and not by['rollback']['trace'][0]['accepted']
    assert all(len(r['trace'])<=r['budget'] and r['final_clean'] for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start,
             surface_test='bidirectional finite samples: vertices, triangle centroids and edge midpoints; not exact Hausdorff')
    P.mkdir(exist_ok=True);(P/'phase162_state_planner.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE162_SUMMARY',json.dumps(dict(cases=len(rows),goal_met=sum(r['status']=='goal_met' for r in rows),
          operations=sum(len(r['trace']) for r in rows),rollbacks=sum(t['rollback_exact'] for r in rows for t in r['trace']),
          elapsed=out['elapsed'])),flush=True)
if __name__=='__main__':main()
