"""Research only: compare fixed short native modifier sequences, with intermediate audits.
Synthetic sheet and cube only. Explicit geometric goals, not general intent inference.
"""
import itertools,json,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase160_operation_contracts import fixture,measure,close
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
EPS=1e-5
OPS=('solidify','bevel','simple_subdivide')
def add(ob,name,op):
    if op=='solidify':
        m=ob.modifiers.new(op,'SOLIDIFY');m.thickness=.2;m.offset=-1.;m.use_rim=True
    elif op=='bevel':
        m=ob.modifiers.new(op,'BEVEL');m.width=.04 if name=='sheet' else .15
        m.segments=3;m.limit_method='ANGLE';m.angle_limit=.5235987756
    elif op=='simple_subdivide':
        m=ob.modifiers.new(op,'SUBSURF');m.subdivision_type='SIMPLE';m.levels=1;m.render_levels=1
    else:raise ValueError(op)
def snapshot(ob,name):
    bpy.context.view_layer.update()
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
    try:return measure(em,name)
    finally:ev.to_mesh_clear()
def sequence(name,ops):
    V,F=fixture(name);m=bpy.data.meshes.new('p161');m.from_pydata(V,[],F);m.update()
    ob=bpy.data.objects.new('p161',m);bpy.context.scene.collection.objects.link(ob)
    try:
        stages=[snapshot(ob,name)]
        for op in ops:
            add(ob,name,op);stages.append(snapshot(ob,name))
        return dict(ops=list(ops),stages=stages,all_clean=all(x['clean'] for x in stages))
    finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
def slab_goal(r):
    a=r['stages'][-1];q=a['metrics']
    return bool(r['all_clean'] and q['boundary_edges']==0 and q['euler']==2
        and close(a['bounds'],[[-1,-1,-.2],[1,1,0]])
        and .9*.8<=a['volume']<.8-EPS and a['oblique_faces']>=12 and all(a['axis_dirs']))
def dense_goal(r,rounded):
    a=r['stages'][-1];q=a['metrics'];b=rounded['metrics']
    return bool(r['all_clean'] and q['boundary_edges']==0 and q['euler']==2
        and close(a['bounds'],rounded['bounds'])
        and abs(a['volume']-rounded['volume'])<=1e-4
        and a['oblique_faces']>=12 and all(a['axis_dirs'])
        and q['faces']>=4*b['faces'] and q['quads']==q['faces'])
def compact(a):
    q=a['metrics'];return dict(clean=a['clean'],faces=q['faces'],quads=q['quads'],vertices=q['vertices'],
        boundary_edges=q['boundary_edges'],volume=a['volume'],bounds=a['bounds'],oblique_faces=a['oblique_faces'],
        overlap=a['nonincident_overlap'],degenerate=a['degenerate'])
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    sequences=[()]+[(x,) for x in OPS]+list(itertools.permutations(OPS,2))
    rows=[]
    for name in ('sheet','cube'):
        runs={ops:sequence(name,ops) for ops in sequences}
        rounded=runs[('bevel',)]['stages'][-1]
        for ops,r in runs.items():
            r['qualified']=slab_goal(r) if name=='sheet' else dense_goal(r,rounded)
            print('PHASE161_ROW',json.dumps(dict(name=name,ops=r['ops'],qualified=r['qualified'],
                all_clean=r['all_clean'],stages=[compact(x) for x in r['stages']]),allow_nan=False),flush=True)
        # Compare the bounded candidates; deterministic shortest qualifying sequence.
        accepted=[r for r in runs.values() if r['qualified']]
        selected=min(accepted,key=lambda r:(len(r['ops']),r['stages'][-1]['metrics']['faces'],r['ops']),default=None)
        rows.append(dict(name=name,goal='rounded_slab' if name=='sheet' else 'dense_rounded_cube',
            candidates=list(runs.values()),selected=None if selected is None else selected['ops']))
    # Two negative controls: reversed slab sequence, and unsuitable double shell.
    sheet,cube=rows
    assert not next(r for r in sheet['candidates'] if r['ops']==['bevel','solidify'])['qualified']
    assert not next(r for r in cube['candidates'] if r['ops']==['solidify'])['all_clean']
    out=dict(complete=True,native_executed=True,approved=False,version=bpy.app.version_string,
        rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase161_operation_sequences.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE161_SUMMARY',json.dumps(dict(cases=len(rows),candidates=sum(len(r['candidates']) for r in rows),
        stage_measurements=sum(len(x['stages']) for r in rows for x in r['candidates']),
        selected={r['name']:r['selected'] for r in rows},
        qualified={r['name']:sum(x['qualified'] for x in r['candidates']) for r in rows},
        elapsed=out['elapsed']),allow_nan=False),flush=True)
    assert len(rows)==2 and all(len(r['candidates'])==10 for r in rows)
if __name__=='__main__':main()
