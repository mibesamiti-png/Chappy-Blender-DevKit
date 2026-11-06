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

SCRIPT_DIR = Path(__file__).resolve().parent\nREPO_ROOT = SCRIPT_DIR.parent\n# Blender does not guarantee the executed script directory is on sys.path.\n# Add both the repository root (for cbdk) and scripts/ (for the trusted sibling smoke helper).\nsys.path.insert(0, str(REPO_ROOT))\nsys.path.insert(0, str(SCRIPT_DIR))\nfrom cbdk.undo_probe_report import PREFIX, build_report\nfrom blender_modular_addon_smoke import PACKAGE, verify_zip

OBJECT_NAME = "CBDK_Native_Undo_Probe"


def current_state():
    """Reacquire BMesh after each Undo; previous RNA/BMesh references can expire."""
    obj = bpy.data.objects.get(OBJECT_NAME)
    if obj is None or bpy.context.mode != "EDIT_MESH":
        raise AssertionError("Undo/Redo changed edit mode or removed test object")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    return {
        "positions": tuple(tuple(float(axis) for axis in vert.co) for vert in bm.verts),
        "selected": tuple(bool(vert.select) for vert in bm.verts),
        "topology_counts": (len(bm.verts), len(bm.edges), len(bm.faces)),
    }


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

            mesh = bpy.data.meshes.new("CBDK_Undo_Probe_Mesh")
            mesh.from_pydata([(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)],
                             [], [(0, 1, 2)])
            mesh.update()
            obj = bpy.data.objects.new(OBJECT_NAME, mesh)
            bpy.context.scene.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="DESELECT")
            bm = bmesh.from_edit_mesh(mesh)
            bm.verts.ensure_lookup_table()
            bm.verts[0].select_set(True)
            bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
            before = current_state()

            result = bpy.ops.cbdk.modular_vertex_nudge(offset=(0., 0., 0.125))
            if result != {"FINISHED"}:
                raise AssertionError("Generated nudge operator did not finish")
            after = current_state()
            if (after["topology_counts"] != before["topology_counts"] or
                after["selected"] != before["selected"] or
                len(after["positions"]) != 3 or
                after["positions"][1:] != before["positions"][1:] or
                abs(after["positions"][0][2] - before["positions"][0][2] - 0.125) > 1e-6 or
                after["positions"][0][:2] != before["positions"][0][:2]):
                raise AssertionError("Nudge changed unexpected mesh data")

            undo, redo = "unavailable", "not_attempted"
            # The Blender native operator can be non-pollable in --background.
            # We never convert an unavailable poll into a successful Undo claim.
            if bpy.ops.ed.undo.poll():
                status = bpy.ops.ed.undo()
                if status != {"FINISHED"}:
                    raise AssertionError("Native Undo did not finish")
                restored = current_state()
                if restored != before:
                    raise AssertionError("Undo failed to restore coordinates/selection/topology")
                undo = "passed"
                redo = "unavailable"
                if bpy.ops.ed.redo.poll():
                    status = bpy.ops.ed.redo()
                    if status != {"FINISHED"}:
                        raise AssertionError("Native Redo did not finish")
                    replayed = current_state()
                    if replayed != after:
                        raise AssertionError("Redo failed to replay the expected edit")
                    redo = "passed"

            report = build_report(bpy.app.version_string, undo, redo)
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
