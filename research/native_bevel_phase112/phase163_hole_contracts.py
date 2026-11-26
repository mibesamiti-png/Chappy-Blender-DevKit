"""Research only: native Boolean hole contracts on synthetic rectangular blocks.
Through and blind holes, dimensions, volume, sampled cavity walls, and rejected-candidate rollback.
Not exact CAD, not arbitrary-mesh minimum wall thickness, not print certification.
"""
import hashlib,json,math,sys,time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase160_operation_contracts import measure,close
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
N=64
EPS=1e-4
BOX=[(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
FACES=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
TARGETS=[dict(name='center_through',xy=(0.,0.),r=.30,kind='through',floor=0.),
         dict(name='offset_through',xy=(.35,-.20),r=.25,kind='through',floor=0.),
         dict(name='blind',xy=(-.2,.1),r=.35,kind='blind',floor=.40)]
def make(name,V,F):
    m=bpy.data.meshes.new(name);m.from_pydata(V,[],F);m.update()
    ob=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(ob)
    return ob,m
def cutter(xy,r,floor):
    z0=floor if floor>0 else -.2
    v=[(xy[0]+r*math.cos(i*2*math.pi/N),xy[1]+r*math.sin(i*2*math.pi/N),z) for z in (z0,1.2) for i in range(N)]
    f=[tuple(reversed(range(N))),tuple(range(N,2*N))]
    f.extend((i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N))
    return make('p163_cutter',v,f)
def ray(tree,origin,direction):
    hit=tree.ray_cast(Vector(origin),Vector(direction),4.)
    return None if hit[0] is None else float(hit[3])
def snapshot(ob,target):
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
    try:
        r=measure(m,'cube')
        V=np.asarray([tuple(v.co) for v in m.vertices],dtype='<f8');F=[tuple(p.vertices) for p in m.polygons]
        r['sha256']=hashlib.sha256(V.tobytes()+json.dumps(F).encode()).hexdigest()
        m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
        tree=BVHTree.FromPolygons([v.co.copy() for v in m.vertices],T,all_triangles=True,epsilon=0.)
        x,y=target['xy'];R=target['r']
        # Seven interior points, four exterior points, and four cardinal cavity-wall rays.
        inside=[(x,y)]+[(x+.5*R*math.cos(i*math.pi/3),y+.5*R*math.sin(i*math.pi/3)) for i in range(6)]
        outside=[(-.9,-.9),(.9,-.9),(.9,.9),(-.9,.9)]
        def vertical(points):
            return [[ray(tree,(a,b,2.),(0,0,-1)),ray(tree,(a,b,-1.),(0,0,1))] for a,b in points]
        radii=[ray(tree,(x,y,.8),d) for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0))]
        outer=[1-x,1+x,1-y,1+y]
        walls=[None if a is None else b-a for a,b in zip(radii,outer)]
        r.update(inside_rays=vertical(inside),outside_rays=vertical(outside),radii=radii,axis_wall_estimates=walls)
        return r
    finally:ev.to_mesh_clear()
def near(a,b):
    return a is None if b is None else a is not None and abs(a-b)<=EPS
def qualify(r,t):
    q=r['metrics'];through=t['kind']=='through';R=t['r']
    area=N*.5*R*R*math.sin(2*math.pi/N)
    expected_volume=4.-area*(1.-t['floor'])
    expected_inside=(None,None) if through else (2.-t['floor'],1.)
    checks=dict(clean=r['clean'],closed=q['boundary_edges']==0,topology=q['euler']==(0 if through else 2),
        bounds=close(r['bounds'],[[-1,-1,0],[1,1,1]]),
        volume=abs(r['volume']-expected_volume)<=EPS,
        cavity=all(all(near(a,b) for a,b in zip(pair,expected_inside)) for pair in r['inside_rays']),
        outside=all(all(near(a,b) for a,b in zip(pair,(1.,1.))) for pair in r['outside_rays']),
        radius=all(near(a,R) for a in r['radii']),
        wall=all(w is not None and w>=.20-EPS for w in r['axis_wall_estimates']),
        floor=through or t['floor']>=.20)
    return checks,expected_volume
def variants(t):
    xy=t['xy'];r=t['r'];floor=t['floor']
    return [('keep',None,xy,r,floor),('exact_correct','EXACT',xy,r,floor),
            ('fast_correct','FAST',xy,r,floor),
            ('wrong_depth','EXACT',xy,r,.60 if floor==0 else 0.),
            ('wrong_radius','EXACT',xy,r*.8,floor),
            ('edge_breakout','EXACT',(.95,0.),r,floor)]
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for t in TARGETS:
        ob,m=make('p163_block',BOX,FACES)
        try:
            base=snapshot(ob,t);assert base['clean'];records=[]
            for label,solver,xy,r,floor in variants(t):
                co=cm=mod=None
                try:
                    if solver:
                        co,cm=cutter(xy,r,floor)
                        mod=ob.modifiers.new('p163_difference','BOOLEAN')
                        mod.operation='DIFFERENCE';mod.solver=solver;mod.object=co
                    a=snapshot(ob,t);checks,expected=qualify(a,t)
                    rec=dict(label=label,solver=solver,passed=all(checks.values()),checks=checks,expected_volume=expected,
                             volume=a['volume'],faces=a['metrics']['faces'],euler=a['metrics']['euler'],radii=a['radii'],
                             wall_estimates=a['axis_wall_estimates'],inside_rays=a['inside_rays'],outside_rays=a['outside_rays'],
                             sha256=a['sha256'],changed=a['sha256']!=base['sha256'])
                finally:
                    if mod is not None:ob.modifiers.remove(mod)
                    if co is not None:bpy.data.objects.remove(co,do_unlink=True);bpy.data.meshes.remove(cm)
                restored=snapshot(ob,t);rec['rollback_exact']=restored['sha256']==base['sha256']
                assert rec['rollback_exact']
                records.append(rec)
                print('PHASE163_ROW',json.dumps(dict(name=t['name'],**rec),allow_nan=False),flush=True)
            selected=next((r['label'] for r in records if r['passed'] and r['changed']),None)
            assert all(not r['passed'] for r in records if r['label'] in ('keep','wrong_depth','wrong_radius','edge_breakout'))
            rows.append(dict(target=t,records=records,selected=selected))
        finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
    out=dict(complete=True,native_executed=True,approved=False,version=bpy.app.version_string,
             wall_method='cardinal samples in fixed rectangular convex synthetic block; not arbitrary thickness',
             rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase163_hole_contracts.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE163_SUMMARY',json.dumps(dict(cases=len(rows),candidates=sum(len(r['records']) for r in rows),
        selected={r['target']['name']:r['selected'] for r in rows},qualified=sum(x['passed'] for r in rows for x in r['records']),
        rollbacks=sum(x['rollback_exact'] for r in rows for x in r['records']),elapsed=out['elapsed']),allow_nan=False),flush=True)
    assert len(rows)==3 and all(len(r['records'])==6 for r in rows)
if __name__=='__main__':main()
