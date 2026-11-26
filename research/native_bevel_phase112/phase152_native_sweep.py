"""Phase 152: bounded built-in parameter sweep. Explicit synthetic targets only."""
import json,sys,time
from pathlib import Path
import numpy as np
import bpy,bmesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase151_native_intent import fixture,goal_error,F,IDS,FIX
from phase112_native_benchmark import metrics,topology_ok
ROOT=Path(__file__).resolve().parent
def run(ref,mode,factor,iterations,preserve=False):
    m=bpy.data.meshes.new('p152');m.from_pydata(ref.tolist(),[],F);m.update()
    ob=bpy.data.objects.new('p152',m);bpy.context.scene.collection.objects.link(ob)
    try:
        if mode=='smooth':
            bm=bmesh.new()
            try:
                bm.from_mesh(m);bm.verts.ensure_lookup_table()
                for _ in range(iterations):
                    bmesh.ops.smooth_vert(bm,verts=[bm.verts[i] for i in IDS],factor=factor,use_axis_x=True,use_axis_y=True,use_axis_z=True)
                bm.to_mesh(m);m.update()
            finally:bm.free()
            return np.array([tuple(v.co) for v in m.vertices],float),[tuple(p.vertices) for p in m.polygons]
        vg=ob.vertex_groups.new(name='editable');vg.add(IDS,1.,'REPLACE')
        mod=ob.modifiers.new('laplacian','LAPLACIANSMOOTH');mod.vertex_group=vg.name
        mod.lambda_factor=factor;mod.iterations=iterations;mod.use_volume_preserve=preserve;mod.use_normalized=True
        bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
        try:return np.array([tuple(v.co) for v in em.vertices],float),[tuple(p.vertices) for p in em.polygons]
        finally:ev.to_mesh_clear()
    finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    cases=[]
    for name in ('axial_spacing','elliptic_ring','radial_ridge'):
        ref=fixture(name);base=metrics(ref,F);rows=[]
        params=[('smooth',f,n,False) for f in (.1,.25,.5,1.) for n in (1,2,4,8)]+[('laplacian',f,n,p) for f in (.1,.5,1.) for n in (1,5) for p in (False,True)]
        for mode,f,n,p in params:
            V,H=run(ref,mode,f,n,p);fixed=float(np.linalg.norm(V[FIX]-ref[FIX],axis=1).max())
            err=goal_error(name,V,ref);safe=bool(H==F and topology_ok(metrics(V,H),base) and fixed<=1e-6)
            rows.append(dict(mode=mode,factor=f,iterations=n,volume_preserve=p,fixed_error=fixed,goal_error=err,safe=safe,qualified=bool(safe and err<=.02)))
        cases.append(dict(name=name,rows=rows))
        print('PHASE152_ROW',json.dumps(dict(name=name,measured=len(rows),qualified=[r for r in rows if r['qualified']],laplacian_safe={str(p):sum(r['safe'] for r in rows if r['mode']=='laplacian' and r['volume_preserve']==p) for p in (False,True)})),flush=True)
    ops=[k for k in dir(bpy.ops.mesh) if 'circle' in k or 'space' in k or 'looptools' in k]
    out=dict(approved=False,native_executed=True,complete=True,version=bpy.app.version_string,cases=cases,mesh_operator_names=ops,elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True);(p/'phase152_native_sweep.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE152_SUMMARY',json.dumps(dict(candidates=sum(len(c['rows']) for c in cases),qualified=sum(r['qualified'] for c in cases for r in c['rows']),mesh_operator_names=ops,elapsed=out['elapsed'])),flush=True)
if __name__=='__main__':main()
