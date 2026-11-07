"""Trusted real-Blender end-to-end smoke for a schema-2 modular preview ZIP.

Blender executes only the CBDK-owned generated preview from an explicit CI
build, never scanned/private third-party scripts. Factory startup is required.
"""
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

import addon_utils
import bpy


PACKAGE = "cbdk_modular_preview"
KNOWN = {"object_selection", "edit_selection", "mesh_bounds", "modifier_summary", "vertex_nudge"}


def verify_zip(path):
    with ZipFile(path, "r") as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)), "Duplicate ZIP entries"
        metadata = json.loads(archive.read(f"{PACKAGE}/CBDK_BUILD_INFO.json"))
        features = set(metadata["features"])
        assert features and features <= KNOWN, features
        expected = {
            f"{PACKAGE}/__init__.py", f"{PACKAGE}/CBDK_BUILD_INFO.json",
            f"{PACKAGE}/README.txt", f"{PACKAGE}/helpers/__init__.py",
            f"{PACKAGE}/helpers/context.py", f"{PACKAGE}/features/__init__.py",
        }
        for feature in features:
            expected.add(f"{PACKAGE}/features/{feature}.py")
        if "edit_selection" in features:
            expected.add(f"{PACKAGE}/helpers/edit_mesh.py")
        if "mesh_bounds" in features:
            expected.add(f"{PACKAGE}/helpers/measure.py")
        if "modifier_summary" in features:
            expected.add(f"{PACKAGE}/helpers/modifiers.py")
        if "vertex_nudge" in features:
            expected.add(f"{PACKAGE}/helpers/edit_transform.py")
            expected.add(f"{PACKAGE}/helpers/edit_audit.py")
        assert set(members) == expected, (set(members), expected)
        for info in archive.infolist():
            assert not any(part in ("", ".", "..") for part in info.filename.split("/"))
            assert not ((info.external_attr >> 16) & 0o170000) == 0o120000
        assert metadata["preview_only"] is True
        assert metadata["approved"] is False
        assert metadata["redistribution_cleared"] is False
        assert metadata["blender_runtime_verified_for_this_build"] is False
        return features


