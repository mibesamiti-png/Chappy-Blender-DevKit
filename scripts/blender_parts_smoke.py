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
from parts.blender.measure import mesh_world_bounds
from parts.blender.modifiers import modifier_snapshot
from parts.blender.edit_transform import translate_selected_vertices

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
checks = {'BLCTX-001': [], 'BLCTX-002': [], 'BME-001': [],
          'BLGEO-001': [], 'BLMOD-001': [], 'BME-002': []}
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
    try:
        translate_selected_vertices(bpy.context, (0.0, 0.0, 0.1))
        raise AssertionError('Edit Mode-only nudge should reject Object Mode')
    except BlenderContextError:
        checks['BME-002'].append('object_mode_rejected')
    light.select_set(False)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    counts = count_edit_selection(bpy.context)
    assert (counts.vertices, counts.edges, counts.faces) == (3, 3, 1), counts
    checks['BME-001'].append('triangle_edit_selection')

    import bmesh
    edit_bm = bmesh.from_edit_mesh(mesh)
    edit_bm.verts.ensure_lookup_table()
    # Select one vertex only and confirm topology and other vertex positions do not change.
    bpy.ops.mesh.select_all(action='DESELECT')
    vertex = edit_bm.verts[0]
    vertex.select_set(True)
    bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
    before = [tuple(v.co) for v in edit_bm.verts]
    vert_count, edge_count, face_count = len(edit_bm.verts), len(edit_bm.edges), len(edit_bm.faces)
    result = translate_selected_vertices(bpy.context, (0.0, 0.0, 0.125))
    after = [tuple(v.co) for v in edit_bm.verts]
    assert result.moved_vertices == 1
    assert abs(after[0][2] - before[0][2] - 0.125) < 1e-6
    assert after[1:] == before[1:]
    assert (len(edit_bm.verts), len(edit_bm.edges), len(edit_bm.faces)) == (vert_count, edge_count, face_count)
    assert bpy.context.mode == 'EDIT_MESH'
    checks['BME-002'].append('selected_vertex_nudge')
    before_bad = [tuple(v.co) for v in edit_bm.verts]
    try:
        translate_selected_vertices(bpy.context, (float('nan'), 0.0, 0.1))
        raise AssertionError('Expected nonfinite offset to be rejected')
    except BlenderContextError:
        pass
    assert before_bad == [tuple(v.co) for v in edit_bm.verts]
    checks['BME-002'].append('invalid_offset_rejected')
    # Reset the fixture before the later read-only geometry/matrix tests.
    # The previous test genuinely changed one vertex, so using the original
    # flat-triangle bounds without restoring it would be a false failure.
    translated_back = translate_selected_vertices(bpy.context, (0.0, 0.0, -0.125))
    assert translated_back.moved_vertices == 1
    assert [tuple(v.co) for v in edit_bm.verts] == before


    # Mesh datablocks can be out of sync while an editable BMesh is active.
    for func, part_id in ((mesh_world_bounds, 'BLGEO-001'),
                          (modifier_snapshot, 'BLMOD-001')):
        try:
            func(bpy.context)
            raise AssertionError('Expected Object Mode-only helper to reject Edit Mode')
        except BlenderContextError:
            checks[part_id].append('edit_mode_rejected')

    bpy.ops.object.mode_set(mode='OBJECT')
    obj.scale = (2.0, 3.0, 1.0)
    obj.location = (5.0, -3.0, 2.0)
    bpy.context.view_layer.update()
    original_verts = len(mesh.vertices)
    bounds = mesh_world_bounds(bpy.context)
    assert all(abs(a - b) < 1e-6 for a, b in zip(bounds.dimensions, (2, 3, 0))), bounds
    assert all(abs(a - b) < 1e-6 for a, b in zip(bounds.minimum, (5, -3, 2))), bounds
    assert bounds.vertex_count == original_verts
    checks['BLGEO-001'].append('scaled_world_bounds')

    mod = obj.modifiers.new(name='CBDK_Test_Subdivision', type='SUBSURF')
    mod.show_viewport = False
    before = (mod.name, mod.type, mod.show_viewport, mod.show_render)
    snapshot = modifier_snapshot(bpy.context)
    assert len(snapshot) == 1 and (
        snapshot[0].name, snapshot[0].type, snapshot[0].viewport, snapshot[0].render
    ) == before, snapshot
    assert (mod.name, mod.type, mod.show_viewport, mod.show_render) == before
    checks['BLMOD-001'].append('modifier_metadata_snapshot')
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
