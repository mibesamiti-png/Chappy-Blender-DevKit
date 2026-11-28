"""Probe native Undo/Redo on one CBDK-owned generated nudge preview.

Run in a *fresh* Blender background process with factory startup.  Background
Undo may be unavailable on some versions/configurations; the report explicitly
marks that as unavailable instead of counting it as a passed Undo test.

This is never evidence that Ctrl+Z or Ctrl+Shift+Z works in the visual editor.
"""
import hashlib
import json
import os
import subprocess
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
from cbdk.undo_probe_report import PREFIX, R25_PREFIX, build_report, validate_grouped_observation
from blender_modular_addon_smoke import PACKAGE, verify_zip

OBJECT_NAME = "CBDK_Native_Undo_Probe"


def current_state():
    """Reacquire BMesh after each Undo; previous RNA/BMesh references can expire."""
    obj = bpy.data.objects.get(OBJECT_NAME)
    if (obj is None or bpy.context.mode != "EDIT_MESH"
            or bpy.context.active_object != obj
            or len(bpy.context.objects_in_mode_unique_data) != 1):
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
    for other in tuple(bpy.context.selected_objects):
        other.select_set(False)
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
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


def probe_registered_fixture(module):
    """Internal synthetic CI probe for an already registered authored addon.

    Never installs or enables anything. Caller owns the isolated fixture and
    must not reuse RNA/BMesh references after undo. Leave the addon registered
    and remove only this probe's object; restore synthetic scene context.
    """
    if (not bpy.app.background or bpy.context.mode != "OBJECT"
            or "vertex_nudge" not in module._FEATURE_IDS
            or not module._CLASSES or any(not cls.is_registered for cls in module._CLASSES)
            or not hasattr(bpy.types.Scene, "cbdk_modular_result")
            or bpy.data.objects.get(OBJECT_NAME) is not None
            or bpy.data.meshes.get("CBDK_Undo_Probe_Mesh") is not None):
        raise AssertionError("Undo probe requires an isolated registered synthetic fixture")
    original_active = bpy.context.active_object
    active_name = original_active.name if original_active is not None else None
    selected_names = {obj.name for obj in bpy.context.selected_objects}
    select_mode = tuple(bpy.context.tool_settings.mesh_select_mode)
    previous_result = bpy.context.scene.cbdk_modular_result
    try:
        # Natural condition always precedes any explicit push in this probe.
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
        before = current_state()
        if (bpy.ops.cbdk.modular_vertex_nudge(offset=(0., 0., 0.)) != {"CANCELLED"}
                or current_state() != before):
            raise AssertionError("Cancelled zero nudge changed mesh state")
        bpy.ops.mesh.select_all(action="DESELECT")
        before = current_state()
        if (any(before["selected"]) or any(before["edge_selection"]) or any(before["face_selection"])
                or bpy.ops.cbdk.modular_vertex_nudge(offset=(0., 0., .125)) != {"CANCELLED"}
                or current_state() != before):
            raise AssertionError("Cancelled empty selection nudge changed mesh state")
        report = build_report(bpy.app.version_string, undo, redo, prepared_cases=cases)
    finally:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        # Undo can invalidate every previous reference, including scene/mesh.
        obj = bpy.data.objects.get(OBJECT_NAME)
        if obj is not None:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)
        # All three native versions exposed a transient None in the view
        # layer immediately after object removal. Update before reacquiring
        # live scene objects by name; never reuse the removed RNA reference.
        bpy.context.view_layer.update()
        view_objects = bpy.context.view_layer.objects
        for obj in tuple(bpy.context.scene.objects):
            live = view_objects.get(obj.name)
            if live is not None:
                live.select_set(live.name in selected_names)
        restored_active = view_objects.get(active_name) if active_name is not None else None
        if active_name is not None and restored_active is None:
            raise AssertionError("Undo probe original active object missing")
        view_objects.active = restored_active
        bpy.context.tool_settings.mesh_select_mode = select_mode
        bpy.context.scene.cbdk_modular_result = previous_result
        bpy.context.view_layer.update()
    if (bpy.data.objects.get(OBJECT_NAME) is not None
            or bpy.data.meshes.get("CBDK_Undo_Probe_Mesh") is not None
            or any(not cls.is_registered for cls in module._CLASSES)
            or {obj.name for obj in bpy.context.selected_objects} != selected_names
            or (bpy.context.active_object.name if bpy.context.active_object else None) != active_name
            or tuple(bpy.context.tool_settings.mesh_select_mode) != select_mode
            or bpy.context.scene.cbdk_modular_result != previous_result):
        raise AssertionError("Undo probe cleanup or addon registration failed")
    return report


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

            report = probe_registered_fixture(module)
            print(PREFIX + json.dumps(report, sort_keys=True), flush=True)
        finally:
            if enabled:
                addon_utils.disable(PACKAGE, default_set=False)
            sys.path.remove(folder)


def run_grouped_specialist():
    """Fresh internal CI subprocess, using the existing fixed Extension verifier."""
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    from test_ui_recipe_r17 import make_r23_recipe
    from cbdk.extension_recipe_preview import write_recipe_extension
    with tempfile.TemporaryDirectory(prefix="cbdk-r25-undo-") as folder:
        root = Path(folder).resolve()
        archive = root / "authored.zip"
        write_recipe_extension(make_r23_recipe("grouped"), archive, preview_unapproved=True)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        env = dict(os.environ)
        for name in ("RESOURCES", "CONFIG", "SCRIPTS", "EXTENSIONS", "DATAFILES"):
            directory = root / name.lower()
            directory.mkdir()
            env["BLENDER_USER_" + name] = str(directory)
        env["CBDK_R19_TEMP"] = str(root)
        env["CBDK_R23_CASE"] = "grouped"
        process = subprocess.run(
            [bpy.app.binary_path, "--background", "--factory-startup", "--disable-autoexec",
             "--offline-mode", "--python-exit-code", "7", "--python",
             str(REPO_ROOT / "tests/blender_r25_grouped_undo.py")],
            env=env, capture_output=True, text=True, timeout=120)
        records = [line[len(R25_PREFIX):] for line in process.stdout.splitlines()
                   if line.startswith(R25_PREFIX)]
        if process.returncode != 0 or len(records) != 1:
            # Fixed synthetic child only; preserve bounded diagnostic for CI.
            print((process.stdout + "\n" + process.stderr)[-6000:], flush=True)
            raise AssertionError("R25 fixed grouped Extension Undo probe failed")
        report = validate_grouped_observation(json.loads(records[0]))
        if (report["artifact_sha256"] != digest
                or report["blender_version"] != ".".join(map(str, bpy.app.version))
                or hashlib.sha256(archive.read_bytes()).hexdigest() != digest):
            raise AssertionError("R25 grouped artifact or version mismatch")
        print(R25_PREFIX + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise ValueError("Expected -- <trusted-modular_nudge-preview.zip>")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise ValueError("Expected exactly one ZIP")
    run(Path(args[0]).resolve())
    run_grouped_specialist()
