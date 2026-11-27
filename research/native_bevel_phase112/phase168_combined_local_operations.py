"""Research only: combine local bevel and through-hole machining on a protected synthetic prism.
Fixed goals, two orders and negative controls. No user meshes or production edits.
"""
import json,math,sys,time
from pathlib import Path
import bpy
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase167_protected_local_bevel import fixture,audit,apply
from phase163_hole_contracts import make,ray,near,N
from phase160_operation_contracts import close
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
X=.5;Y=0.;R=.2;WIDTH=.1;EPS=1e-4
REMOVED=N*R*R*math.sin(2*math.pi/N)
def hole_mesh(m,x):
    V=[(x+R*math.cos(i*2*math.pi/N),Y+R*math.sin(i*2*math.pi/N),z) for z in (-1.2,1.2) for i in range(N)]
    F=[tuple(reversed(range(N))),tuple(range(N,2*N))]
    F.extend((i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N))
    co,cm=make('p168_cutter',V,F)
    ob=bpy.data.objects.new('p168_operand',m);bpy.context.scene.collection.objects.link(ob)
    try:
        mod=ob.modifiers.new('cut','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=co
        bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        result=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=False,depsgraph=bpy.context.evaluated_depsgraph_get())
        result.update()
        return result
    finally:
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.objects.remove(co,do_unlink=True);bpy.data.meshes.remove(cm)
def inspect(m,source):
    a=audit(m,source);q=a['metrics']
    m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
    tree=BVHTree.FromPolygons([v.co.copy() for v in m.vertices],T,all_triangles=True,epsilon=0.)
    points=[(X,Y)]+[(X+.5*R*math.cos(i*math.pi/3),Y+.5*R*math.sin(i*math.pi/3)) for i in range(6)]
    rays=[[ray(tree,(x,y,2.),(0,0,-1)),ray(tree,(x,y,-2.),(0,0,1))] for x,y in points]
    radii=[ray(tree,(X,Y,0.),d) for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0))]
    outside=[[ray(tree,(x,y,2.),(0,0,-1)),ray(tree,(x,y,-2.),(0,0,1))] for x,y in ((-.5,0.),(.5,.7),(.1,-.7))]
    rounding=sum(all(m.vertices[i].co.x>.8 for i in p.vertices) and .01<abs(p.normal.x)<.999 for p in m.polygons)
    a.update(hole=all(v is None for pair in rays for v in pair) and all(near(v,R) for v in radii),
        radii=radii,interior_rays=rays,exterior_ok=all(near(v,1.) for pair in outside for v in pair),
        local_round_faces=rounding,closed=q['boundary_edges']==0,
        scope_ok=a['protected_exact'] and a['fixed_error']<=EPS)
    return a
def compact(a):
    return dict(clean=a['clean'],closed=a['closed'],scope_ok=a['scope_ok'],hole=a['hole'],radii=a['radii'],
        protected=a['protected_faces_preserved'],protected_total=a['protected_faces'],fixed_error=a['fixed_error'],
        local_round_faces=a['local_round_faces'],exterior_ok=a['exterior_ok'],volume=a['volume'],euler=a['metrics']['euler'],
        faces=a['metrics']['faces'],bounds=a['bounds'],sha256=a['sha256'])
def run(base,source,ops,rounded_volume):
    m=base.copy();stages=[]
    try:
        for op in ops:
            if op in ('local_bevel','global_bevel'):
                apply(m,'right' if op=='local_bevel' else 'all',WIDTH)
            elif op in ('hole','wrong_hole'):
                n=hole_mesh(m,X if op=='hole' else -.5);bpy.data.meshes.remove(m);m=n
            else:raise ValueError(op)
            stages.append(inspect(m,source))
        a=stages[-1] if stages else inspect(m,source)
        checks=dict(intermediate_safe=all(s['clean'] and s['closed'] and s['scope_ok'] for s in stages),
            clean=a['clean'],closed=a['closed'],protected=a['scope_ok'],hole=a['hole'],exterior=a['exterior_ok'],
            rounding=a['local_round_faces']>=4,topology=a['metrics']['euler']==0,
            bounds=close(a['bounds'],[[-1,-1,-1],[1,1,1]]),
            volume=abs(a['volume']-(rounded_volume-REMOVED))<=EPS)
        return dict(ops=list(ops),checks=checks,passed=all(checks.values()),stages=[compact(s) for s in stages],final=compact(a))
    finally:bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p168_source');base.from_pydata(V,[],F);base.update()
    try:
        initial=inspect(base,source);assert initial['clean'] and initial['scope_ok'] and initial['closed']
        ref=base.copy()
        try:
            apply(ref,'right',WIDTH);rounded=inspect(ref,source)
            assert rounded['clean'] and rounded['scope_ok'] and rounded['local_round_faces']>=4
        finally:bpy.data.meshes.remove(ref)
        cases=[('keep',()),('bevel_only',('local_bevel',)),('hole_only',('hole',)),
            ('bevel_then_hole',('local_bevel','hole')),('hole_then_bevel',('hole','local_bevel')),
            ('global_then_hole',('global_bevel','hole')),('bevel_then_wrong_hole',('local_bevel','wrong_hole'))]
        rows=[]
        for name,ops in cases:
            r=dict(name=name,**run(base,source,ops,rounded['volume']))
            r['source_unchanged']=inspect(base,source)['sha256']==initial['sha256'];assert r['source_unchanged']
            rows.append(r);print('PHASE168_ROW',json.dumps(r,allow_nan=False),flush=True)
        assert all(not r['passed'] for r in rows if r['name'] not in ('bevel_then_hole','hole_then_bevel'))
        selected=next((r['name'] for r in rows if r['passed']),None)
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,selected=selected,
            removed_volume=REMOVED,reference_rounded_volume=rounded['volume'],elapsed=time.perf_counter()-start)
        P.mkdir(exist_ok=True);(P/'phase168_combined_local_operations.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        print('PHASE168_SUMMARY',json.dumps(dict(candidates=len(rows),qualified=sum(r['passed'] for r in rows),
            selected=selected,source_preserved=sum(r['source_unchanged'] for r in rows),elapsed=out['elapsed'])),flush=True)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
