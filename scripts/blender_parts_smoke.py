"""Opt-in trusted Blender runtime smoke for CBDK-authored read-only helpers."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy

from parts.blender import (BlenderContextError, count_edit_selection,
                           require_active_mesh, selected_mesh_objects)

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new('CBDK_Parts_Test')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
mesh.update()
obj = bpy.data.objects.new('CBDK_Parts_Object', mesh)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
try:
    assert require_active_mesh(bpy.context, mode='OBJECT') is obj
    assert obj in selected_mesh_objects(bpy.context)
    try:
        count_edit_selection(bpy.context)
        raise AssertionError('Object-mode count should fail')
    except BlenderContextError:
        pass
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    counts = count_edit_selection(bpy.context)
    assert (counts.vertices, counts.edges, counts.faces) == (3, 3, 1), counts
    bpy.ops.object.mode_set(mode='OBJECT')
    assert len(obj.data.vertices) == 3 and len(obj.data.polygons) == 1
finally:
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
print('CBDK_BLENDER_SMOKE_PASS ' + json.dumps({'suite': 'parts', 'blender': bpy.app.version_string,
                                              'selection_counts': [3, 3, 1]}))