def run(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    features = verify_zip(path)
    checks = ["safe_recipe_zip"]
    with tempfile.TemporaryDirectory(prefix="cbdk-modular-") as directory:
        with ZipFile(path, "r") as archive:
            archive.extractall(directory)
        sys.path.insert(0, directory)
        enabled = False
        try:
            module = addon_utils.enable(PACKAGE, default_set=False, persistent=False)
            assert module is not None
            enabled = True
            assert hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview")
            assert hasattr(bpy.types.Scene, "cbdk_modular_result")
            assert hasattr(bpy.types.Scene, "cbdk_modular_nudge_offset")
            operator_ids = {op.bl_idname for op in module._OPERATORS}
            expected_ops = set()
            if "object_selection" in features:
                expected_ops.add("cbdk.modular_selected_meshes")
            if "edit_selection" in features:
                expected_ops.add("cbdk.modular_edit_selection")
            if "mesh_bounds" in features:
                expected_ops.add("cbdk.modular_mesh_bounds")
            if "modifier_summary" in features:
                expected_ops.add("cbdk.modular_modifier_summary")
            if "vertex_nudge" in features:
                expected_ops.add("cbdk.modular_vertex_nudge")
            assert operator_ids == expected_ops, (operator_ids, expected_ops)
            checks.append("only_selected_operators_registered")

            # Exercise Blender's real Panel.draw with a recording layout.
            # This verifies the UI logic, not real Windows mouse/GPU rendering.
            class RecordingOperator:
                def __init__(self, events):
                    object.__setattr__(self, "events", events)

                def __setattr__(self, key, value):
                    self.events.append(("operator_property", key, tuple(value)))

            class RecordingLayout:
                def __init__(self, events=None):
                    self.events = events if events is not None else []

                def column(self, align=False):
                    return RecordingLayout(self.events)

                def row(self, align=False):
                    self.events.append(("row",))
                    return RecordingLayout(self.events)

                def box(self):
                    self.events.append(("box",))
                    return RecordingLayout(self.events)

                def label(self, *, text):
                    self.events.append(("label", text))

                @property
                def enabled(self):
                    return True

                @enabled.setter
                def enabled(self, value):
                    self.events.append(("enabled", bool(value)))

                def prop(self, data, identifier, *, text):
                    self.events.append(("prop", identifier, text, tuple(getattr(data, identifier))))

                def operator(self, identifier, *, text):
                    self.events.append(("operator", identifier, text))
                    return RecordingOperator(self.events)

            def verify_panel(expected_mode, expected_enabled):
                layout = RecordingLayout()
                preview = type("CBDK_Synthetic_Panel", (), {"layout": layout})()
                module.VIEW3D_PT_cbdk_modular_preview.draw(preview, bpy.context)
                result = layout.events
                observed_ops = [entry for entry in result if entry[0] == "operator"]
                assert {entry[1] for entry in observed_ops} == expected_ops, result
                enabled = [entry[1] for entry in result if entry[0] == "enabled"]
                assert len(enabled) == len(module._FEATURE_IDS), result
                expected = []
                for _, controls in module._UI_SECTIONS:
                    for feature, _ in controls:
                        expected.append(feature in expected_enabled)
                assert enabled == expected, (enabled, expected, expected_mode)
                assert bpy.context.mode == expected_mode
                if "vertex_nudge" in features:
                    props = [entry for entry in result if entry[0] == "prop"]
                    offsets = [entry for entry in result if entry[0] == "operator_property"]
                    assert len(props) == len(offsets) == 1, result
                    assert props[0][1] == "cbdk_modular_nudge_offset"
                    assert offsets[0] == ("operator_property", "offset", props[0][3])
                else:
                    assert not any(event[0] in {"prop", "operator_property"} for event in result)
                return result

            assert all(not enabled for enabled in
                       [item[1] for item in verify_panel("OBJECT", set())
                        if item[0] == "enabled"])
            checks.append("panel_requires_active_mesh")

            mesh = bpy.data.meshes.new("CBDK_Modular_Triangle")
            mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
            mesh.update()
            obj = bpy.data.objects.new("CBDK_Modular_Object", mesh)
            bpy.context.scene.collection.objects.link(obj)
            light_data = bpy.data.lights.new("CBDK_Modular_Light", "POINT")
            light = bpy.data.objects.new("CBDK_Modular_Light", light_data)
            bpy.context.scene.collection.objects.link(light)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            light.select_set(True)
            assert bpy.context.mode == "OBJECT"
            verify_panel("OBJECT", {"object_selection", "mesh_bounds", "modifier_summary"})
            checks.append("panel_object_mode_guards")

            if "object_selection" in features:
                assert bpy.ops.cbdk.modular_selected_meshes() == {"FINISHED"}
                status = bpy.context.scene.cbdk_modular_result
                assert "Selected meshes: 1" in status and "CBDK_Modular_Object" in status, status
                assert obj.select_get() and light.select_get()
                assert bpy.context.mode == "OBJECT"
                checks.append("object_selection_readonly")
            if "edit_selection" in features:
                assert bpy.ops.cbdk.modular_edit_selection() == {"CANCELLED"}
                checks.append("edit_requires_edit_mode")
            if "vertex_nudge" in features:
                assert bpy.ops.cbdk.modular_vertex_nudge() == {"CANCELLED"}
                checks.append("nudge_requires_edit_mode")

            if "mesh_bounds" in features:
                obj.scale = (2.0, 3.0, 1.0)
                obj.location = (5.0, -3.0, 2.0)
                bpy.context.view_layer.update()
                old_vertices = len(mesh.vertices)
                assert bpy.ops.cbdk.modular_mesh_bounds() == {"FINISHED"}
                status = bpy.context.scene.cbdk_modular_result
                assert "2.000 x 3.000 x 0.000" in status, status
                assert len(mesh.vertices) == old_vertices and bpy.context.mode == "OBJECT"
                checks.append("mesh_world_bounds_non_destructive")

            if "modifier_summary" in features:
                modifier = obj.modifiers.new(name="CBDK_Subdivision", type="SUBSURF")
                modifier.show_viewport = False
                before = [(m.name, m.type, m.show_viewport, m.show_render)
                          for m in obj.modifiers]
                assert bpy.ops.cbdk.modular_modifier_summary() == {"FINISHED"}
                status = bpy.context.scene.cbdk_modular_result
                assert "Modifiers: 1 (SUBSURF:1)" in status, status
                after = [(m.name, m.type, m.show_viewport, m.show_render)
                         for m in obj.modifiers]
                assert before == after
                checks.append("modifier_stack_read_only")

            light.select_set(False)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            verify_panel("EDIT_MESH", {"edit_selection", "vertex_nudge"})
            checks.append("panel_edit_mode_guards")
            if "vertex_nudge" in features:
                bpy.context.scene.cbdk_modular_nudge_offset = (0.125, 0.0, 0.0)
                actual_layout = verify_panel("EDIT_MESH", {"edit_selection", "vertex_nudge"})
                assert ("operator_property", "offset", (0.125, 0.0, 0.0)) in actual_layout
                checks.append("panel_editable_nudge_offset")
            if "edit_selection" in features:
                assert bpy.ops.cbdk.modular_edit_selection() == {"FINISHED"}
                status = bpy.context.scene.cbdk_modular_result
                assert "V=3 E=3 F=1" in status, status
                assert bpy.context.mode == "EDIT_MESH"
                checks.append("edit_selection_readonly")
            if "vertex_nudge" in features:
                import bmesh
                bm = bmesh.from_edit_mesh(mesh)
                bm.verts.ensure_lookup_table()
                bpy.ops.mesh.select_all(action="DESELECT")
                chosen = bm.verts[0]
                chosen.select_set(True)
                bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
                before = [tuple(v.co) for v in bm.verts]
                original_structure = (len(bm.verts), len(bm.edges), len(bm.faces))
                assert bpy.ops.cbdk.modular_vertex_nudge(offset=(0.0, 0.0, 0.125)) == {"FINISHED"}
                after = [tuple(v.co) for v in bm.verts]
                assert abs(after[0][2] - before[0][2] - 0.125) < 1e-6, (before, after)
                assert after[1:] == before[1:], (before, after)
                assert original_structure == (len(bm.verts), len(bm.edges), len(bm.faces))
                assert bm.verts[0].select and not any(v.select for v in list(bm.verts)[1:])
                assert bpy.context.mode == "EDIT_MESH"
                assert "UNDO" in next(op for op in module._OPERATORS if op.bl_idname ==
                                      "cbdk.modular_vertex_nudge").bl_options
                assert "REGISTER" in next(op for op in module._OPERATORS if op.bl_idname ==
                                      "cbdk.modular_vertex_nudge").bl_options
                checks.append("nudge_local_selected_only_and_undo_flag")
                untouched = [tuple(v.co) for v in bm.verts]
                assert bpy.ops.cbdk.modular_vertex_nudge(offset=(0.0, 0.0, 0.0)) == {"CANCELLED"}
                assert untouched == [tuple(v.co) for v in bm.verts]
                checks.append("nudge_zero_offset_preserves_mesh")
            if "object_selection" in features:
                assert bpy.ops.cbdk.modular_selected_meshes() == {"CANCELLED"}
                checks.append("object_requires_object_mode")
            if "mesh_bounds" in features:
                assert bpy.ops.cbdk.modular_mesh_bounds() == {"CANCELLED"}
                checks.append("bounds_reject_edit_mode")
            if "modifier_summary" in features:
                assert bpy.ops.cbdk.modular_modifier_summary() == {"CANCELLED"}
                checks.append("modifiers_reject_edit_mode")

            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.context.view_layer.objects.active = None
            if "object_selection" in features:
                assert bpy.ops.cbdk.modular_selected_meshes() == {"CANCELLED"}
                checks.append("missing_active_mesh_cancelled")
            addon_utils.disable(PACKAGE, default_set=False)
            enabled = False
            assert not hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview")
            assert not hasattr(bpy.types.Scene, "cbdk_modular_result")
            assert not hasattr(bpy.types.Scene, "cbdk_modular_nudge_offset")
            assert not module._REGISTERED
            checks.append("disable_unregistered_all")
        finally:
            if enabled:
                try:
                    addon_utils.disable(PACKAGE, default_set=False)
                except Exception:
                    pass
            sys.path.remove(directory)
    print("CBDK_MODULAR_ADDON_PASS " + json.dumps({
        "schema_version": 2,
        "blender": bpy.app.version_string,
        "package_id": PACKAGE,
        "features": sorted(features),
        "checks": checks,
        "preview_only": True,
        "approved": False,
    }, sort_keys=True))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("Expected -- <trusted-generated-zip>")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Exactly one ZIP is required")
    run(Path(args[0]).resolve())
