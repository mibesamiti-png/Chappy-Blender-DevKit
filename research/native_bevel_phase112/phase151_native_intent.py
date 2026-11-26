"""Phase 151: compare actual Blender operations on paired synthetic modeling intents.
No inference of intent, no production adoption. All methods use the same middle ring.
"""
import json, sys, time
from pathlib import Path
import numpy as np
import bpy, bmesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase112_native_benchmark import metrics, topology_ok
ROOT=Path(__file__).resolve().parent
N=16; Z=np.linspace(0,2,9); A=np.arange(N)*2*np.pi/N
F=[(i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j) for i in range(8) for j in range(N)]
IDS=list(range(4*N,5*N)); FIX=[i for i in range(9*N) if i not in IDS]
def fixture(name):
    z=Z.copy();rx=np.ones(9);ry=rx.copy()
    if name=='axial_spacing':z[4]+=.20
    if name=='elliptic_ring':rx[4]=1.3;ry[4]=.7
    if name=='radial_ridge':rx[4]=ry[4]=1.22
    return np.array([[(rx[i]*np.cos(a),ry[i]*np.sin(a),v) for a in A] for i,v in enumerate(z)],dtype=np.float32).reshape(-1,3).astype(float)
def goal_error(name,V,ref):
    P=V[IDS]; xy=P[:,:2]; r=np.linalg.norm(xy,axis=1)
    if name=='axial_spacing':
        target=ref[IDS].copy();target[:,2]=Z[4]
        return float(np.linalg.norm(P-target,axis=1).max())
    target_radius=float(np.linalg.norm(ref[IDS,:2],axis=1).mean()) if name=='elliptic_ring' else 1.
    return float(max(abs(r-target_radius).max(),abs(P[:,2]-Z[4]).max(),np.linalg.norm(xy.mean(0))))
def operate(ref,mode):
    mesh=bpy.data.meshes.new('intent_fixture');mesh.from_pydata(ref.tolist(),[],F);mesh.update()
    ob=bpy.data.objects.new('intent_fixture',mesh);bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    try:
        if mode.startswith('smooth'):
            bm=bmesh.new()
            try:
                bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
                axes=mode!='smooth_z_8'
                for _ in range(1 if mode=='smooth_xyz_1' else 8):
                    bmesh.ops.smooth_vert(bm,verts=[bm.verts[i] for i in IDS],factor=1.,use_axis_x=axes,use_axis_y=axes,use_axis_z=True)
                bm.to_mesh(mesh);mesh.update()
            finally:bm.free()
        elif mode=='laplacian':
            vg=ob.vertex_groups.new(name='editable');vg.add(IDS,1.,'REPLACE')
            mod=ob.modifiers.new('laplacian','LAPLACIANSMOOTH');mod.vertex_group=vg.name;mod.lambda_factor=.5;mod.iterations=5;mod.use_volume_preserve=True;mod.use_normalized=True
            bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
            try:return np.array([tuple(v.co) for v in em.vertices],float),[tuple(p.vertices) for p in em.polygons]
            finally:ev.to_mesh_clear()
        elif mode=='to_sphere':
            bpy.context.scene.tool_settings.mesh_select_mode=(True,False,False)
            bpy.context.scene.tool_settings.transform_pivot_point='MEDIAN_POINT'
            for p in mesh.polygons:p.select=False
            for e in mesh.edges:e.select=False
            for v in mesh.vertices:v.select=v.index in IDS
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                status=bpy.ops.transform.tosphere(value=1.)
                if 'FINISHED' not in status:raise RuntimeError(str(status))
            finally:bpy.ops.object.mode_set(mode='OBJECT')
        elif mode=='axial_spacing':
            for i in IDS:mesh.vertices[i].co.z=Z[4]
            mesh.update()
        elif mode=='keep':pass
        else:raise ValueError(mode)
        return np.array([tuple(v.co) for v in mesh.vertices],float),[tuple(p.vertices) for p in mesh.polygons]
    finally:
        if ob.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    modes=['keep','smooth_xyz_1','smooth_xyz_8','smooth_z_8','laplacian','to_sphere','axial_spacing']
    rows=[]
    for name in ('axial_spacing','elliptic_ring','radial_ridge'):
        ref=fixture(name);base=metrics(ref,F);options=[]
        for mode in modes:
            try:
                V,H=operate(ref,mode);assert len(V)==len(ref)
                delta=np.linalg.norm(V-ref,axis=1);q=metrics(V,H);P=V[IDS];rr=np.linalg.norm(P[:,:2],axis=1);e=np.linalg.norm(np.roll(P,-1,axis=0)-P,axis=1)
                fixed=float(delta[FIX].max());err=goal_error(name,V,ref)
                options.append(dict(mode=mode,ok=bool(topology_ok(q,base) and H==F and fixed<=1e-6),fixed_error=fixed,goal_error=err,preserve_error=float(delta.max()),radial_spread=float(np.ptp(rr)),ring_edge_ratio=float(e.max()/e.min())))
            except Exception as exc:options.append(dict(mode=mode,ok=False,error=repr(exc)))
        valid=[r for r in options if r['ok']];assert valid and valid[0]['mode']=='keep'
        # Explicit target, not intent inference. A 0.02 tolerance is an experimental goal only.
        good=[r for r in valid if r['goal_error']<=.02]
        selected=min(good,key=lambda r:(r['goal_error'],r['preserve_error']))['mode'] if good else None
        preserve=min(valid,key=lambda r:r['preserve_error'])['mode']
        row=dict(name=name,options=options,explicit_target=selected,preserve=preserve,unknown='keep')
        rows.append(row);print('PHASE151_ROW',json.dumps(row,allow_nan=False),flush=True)
    out=dict(approved=False,native_executed=True,complete=True,version=bpy.app.version_string,rows=rows,elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True);(p/'phase151_native_intent.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE151_SUMMARY',json.dumps(dict(cases=len(rows),candidates=sum(len(r['options']) for r in rows),errors=sum('error' in x for r in rows for x in r['options']),elapsed=out['elapsed'])),flush=True)
if __name__=='__main__':main()
