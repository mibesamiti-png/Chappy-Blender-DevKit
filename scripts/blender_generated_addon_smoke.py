"""Trusted end-to-end generated addon smoke test in real Blender.

Run with --background --factory-startup --python-exit-code 7:
blender --background --factory-startup --python-exit-code 7 \
    --python scripts/blender_generated_addon_smoke.py -- dist/CBDK_Mesh_Inspector_Preview.zip

Temporarily unpacks the allowlisted package, activates it with addon_utils,
exercises Object/Edit Mode and unregisters without touching user startup files.
"""
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

import addon_utils
import bpy


PACKAGE = "cbdk_mesh_inspector_preview"
EXPECTED = {
    f"{PACKAGE}/__init__.py",
    f"{PACKAGE}/helpers/__init__.py",
    f"{PACKAGE}/helpers/context.py",
    f"{PACKAGE}/helpers/edit_mesh.py",
    f"{PACKAGE}/CBDK_BUILD_INFO.json",
    f"{PACKAGE}/README.txt",
}


def assert_addon_zip(path):
    with ZipFile(path, "r") as archive:
        assert set(archive.namelist()) == EXPECTED, archive.namelist()
        for info in archive.infolist():
            assert info.filename.startswith(PACKAGE + "/")
            assert not any(part in ("", ".", "..") for part in info.filename.split("/"))
            assert not ((info.external_attr >> 16) & 0o170000) == 0o120000
        metadata = json.loads(archive.read(f"{PACKAGE}/CBDK_BUILD_INFO.json"))
        assert metadata["preview_only"] is True
        assert metadata["approved"] is False
        assert metadata["redistribution_cleared"] is False


def smoke(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    checks = []
    assert_addon_zip(path)
    checks.append("safe_zip_structure")

    with tempfile.TemporaryDirectory(prefix="cbdk-addon-smoke-") as tmp:
        with ZipFile(path, "r") as archive:
            archive.extractall(tmp)
        sys.path.insert(0, tmp)
        try:
            module = addon_utils.enable(PACKAGE, default_set=False, persistent=False)
            assert module is not None, "addon_utils.enable returned None"
            assert hasattr(bpy.types, "VIEW3D_PT_cbdk_mesh_inspector")
            assert hasattr(bpy.types.Scene, "cbdk_mesh_inspector_result")
            checks.append("addon_enable_panel")

            mesh = bpy.data.meshes.new("CBDK_Triangle")
            mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
            mesh.update()
            obj = bpy.data.objects.new("CBDK_Test_Mesh", mesh)
            bpy.context.scene.collection.objects.link(obj)
            lightdata = bpy.data.lights.new("CBDK_Light", "POINT")
            light = bpy.data.objects.new("CBDK_Light", lightdata)
            bpy.context.scene.collection.objects.link(light)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            light.select_set(True)

            assert bpy.ops.cbdk.inspect_mesh_selection() == {"FINISHED"}
            status = bpy.context.scene.cbdk_mesh_inspector_result
            assert "1 selected mesh(es)" in status and "CBDK_Test_Mesh" in status, status
            assert bpy.context.mode == "OBJECT" and light.select_get() and obj.select_get()
            checks.append("object_mode_read_only")

            light.select_set(False)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            assert bpy.ops.cbdk.inspect_mesh_selection() == {"FINISHED"}
            status = bpy.context.scene.cbdk_mesh_inspector_result
            assert "V=3 E=3 F=1" in status, status
            assert bpy.context.mode == "EDIT_MESH", bpy.context.mode
            checks.append("edit_mode_counts_no_mode_change")

            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.context.view_layer.objects.active = None
            assert bpy.ops.cbdk.inspect_mesh_selection() == {"CANCELLED"}
            checks.append("missing_mesh_cancelled")

            addon_utils.disable(PACKAGE, default_set=False)
            assert not hasattr(bpy.types, "VIEW3D_PT_cbdk_mesh_inspector")
            assert not hasattr(bpy.types.Scene, "cbdk_mesh_inspector_result")
            checks.append("addon_disable_cleanup")
        finally:
            if PACKAGE in sys.modules:
                try:
                    addon_utils.disable(PACKAGE, default_set=False)
                except Exception:
                    pass
            sys.path.remove(tmp)

    print("CBDK_GENERATED_ADDON_PASS " + json.dumps({
        "schema_version": 1, "addon": PACKAGE,
        "blender": bpy.app.version_string, "checks": checks,
        "approved": False, "preview_only": True,
    }, sort_keys=True))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("Expected -- followed by the generated ZIP filename")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Exactly one generated ZIP path required")
    smoke(Path(args[0]).resolve())
