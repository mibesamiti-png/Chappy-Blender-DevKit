"""Isolated runtime smoke for the chat-authored Dual Reflector addon.

Uses only synthetic geometry. Does not access private addon source or user models.
Run: blender --background --factory-startup --python-exit-code 7 --python scripts/blender_dual_reflector_smoke.py -- <addon.py>
"""
import importlib.util
import json
import math
import pathlib
import struct
import sys
import tempfile

import bmesh
import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
assert len(args) == 1, "Pass a single source-file path after --"
addon_path = pathlib.Path(args[0]).resolve()
assert addon_path.is_file(), addon_path

spec = importlib.util.spec_from_file_location("Chappy_Dual_Reflector_Maker", addon_path)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
try:
    assert hasattr(bpy.types.Scene, "chappy_dual_reflector")
    assert hasattr(bpy.types, "CHAPPY_PT_dual_reflector")

    p = bpy.context.scene.chappy_dual_reflector
    p.show_rays = True
    p.ray_count = 5
    p.show_reference = True
    p.resolution = 48
    p.export_dir = tempfile.mkdtemp(prefix="cbdk_dual_reflector_")
    root_names = []
    result = {}

    sentinel = bpy.data.objects.new("CBDK_Sentinel_Unrelated", None)
    bpy.context.scene.collection.objects.link(sentinel)

    for mode, source in (("ELLIPSE", "MOUTH"), ("PARABOLA", "PLANE")):
        p.mode, p.ray_source = mode, source
        status = bpy.ops.chappy.build_dual_reflector()
        assert status == {"FINISHED"}, (mode, status)
        root = bpy.data.collections.get(addon.MAIN_COLLECTION)
        ref = bpy.data.collections.get(addon.REFERENCE_COLLECTION)
        assert root is not None and ref is not None
        meshes = [o for o in root.objects if o.type == "MESH"]
        curves = [o for o in root.objects if o.type == "CURVE"]
        assert len(meshes) == 6, (mode, len(meshes))
        assert len(curves) == 10, (mode, len(curves))
        assert p.last_summary and "共通焦点" in p.last_summary
        assert len([o for o in ref.objects if o.type == "MESH"]) == 1
        assert bpy.data.objects.get(sentinel.name) is sentinel

        for ob in meshes:
            bm = bmesh.new()
            try:
                bm.from_mesh(ob.data)
                assert len(bm.faces) > 0, ob.name
                assert all(e.is_manifold for e in bm.edges), ob.name
                assert all(math.isfinite(v.co.x) and math.isfinite(v.co.y) and math.isfinite(v.co.z)
                           for v in bm.verts), ob.name
            finally:
                bm.free()

        if mode == "ELLIPSE":
            keep = root.objects.get("01_Mouth_Horn")
            pointer = keep.as_pointer()
            p.diameter, p.mouth_d = 60.0, 65.0
            # Blender may raise RuntimeError for an operator that reports ERROR,
            # even if the operator explicitly returned CANCELLED.
            try:
                reject_status = bpy.ops.chappy.build_dual_reflector()
                assert reject_status == {"CANCELLED"}, reject_status
            except RuntimeError as exc:
                assert "外径を大きく" in str(exc), str(exc)
            root_after = bpy.data.collections.get(addon.MAIN_COLLECTION)
            assert root_after.objects.get("01_Mouth_Horn").as_pointer() == pointer, "invalid input mutated scene"
            p.diameter, p.mouth_d = 100.0, 32.0

        root_names.append(mode)
        if mode == "PARABOLA":
            p.include_reference = True
            status = bpy.ops.chappy.export_dual_reflector()
            assert status == {"FINISHED"}, status
            exports = sorted(pathlib.Path(p.export_dir).glob("*.stl"))
            assert len(exports) == 7, [x.name for x in exports]
            assert (pathlib.Path(p.export_dir) / "READ_ME_FIRST.txt").is_file()
            for file in exports:
                raw = file.read_bytes()
                assert len(raw) >= 84
                count = struct.unpack_from("<I", raw, 80)[0]
                assert count > 0 and len(raw) == 84 + 50 * count, file.name
            result["stl_count"] = len(exports)

            # A manually linked object must never be destroyed on regeneration.
            user_object = bpy.data.objects.new("CBDK_User_Object_Not_To_Delete", None)
            root.objects.link(user_object)
            root_ptr = root.objects.get("01_Mouth_Horn").as_pointer()
            try:
                bpy.ops.chappy.build_dual_reflector()
                raise AssertionError("must reject a collection containing user objects")
            except RuntimeError as exc:
                assert "手動のオブジェクト" in str(exc), str(exc)
            assert bpy.data.objects.get(user_object.name) is user_object
            assert root.objects.get("01_Mouth_Horn").as_pointer() == root_ptr
            root.objects.unlink(user_object)
            bpy.data.objects.remove(user_object)
            result["user_object_protected"] = True

    p.show_reference, p.show_rays = False, False
    assert bpy.ops.chappy.build_dual_reflector() == {"FINISHED"}
    assert bpy.data.collections.get(addon.REFERENCE_COLLECTION) is None
    assert all(o.type != "CURVE" for o in bpy.data.collections[addon.MAIN_COLLECTION].objects)
    result.update(blender=bpy.app.version_string, modes=root_names,
                  status="passed", object_count=6, invalid_input_preserved=True,
                  reference_toggle=True, ray_toggle=True)
    print("CBDK_DUAL_REFLECTOR_PASS " + json.dumps(result, ensure_ascii=False, sort_keys=True))
finally:
    addon.unregister()
    assert not hasattr(bpy.types.Scene, "chappy_dual_reflector")
