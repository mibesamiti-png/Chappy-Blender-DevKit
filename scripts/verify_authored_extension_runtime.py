"""Internal CI-only Blender subprocess. Not a general installer."""
import io
import os
from pathlib import Path
import sys
from zipfile import ZipFile

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cbdk.extension_authored_fixture import FIXTURE_ID, build_authored_fixture_bytes
from cbdk.extension_preflight import MAX_ARCHIVE_BYTES


def verify():
    root = Path(os.environ["CBDK_R19_TEMP"]).resolve()
    config = Path(os.environ["BLENDER_USER_CONFIG"]).resolve()
    if not config.is_relative_to(root) or not root.is_dir() or bpy.app.online_access:
        raise AssertionError("R19 runtime is not isolated/offline")
    if not Path(bpy.utils.user_resource("CONFIG")).resolve().is_relative_to(root):
        raise AssertionError("R19 Blender config escaped isolation")
    archive_path = root / "authored.zip"
    with archive_path.open("rb") as stream:
        blob = stream.read(MAX_ARCHIVE_BYTES + 1)
    # A supplied path or hash cannot authorize code execution. Rebuild the
    # fixed authored recipe inside this trusted checkout and compare bytes.
    if blob != build_authored_fixture_bytes():
        raise AssertionError("R19 runtime input differs from fixed authored generation")
    directory = root / "local_repo"
    directory.mkdir()
    package = directory / FIXTURE_ID
    package.mkdir()
    with ZipFile(io.BytesIO(blob)) as archive:
        for name in archive.namelist():
            target = package / name
            if not target.resolve().is_relative_to(package):
                raise AssertionError("R19 unsafe staging member")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(archive.read(name))
    # Explicit manual staging into a real Blender local Extension repository.
    # This does not claim that the official install-files operator ran.
    result = bpy.ops.preferences.extension_repo_add(
        name="CBDK R19 isolated fixture", type="LOCAL",
        use_custom_directory=True, custom_directory=str(directory),
        use_sync_on_startup=False)
    if result != {"FINISHED"}:
        raise AssertionError("R19 local Extension repository registration failed")
    repos = bpy.context.preferences.extensions.repos
    matches = [repo for repo in repos if Path(repo.directory).resolve() == directory]
    if len(matches) != 1:
        raise AssertionError("R19 local Extension repository not found")
    repo = matches[0]
    namespace = "bl_ext." + repo.module + "." + FIXTURE_ID
    if addon_utils.check(namespace)[1] or hasattr(bpy.types.Scene, "cbdk_modular_result"):
        raise AssertionError("R19 preexisting fixture registration")
    addon_utils.modules_refresh()
    module = addon_utils.enable(namespace, default_set=True, persistent=False)
    if module is None:
        raise AssertionError("R19 Extension enable failed")
    classes = tuple(module._CLASSES)
    try:
        if (module.__name__ != namespace or
                Path(module.__file__).resolve() != package / "__init__.py" or
                not addon_utils.check(namespace)[1] or
                bpy.context.preferences.addons.get(namespace) is None or
                set(module._FEATURE_IDS) != {"mesh_bounds", "mesh_center"} or
                any(not c.is_registered for c in classes)):
            raise AssertionError("R19 real Extension namespace/registration mismatch")
        mesh = bpy.data.meshes.new("CBDK R19 asymmetric")
        mesh.from_pydata([(-2,-1,-3), (4,3,5), (1,0,0)], [], [(0,1,2)])
        mesh.update()
        obj = bpy.data.objects.new("CBDK R19 asymmetric", mesh)
        bpy.context.collection.objects.link(obj)
        for other in bpy.context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.location = (10,20,30)
        bpy.context.view_layer.update()
        before = [tuple(v.co) for v in mesh.vertices]
        # Independent known extrema and translation, not the addon helper.
        if (bpy.ops.cbdk.modular_mesh_bounds() != {"FINISHED"} or
                bpy.context.scene.cbdk_modular_result != "World bounds (base): 6.000 x 4.000 x 8.000"):
            raise AssertionError("R19 bounds operator mismatch")
        if (bpy.ops.cbdk.modular_mesh_center() != {"FINISHED"} or
                bpy.context.scene.cbdk_modular_result != "World bounds center (base): 11.000, 21.000, 31.000"):
            raise AssertionError("R19 center operator mismatch")
        if before != [tuple(v.co) for v in mesh.vertices]:
            raise AssertionError("R19 read-only feature modified vertices")
    finally:
        addon_utils.disable(namespace, default_set=True)
    if (addon_utils.check(namespace)[1] or
            bpy.context.preferences.addons.get(namespace) is not None or
            any(c.is_registered for c in classes) or module._REGISTERED or
            module._OWNED_PROPERTIES or module._OWNED_PROPERTY_TOKENS or
            any(hasattr(bpy.types.Scene, n) for n in module._PROPERTY_NAMES)):
        raise AssertionError("R19 Extension registration cleanup incomplete")
    print("CBDK_R19_AUTHORED_EXTENSION_RUNTIME_PASS: local repo namespace enable, bounds/center, disable; manual staging only")


if __name__ == "__main__":
    verify()
