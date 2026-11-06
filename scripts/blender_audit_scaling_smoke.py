"""Actual Blender scaling smoke for v0.16 edited mesh audit.

A moderate 70x70 quad grid (roughly 20k BMesh elements) avoids an artificial
tiny triangle-only benchmark. Timings and tracked Python heap peak are emitted
as observations, not claims of a universal speed guarantee.
"""
import json
import sys
import time
import tracemalloc
from pathlib import Path

# Blender --python scripts/.. does not automatically add repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bmesh
import bpy
from parts.blender import edit_audit
from parts.blender.context import BlenderContextError
from parts.blender.edit_audit import (capture_edit_snapshot, preflight_audit_size,
                                     audit_vertex_translation)
from parts.blender.edit_transform import translate_selected_vertices


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    n = 70
    points = [(float(x), float(y), 0.) for y in range(n + 1) for x in range(n + 1)]
    faces = [(
        y * (n + 1) + x,
        y * (n + 1) + x + 1,
        (y + 1) * (n + 1) + x + 1,
        (y + 1) * (n + 1) + x,
    ) for y in range(n) for x in range(n)]
    mesh = bpy.data.meshes.new("CBDK_Audit_Perf_Grid")
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("CBDK_Audit_Perf_Grid", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    first = bm.verts[0]
    first.select_set(True)
    bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
    v, e, f = preflight_audit_size(bm)
    assert (v, f) == ((n + 1) ** 2, n ** 2)
    assert v + e + f < edit_audit.MAX_AUDIT_ELEMENTS

    tracemalloc.start()
    started = time.perf_counter()
    before = capture_edit_snapshot(bm)
    captured = time.perf_counter()
    result = translate_selected_vertices(bpy.context, (0., 0., 0.125))
    finished = time.perf_counter()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result.audit.valid
    reference_diff = audit_vertex_translation(before, capture_edit_snapshot(bm),
                                              (0., 0., 0.125))
    assert result.audit == reference_diff, (result.audit, reference_diff)
    assert result.moved_vertices == 1
    assert len(result.audit.moved_vertices) == 1
    assert abs(float(bm.verts[0].co.z) - 0.125) < 1e-6
    assert (len(bm.verts), len(bm.edges), len(bm.faces)) == (v, e, f)
    # A successful nudge must not silently alter a faraway vertex.
    assert abs(float(bm.verts[-1].co.z)) < 1e-7

    # Simulate a lower configured cap on *real* BMesh, not a stub object:
    # the size guard must stop before any write/update occurs.
    original_cap = edit_audit.MAX_AUDIT_ELEMENTS
    before_reject = tuple(bm.verts[0].co)
    try:
        edit_audit.MAX_AUDIT_ELEMENTS = 100
        try:
            translate_selected_vertices(bpy.context, (0., 0., 0.125))
        except BlenderContextError as exc:
            assert "size limit" in str(exc), str(exc)
        else:
            raise AssertionError("Audit preflight did not reject oversized BMesh")
    finally:
        edit_audit.MAX_AUDIT_ELEMENTS = original_cap
    assert tuple(bm.verts[0].co) == before_reject
    assert bpy.context.mode == "EDIT_MESH"
    # Do not assert a fixed speed: CI hosts differ. Report meaningful metrics.
    report = {
        "schema_version": 1, "blender": bpy.app.version_string,
        "vertex_count": v, "edge_count": e, "face_count": f,
        "snapshot_seconds": round(captured - started, 5),
        "nudge_including_audit_seconds": round(finished - captured, 5),
        "python_peak_bytes": peak,
        "no_mutation_on_limit": True,
        "postedit_audit_passed": True,
        "preview_only": True,
    }
    print("CBDK_AUDIT_SCALING_PASS " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    run()
