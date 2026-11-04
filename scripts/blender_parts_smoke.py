"""Trusted opt-in Blender runtime tests for authored CBDK parts only.

No scanned or third-party modules are imported. A single structured PASS record
is emitted after all assertions have succeeded.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from parts.blender import (
    BlenderContextError, count_edit_selection, require_active_mesh,
    selected_mesh_objects,
)

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new('CBDK_Parts_Test')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
mesh.update()
obj = bpy.data.objects.new('CBDK_Parts_Object', mesh)
bpy.context.scene.collection.objects.link(obj)
light_data = bpy.data.lights.new('CBDK_Light_Data', 'POINT')
light = bpy.data.objects.new('CBDK_Light', light_data)
bpy.context.scene.collection.objects.link(light)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
light.select_set(True)
checks = {'BLCTX-001': [], 'BLCTX-002': [], 'BME-001': []}
try:
    assert require_active_mesh(bpy.context, mode='OBJECT') is obj
    checks['BLCTX-001'].append('active_mesh_object')
    try:
        require_active_mesh(bpy.context, mode='EDIT_MESH')
        raise AssertionError('Expected wrong mode failure')
    except BlenderContextError:
        checks['BLCTX-001'].append('wrong_mode_rejected')

    selected = selected_mesh_objects(bpy.context)
    assert selected == (obj,), selected
    checks['BLCTX-002'].append('selection_excludes_non_mesh')
    assert isinstance(selected, tuple)
    checks['BLCTX-002'].append('selection_snapshot_tuple')

    try:
        count_edit_selection(bpy.context)
        raise AssertionError('Expected edit-mode requirement')
    except BlenderContextError:
        checks['BME-001'].append('object_mode_rejected')
    light.select_set(False)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    counts = count_edit_selection(bpy.context)
    assert (counts.vertices, counts.edges, counts.faces) == (3, 3, 1), counts
    checks['BME-001'].append('triangle_edit_selection')
finally:
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.objects.remove(light, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    bpy.data.lights.remove(light_data)

payload = {'schema_version': 1, 'suite': 'parts', 'blender': bpy.app.version_string,
           'part_checks': checks}
print('CBDK_BLENDER_SMOKE_PASS ' + json.dumps(payload, sort_keys=True))
