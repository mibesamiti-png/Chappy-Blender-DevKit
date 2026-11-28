"""Optional Blender-only adapters. Operate on temporary authored datablocks."""
from .geometry import Mesh


def snapshot(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    try:
        data.calc_loop_triangles()
        return Mesh([tuple(obj.matrix_world @ v.co) for v in data.vertices],
                    [tuple(t.vertices) for t in data.loop_triangles])
    finally:
        evaluated.to_mesh_clear()


def join(mesh_a, mesh_b, method='exact', voxel_size=0.15):
    """Return a detached mesh; never change caller objects, selection or mode."""
    import bpy
    import math
    if method not in {'exact', 'voxel'}:
        raise ValueError('unknown joining backend')
    if not math.isfinite(voxel_size) or voxel_size <= 0:
        raise ValueError('positive voxel size required')
    objects, datablocks = [], []
    try:
        def create(mesh):
            data = bpy.data.meshes.new('CBDK_RESEARCH_TEMP')
            datablocks.append(data)
            data.from_pydata(mesh.vertices.tolist(), [], mesh.faces.tolist())
            data.update()
            obj = bpy.data.objects.new('CBDK_RESEARCH_TEMP', data)
            objects.append(obj)
            bpy.context.scene.collection.objects.link(obj)
            return obj
        if method == 'exact':
            a, b = create(mesh_a), create(mesh_b)
            modifier = a.modifiers.new('research union', 'BOOLEAN')
            modifier.operation = 'UNION'
            modifier.solver = 'EXACT'
            modifier.use_self = True
            modifier.object = b
        else:
            import numpy as np
            a = create(Mesh(np.vstack((mesh_a.vertices, mesh_b.vertices)),
                            np.vstack((mesh_a.faces, mesh_b.faces+len(mesh_a.vertices)))))
            # Bound grid dimensions before asking the native backend to allocate.
            dimensions = np.ceil(np.ptp(np.vstack((mesh_a.vertices, mesh_b.vertices)), axis=0)/voxel_size)+3
            if np.prod(dimensions) > 2000000:
                raise ValueError('voxel grid budget exceeded')
            modifier = a.modifiers.new('research voxel union', 'REMESH')
            modifier.mode = 'VOXEL'
            modifier.voxel_size = voxel_size
            modifier.use_smooth_shade = False
        bpy.context.view_layer.update()
        return snapshot(a, bpy.context.evaluated_depsgraph_get())
    finally:
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in datablocks:
            if data.users == 0:
                bpy.data.meshes.remove(data)
