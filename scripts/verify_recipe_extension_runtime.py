"""Internal CI-only Blender subprocess. Not a general installer."""
import io
import os
from pathlib import Path
import sys
from zipfile import ZipFile

import addon_utils
import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cbdk.extension_authored_fixture import FIXTURE_ID
from cbdk.extension_recipe_preview import ci_recipe, build_recipe_extension_bytes
from cbdk.extension_preflight import MAX_ARCHIVE_BYTES


def verify():
    case = os.environ["CBDK_R23_CASE"]
    recipe = ci_recipe(case)
    root = Path(os.environ["CBDK_R19_TEMP"]).resolve()
    config = Path(os.environ["BLENDER_USER_CONFIG"]).resolve()
    if not config.is_relative_to(root) or not root.is_dir() or bpy.app.online_access:
        raise AssertionError("R23 runtime is not isolated/offline")
    if not Path(bpy.utils.user_resource("CONFIG")).resolve().is_relative_to(root):
        raise AssertionError("R23 Blender config escaped isolation")
    archive_path = root / "authored.zip"
    with archive_path.open("rb") as stream:
        blob = stream.read(MAX_ARCHIVE_BYTES + 1)
    # A supplied path or hash cannot authorize code execution. Rebuild the
    # fixed authored recipe inside this trusted checkout and compare bytes.
    if blob != build_recipe_extension_bytes(recipe, preview_unapproved=True):
        raise AssertionError("R23 runtime input differs from fixed authored generation")
    directory = root / "local_repo"
    directory.mkdir()
    package = directory / FIXTURE_ID
    package.mkdir()
    with ZipFile(io.BytesIO(blob)) as archive:
        for name in archive.namelist():
            target = package / name
            if not target.resolve().is_relative_to(package):
                raise AssertionError("R23 unsafe staging member")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(archive.read(name))
    # Explicit manual staging into a real Blender local Extension repository.
    # This does not claim that the official install-files operator ran.
    result = bpy.ops.preferences.extension_repo_add(
        name="CBDK R23 isolated fixture", type="LOCAL",
        use_custom_directory=True, custom_directory=str(directory),
        use_sync_on_startup=False)
    if result != {"FINISHED"}:
        raise AssertionError("R23 local Extension repository registration failed")
    repos = bpy.context.preferences.extensions.repos
    matches = [repo for repo in repos if Path(repo.directory).resolve() == directory]
    if len(matches) != 1:
        raise AssertionError("R23 local Extension repository not found")
    repo = matches[0]
    namespace = "bl_ext." + repo.module + "." + FIXTURE_ID
    if addon_utils.check(namespace)[1] or hasattr(bpy.types.Scene, "cbdk_modular_result"):
        raise AssertionError("R23 preexisting fixture registration")
    addon_utils.modules_refresh()
    module = addon_utils.enable(namespace, default_set=True, persistent=False)
    if module is None:
        raise AssertionError("R23 Extension enable failed")
    classes = tuple(module._CLASSES)
    try:
        if (module.__name__ != namespace or
                Path(module.__file__).resolve() != package / "__init__.py" or
                not addon_utils.check(namespace)[1] or
                bpy.context.preferences.addons.get(namespace) is None or
                set(module._FEATURE_IDS) != set(recipe["features"]) or
                any(not c.is_registered for c in classes)):
            raise AssertionError("R23 native Extension registration mismatch")
        mesh = bpy.data.meshes.new("CBDK R23 asymmetric")
        mesh.from_pydata([(-2,-1,-3), (4,3,5), (1,0,0)], [], [(0,1,2)])
        mesh.update()
        obj = bpy.data.objects.new("CBDK R23 asymmetric", mesh)
        bpy.context.collection.objects.link(obj)
        for other in bpy.context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.location = (10.1875, 20.3125, 30.6875)
        bpy.context.view_layer.update()
        scene = bpy.context.scene
        before = [tuple(v.co) for v in mesh.vertices]
        if case == "read":
            if (bpy.ops.cbdk.modular_mesh_bounds() != {"FINISHED"} or
                    scene.cbdk_modular_result != "World bounds (base): 6.000 x 4.000 x 8.000"):
                raise AssertionError("R23 bounds mismatch")
            if (scene.cbdk_modular_center_precision != 3 or
                    bpy.ops.cbdk.modular_mesh_center() != {"FINISHED"} or
                    scene.cbdk_modular_result != "World bounds center (base): 11.188, 21.312, 31.688"):
                raise AssertionError("R23 center mismatch")
            if before != [tuple(v.co) for v in mesh.vertices]:
                raise AssertionError("R23 read case changed vertices")
        else:
            delta = (0.25, -0.5, 0.125)
            if (bpy.ops.cbdk.modular_vertex_nudge(offset=delta) != {"CANCELLED"}
                    or before != [tuple(v.co) for v in mesh.vertices]):
                raise AssertionError("R23 object-mode guard failed")
            bpy.context.tool_settings.mesh_select_mode = (True, False, False)
            bpy.ops.object.mode_set(mode="EDIT")
            try:
                bpy.ops.mesh.select_all(action="DESELECT")
                bm = bmesh.from_edit_mesh(mesh)
                bm.verts.ensure_lookup_table()
                snapshot = lambda: [tuple(v.co) for v in bm.verts]
                start = snapshot()
                if bpy.ops.cbdk.modular_vertex_nudge(offset=delta) != {"CANCELLED"} or snapshot() != start:
                    raise AssertionError("R23 empty-selection guard failed")
                bm.verts[0].select_set(True)
                bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
                if bpy.ops.cbdk.modular_edit_selection() != {"FINISHED"} or scene.cbdk_modular_result != "Edit selection: V=1 E=0 F=0":
                    raise AssertionError("R23 edit selection result mismatch")
                if bpy.ops.cbdk.modular_vertex_nudge(offset=delta) != {"FINISHED"} or scene.cbdk_modular_result != "Moved 1 selected vertices (local)":
                    raise AssertionError("R23 edit operator failed")
                expected = [tuple(a+b for a,b in zip(start[0],delta)), *start[1:]]
                if snapshot() != expected or [v.select for v in bm.verts] != [True,False,False]:
                    raise AssertionError("R23 selected-only edit mismatch")
            finally:
                bpy.ops.object.mode_set(mode="OBJECT")
            if [tuple(v.co) for v in mesh.vertices] != [(-1.75,-1.5,-2.875), *before[1:]]:
                raise AssertionError("R23 committed mesh mismatch")
    finally:
        addon_utils.disable(namespace, default_set=True)
    if (addon_utils.check(namespace)[1] or
            bpy.context.preferences.addons.get(namespace) is not None or
            any(c.is_registered for c in classes) or module._REGISTERED or
            module._OWNED_PROPERTIES or module._OWNED_PROPERTY_TOKENS or
            any(hasattr(bpy.types.Scene, n) for n in
                ("cbdk_modular_result", "cbdk_modular_nudge_offset", "cbdk_modular_center_precision"))):
        raise AssertionError("R23 registration cleanup incomplete")
    print("CBDK_R23_RECIPE_EXTENSION_RUNTIME_PASS: " + case)


if __name__ == "__main__":
    verify()
