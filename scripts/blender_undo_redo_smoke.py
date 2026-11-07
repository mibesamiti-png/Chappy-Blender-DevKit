"""Probe native Undo/Redo on one CBDK-owned generated nudge preview.

Run in a *fresh* Blender background process with factory startup.  Background
Undo may be unavailable on some versions/configurations; the report explicitly
marks that as unavailable instead of counting it as a passed Undo test.

This is never evidence that Ctrl+Z or Ctrl+Shift+Z works in the visual editor.
"""
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

import addon_utils
import bmesh
import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
# Blender does not guarantee the executed script directory is on sys.path.
# Add both the repository root (for cbdk) and scripts/ (for the trusted sibling smoke helper).
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))
from cbdk.undo_probe_report import PREFIX, build_report
from blender_modular_addon_smoke import PACKAGE, verify_zip

OBJECT_NAME = "CBDK_Native_Undo_Probe"


def current_state():
    """Reacquire BMesh after each Undo; previous RNA/BMesh references can expire."""
    obj = bpy.data.objects.get(OBJECT_NAME)
    if obj is None or bpy.context.mode != "EDIT_MESH":
        raise AssertionError("Undo/Redo changed edit mode or removed test object")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    return {
        "positions": tuple(tuple(float(axis) for axis in vert.co) for vert in bm.verts),
        "selected": tuple(bool(vert.select) for vert in bm.verts),
        "topology_counts": (len(bm.verts), len(bm.edges), len(bm.faces)),
        "edges": tuple(tuple(v.index for v in edge.verts) for edge in bm.edges),
        "faces": tuple(tuple(v.index for v in face.verts) for face in bm.faces),
        "edge_selection": tuple(bool(edge.select) for edge in bm.edges),
        "face_selection": tuple(bool(face.select) for face in bm.faces),
    }


def run_case(selected, offsets, *, prepared):
    """Native round trips; explicit pushes are a separate controlled condition."""
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    old = bpy.data.objects.get(OBJECT_NAME)
    if old is not None:
        old_mesh = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        bpy.data.meshes.remove(old_mesh)
    mesh = bpy.data.meshes.new("CBDK_Undo_Probe_Mesh")
    mesh.from_pydata([(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)], [], [(0, 1, 2)])
    mesh.update()
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    for index in selected:
        bm.verts[index].select_set(True)
    bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
    can_push = prepared and bpy.ops.ed.undo_push.poll()
    if can_push:
        if bpy.ops.ed.undo_push(message="CBDK controlled baseline") != {"FINISHED"}:
            raise AssertionError("Undo baseline push failed")
    states = [current_state()]
    for offset in offsets:
        result = bpy.ops.cbdk.modular_vertex_nudge(offset=offset)
        if result != {"FINISHED"}:
            raise AssertionError("Generated nudge operator did not finish")
        after = current_state()
        expected = dict(states[-1])
        expected["positions"] = tuple(
            tuple(value + offset[axis] if i in selected else value
                  for axis, value in enumerate(position))
            for i, position in enumerate(states[-1]["positions"]))
        if after != expected:
            raise AssertionError("Nudge changed unexpected coordinates/selection/connectivity")
        states.append(after)
        if can_push:
            if bpy.ops.ed.undo_push(message="CBDK controlled edit") != {"FINISHED"}:
                raise AssertionError("Undo edit push failed")
    # Do not mix naturally available history with prepared history claims.
    if prepared and not can_push:
        return "unavailable", "not_attempted"
    for expected in reversed(states[:-1]):
        if not bpy.ops.ed.undo.poll():
            return "unavailable", "not_attempted"
        if bpy.ops.ed.undo() != {"FINISHED"} or current_state() != expected:
            raise AssertionError("Native Undo failed exact state restoration")
    for expected in states[1:]:
        if not bpy.ops.ed.redo.poll():
            return "passed", "unavailable"
        if bpy.ops.ed.redo() != {"FINISHED"} or current_state() != expected:
            raise AssertionError("Native Redo failed exact state replay")
    return "passed", "passed"


def run(path: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    features = verify_zip(path)
    if "vertex_nudge" not in features:
        raise ValueError("Undo probe requires the generated vertex_nudge recipe")
    with tempfile.TemporaryDirectory(prefix="cbdk-undo-probe-") as folder:
        with ZipFile(path, "r") as archive:
            archive.extractall(folder)
        sys.path.insert(0, folder)
        enabled = False
        try:
            module = addon_utils.enable(PACKAGE, default_set=False, persistent=False)
            if module is None:
                raise AssertionError("Generated add-on could not be enabled")
            enabled = True

            undo, redo = run_case((0,), ((0., 0., 0.125),), prepared=False)
            cases = {}
            for name, selection, offsets in (
                ("single_vertex", (0,), ((0., 0., 0.125),)),
                ("multi_vertex_repeated", (0, 2),
                 ((0., 0., 0.125), (0.25, -0.125, 0.))),
            ):
                case_undo, case_redo = run_case(selection, offsets, prepared=True)
                cases[name] = {"undo_status": case_undo, "redo_status": case_redo,
                               "edit_steps": len(offsets)}
            # A rejected operation must leave the full current mesh unchanged.
            before = current_state()
            result = bpy.ops.cbdk.modular_vertex_nudge(offset=(0., 0., 0.))
            if result != {"CANCELLED"} or current_state() != before:
                raise AssertionError("Cancelled nudge changed mesh state")
            report = build_report(bpy.app.version_string, undo, redo, prepared_cases=cases)
            print(PREFIX + json.dumps(report, sort_keys=True), flush=True)
        finally:
            if enabled:
                addon_utils.disable(PACKAGE, default_set=False)
            sys.path.remove(folder)


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise ValueError("Expected -- <trusted-modular_nudge-preview.zip>")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise ValueError("Expected exactly one ZIP")
    run(Path(args[0]).resolve())
