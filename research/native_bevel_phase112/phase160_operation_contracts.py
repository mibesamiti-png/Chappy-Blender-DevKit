"""Phase 160: select native operations using explicit geometric goals.
New synthetic sheet and cube. Candidate outputs remain isolated; no production adoption.
This is a bounded operation-contract test, not natural-language intent inference.
"""
import json,sys,time
from pathlib import Path
import numpy as np
import bpy
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase112_native_benchmark import metrics
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
OPS=('keep','solidify','bevel','simple_subdivide')
EPS=1e-5
def fixture(name):
    if name=='sheet':
        return [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[(0,1,2,3)]
    return [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def measure(m,name):
    V=np.array([tuple(v.co) for v in m.vertices]);F=[tuple(f.vertices) for f in m.polygons]
    q=metrics(V,F);m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
    tree=BVHTree.FromPolygons([v.co.copy() for v in m.vertices],T,all_triangles=True,epsilon=0.)
    overlap=sum(i<j and not set(T[i])&set(T[j]) for i,j in tree.overlap(tree))
    deg=sum(t.area<=1e-12 for t in m.loop_triangles)
    A=V[np.array(T)];volume=float(abs(np.einsum('ij,ij->i',A[:,0],np.cross(A[:,1],A[:,2])).sum()/6))
    normals=np.array([tuple(f.normal) for f in m.polygons])
    oblique=int(np.sum(np.max(np.abs(normals),axis=1)<.999))
    axis_dirs=[int(np.sum(normals[:,axis]*sign>.999)) for axis in range(3) for sign in (-1,1)]
    on_surface=float(np.max(np.abs(V[:,2]))) if name=='sheet' else float(np.max(np.abs(np.max(np.abs(V),axis=1)-1.)))
    bad=('bad_boundary_vertices','nonmanifold_edges','orientation_errors','zero_area_faces','duplicate_faces','unused_vertices','bad_vertex_links')
    clean=bool(q['components']==1 and not any(q[k] for k in bad) and overlap==0 and deg==0)
    return dict(metrics=q,clean=clean,nonincident_overlap=int(overlap),degenerate=int(deg),
        bounds=[V.min(0).tolist(),V.max(0).tolist()],volume=volume,oblique_faces=oblique,axis_dirs=axis_dirs,surface_vertex_error=on_surface)
def operate(name,op):
    V,F=fixture(name);m=bpy.data.meshes.new('p160');m.from_pydata(V,[],F);m.update()
    ob=bpy.data.objects.new('p160',m);bpy.context.scene.collection.objects.link(ob)
    try:
        if op=='keep':return measure(m,name)
        if op=='solidify':
            mod=ob.modifiers.new('thickness','SOLIDIFY');mod.thickness=.2;mod.offset=-1.;mod.use_rim=True
        elif op=='bevel':
            mod=ob.modifiers.new('rounding','BEVEL');mod.width=.15;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.5235987756
        elif op=='simple_subdivide':
            mod=ob.modifiers.new('density','SUBSURF');mod.subdivision_type='SIMPLE';mod.levels=1;mod.render_levels=1
        else:raise ValueError(op)
        bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
        try:return measure(em,name)
        finally:ev.to_mesh_clear()
    finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
def close(a,b):return bool(np.max(np.abs(np.array(a)-np.array(b)))<=EPS)
def qualify(name,goal,r,base,op):
    q=r['metrics'];b=base['metrics']
    if goal in ('preserve','unknown'):return op=='keep'
    if not r['clean']:return False
    closed=q['boundary_edges']==0 and q['euler']==2
    if goal=='thickness':
        return name=='sheet' and closed and close(r['bounds'],[[-1,-1,-.2],[1,1,0]]) and abs(r['volume']-.8)<=EPS
    if goal=='round_edges':
        return name=='cube' and closed and close(r['bounds'],base['bounds']) and .9*base['volume']<=r['volume']<base['volume']-EPS and r['oblique_faces']>=12 and all(r['axis_dirs'])
    if goal=='surface_density':
        return (close(r['bounds'],base['bounds']) and r['surface_vertex_error']<=EPS and
            q['faces']==4*b['faces'] and q['quads']==q['faces'] and q['euler']==b['euler'] and
            q['boundary_loops']==b['boundary_loops'] and abs(r['volume']-base['volume'])<=EPS and not r['oblique_faces'])
    raise ValueError(goal)
def plan(name,goal):
    if goal in ('preserve','unknown'):return ('keep',)
    return {'thickness':('solidify',),'round_edges':('bevel',),'surface_density':('simple_subdivide',)}[goal]
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    goals={'sheet':('thickness','surface_density','preserve','unknown','round_edges'),
           'cube':('round_edges','surface_density','preserve','unknown','thickness')}
    rows=[];measurements={}
    for name in goals:
        opts={op:operate(name,op) for op in OPS};base=opts['keep'];assert base['clean']
        measurements[name]=opts
        for goal in goals[name]:
            valid=[op for op,r in opts.items() if qualify(name,goal,r,base,op)]
            planned=plan(name,goal);selected=next((op for op in planned if op in valid),None)
            applicable=not ((name=='sheet' and goal=='round_edges') or (name=='cube' and goal=='thickness'))
            expected={'thickness':'solidify','round_edges':'bevel','surface_density':'simple_subdivide','preserve':'keep','unknown':'keep'}[goal] if applicable else None
            row=dict(name=name,goal=goal,valid=valid,selected=selected,status='selected' if selected else 'needs_review',expected=expected,passed=selected==expected,planned=list(planned))
            rows.append(row);print('PHASE160_ROW',json.dumps(row,allow_nan=False),flush=True)
        for op,r in opts.items():
            print('PHASE160_MESH',json.dumps(dict(name=name,op=op,faces=r['metrics']['faces'],vertices=r['metrics']['vertices'],clean=r['clean'],bounds=r['bounds'],volume=r['volume'],oblique_faces=r['oblique_faces'],surface_vertex_error=r['surface_vertex_error'],boundary_edges=r['metrics']['boundary_edges']),allow_nan=False),flush=True)
    out=dict(complete=True,native_executed=True,approved=False,version=bpy.app.version_string,rows=rows,measurements=measurements,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase160_operation_contracts.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE160_SUMMARY',json.dumps(dict(cases=len(rows),mesh_evaluations=8,passed=sum(r['passed'] for r in rows),unresolved=sum(r['selected'] is None for r in rows),elapsed=out['elapsed'])),flush=True)
    assert len(rows)==10 and all(r['passed'] for r in rows)
if __name__=='__main__':main()
