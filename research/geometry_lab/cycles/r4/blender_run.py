"""Run frozen development + holdout in factory-startup; no user model IO."""
import sys,json,time,hashlib,argparse
from pathlib import Path
from statistics import median
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
import bpy,bmesh,numpy as np
from cbdk_geometry import Mesh
from cbdk_geometry.bridge import bridge_loops
import importlib.util
_spec=importlib.util.spec_from_file_location("geometry_lab_r4_fixtures",Path(__file__).with_name("fixtures.py"))
_fixtures=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_fixtures)
cases=_fixtures.cases
from benchmark import source_hashes


def native(a,b):
    bm=bmesh.new()
    try:
        va=[bm.verts.new(v) for v in a];vb=[bm.verts.new(v) for v in b]
        edges=[]
        for vs in (va,vb):
            for i in range(len(vs)):edges.append(bm.edges.new((vs[i],vs[(i+1)%len(vs)])))
        bmesh.ops.bridge_loops(bm,edges=edges,use_pairs=False,use_cyclic=False,use_merge=False,twist_offset=0)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bm.verts.index_update()
        return Mesh([list(v.co) for v in bm.verts],[[v.index for v in f.verts] for f in bm.faces])
    finally:bm.free()


def run():
    rows=[];scene=(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.context.selected_objects))
    for split in ('development','holdout'):
        for c in cases(split):
            # Equal numerical inputs: all backends receive coordinates rounded
            # to Blender's float32 storage before timing.
            a=c['a'].astype(np.float32).astype(float);b=c['b'].astype(np.float32).astype(float)
            for method in ('index','phase','dp','blender_native'):
                samples=[];row=dict(name=c['name'],split=split,method=method)
                try:
                    meshes=[]
                    for _ in range(3):
                        start=time.perf_counter()
                        mesh=native(a,b) if method=='blender_native' else bridge_loops(a,b,method)['mesh']
                        samples.append(time.perf_counter()-start);meshes.append(mesh)
                    assert all(np.array_equal(meshes[0].vertices,m.vertices) and np.array_equal(meshes[0].faces,m.faces) for m in meshes)
                    row.update(status='generated',vertices=mesh.vertices.tolist(),faces=mesh.faces.tolist(),samples_seconds=samples,median_seconds=median(samples))
                except Exception as exc:row.update(status='failed',reason=type(exc).__name__+': '+str(exc))
                rows.append(row)
    assert scene==(set(bpy.data.objects),set(bpy.data.meshes),set(bpy.context.selected_objects))
    return dict(synthetic_only=True,blender=bpy.app.version_string,numpy=np.__version__,
                source_sha256=source_hashes(),fixture_sha256=hashlib.sha256((root/'cycles/r4/fixtures.py').read_bytes()).hexdigest(),cases=rows,scene_preserved=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    result=run();path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(result,f)
    print('R4 generated',len(result['cases']),'Blender',result['blender'])
