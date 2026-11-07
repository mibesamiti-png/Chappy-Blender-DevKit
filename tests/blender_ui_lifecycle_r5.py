"""Team C R5 real-Blender lifecycle probe for a trusted CBDK-authored preview.

Explicit opt-in, standalone. This file is NOT invoked by the current shared
Blender workflow; Team A owns connecting it. Use only factory-startup and a
locally generated `modular_all` preview ZIP. No private addon/user .blend.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import addon_utils
import bpy


PACKAGE = "cbdk_modular_preview"
IDS = {
    "object_selection": "cbdk.modular_selected_meshes",
    "mesh_bounds": "cbdk.modular_mesh_bounds",
    "modifier_summary": "cbdk.modular_modifier_summary",
    "edit_selection": "cbdk.modular_edit_selection",
    "vertex_nudge": "cbdk.modular_vertex_nudge",
}
PROPERTIES = ("cbdk_modular_result", "cbdk_modular_nudge_offset")


class RecordLayout:
    def __init__(self, events=None, parent_enabled=True):
        self.events = [] if events is None else events
        self._enabled = parent_enabled

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = self._enabled and bool(value)

    def column(self, align=False):
        return RecordLayout(self.events, self._enabled)

    def row(self, align=False):
        return RecordLayout(self.events, self._enabled)

    def box(self):
        return RecordLayout(self.events, self._enabled)

    def label(self, *, text):
        self.events.append(("label", text))

    def prop(self, data, identifier, *, text):
        self.events.append(("prop", identifier, self._enabled))

    def operator(self, identifier, *, text):
        self.events.append(("operator", identifier, self._enabled))
        return SimpleNamespace(offset=None)


def panel_events(module):
    layout = RecordLayout()
    module.VIEW3D_PT_cbdk_modular_preview.draw(
        SimpleNamespace(layout=layout), bpy.context)
    return {item[1]: item[2] for item in layout.events
            if item[0] == "operator"}, layout.events


def assert_detached(module):
    assert not module._REGISTERED, "CBDK operator classes leaked"
    assert not module._OWNED_PROPERTIES, "CBDK property names leaked"
    assert not module._OWNED_PROPERTY_TOKENS, "CBDK property tokens leaked"
    assert not hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview")
    assert all(not hasattr(bpy.types.Scene, name) for name in PROPERTIES)


def check_zip(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate archive paths"
        assert names and all(name.startswith(PACKAGE + "/")
                             and not any(segment in ("", ".", "..")
                                         for segment in name.split("/")[:-1])
                             for name in names), "Unsafe archive entry"
        metadata = json.loads(archive.read(PACKAGE + "/CBDK_BUILD_INFO.json"))
        assert set(metadata["features"]) == set(IDS)
        assert metadata["preview_only"] is True
        assert metadata["approved"] is False
        assert metadata["redistribution_cleared"] is False


def run(path):
    check_zip(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    checks = ["trusted_modular_all_zip"]
    enabled = False
    module = None
    with tempfile.TemporaryDirectory(prefix="cbdk-r5-native-") as directory:
        with ZipFile(path) as archive:
            archive.extractall(directory)
        sys.path.insert(0, directory)
        try:
            module = addon_utils.enable(PACKAGE, default_set=False, persistent=False)
            assert module is not None
            enabled = True
            assert set(module._FEATURE_IDS) == set(IDS)

            mesh = bpy.data.meshes.new("CBDK_R5_triangle")
            mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                             [], [(0, 1, 2)])
            mesh.update()
            obj = bpy.data.objects.new("CBDK_R5_object", mesh)
            bpy.context.scene.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            assert bpy.context.mode == "OBJECT"
            before = tuple(tuple(v.co) for v in mesh.vertices)

            for _ in range(3):
                object_ui, _ = panel_events(module)
                assert set(object_ui) == set(IDS.values()), object_ui
                assert all(object_ui[IDS[f]] for f in (
                    "object_selection", "mesh_bounds", "modifier_summary"))
                assert not any(object_ui[IDS[f]] for f in (
                    "edit_selection", "vertex_nudge"))
                assert bpy.ops.cbdk.modular_selected_meshes() == {"FINISHED"}
                bpy.ops.object.mode_set(mode="EDIT")
                assert bpy.context.mode == "EDIT_MESH"
                bpy.ops.mesh.select_all(action="DESELECT")
                edit_ui, edit_events = panel_events(module)
                assert set(edit_ui) == set(IDS.values()), edit_ui
                assert edit_ui[IDS["edit_selection"]]
                assert not edit_ui[IDS["vertex_nudge"]]
                assert not any(edit_ui[IDS[f]] for f in (
                    "object_selection", "mesh_bounds", "modifier_summary"))
                assert ("prop", "cbdk_modular_nudge_offset", True) in edit_events
                assert module._preview_unavailable_reason("vertex_nudge",
                                                          bpy.context) is not None
                current_result = bpy.context.scene.cbdk_modular_result
                assert bpy.ops.cbdk.modular_vertex_nudge() == {"CANCELLED"}
                assert bpy.ops.cbdk.modular_selected_meshes() == {"CANCELLED"}
                assert bpy.context.scene.cbdk_modular_result == current_result
                bpy.ops.object.mode_set(mode="OBJECT")
                assert bpy.context.mode == "OBJECT"
                assert tuple(tuple(v.co) for v in mesh.vertices) == before
            checks.append("native_object_edit_cancel_mode_cycles_3")
            checks.append("native_zero_selection_xyz_editable_and_non_mutating")

            addon_utils.disable(PACKAGE, default_set=False)
            enabled = False
            assert_detached(module)
            checks.append("native_initial_disable_complete")
            for _ in range(4):
                module.register()
                assert hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview")
                assert all(hasattr(bpy.types.Scene, name) for name in PROPERTIES)
                try:
                    module.register()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Double register wrongly accepted")
                module.unregister()
                assert_detached(module)
                module.unregister()
            checks.append("native_register_unregister_cycles_4")

            # A *synthetic stand-in* for another addon's property. This is not
            # executing or importing any external/third-party addon.
            bpy.types.Scene.cbdk_modular_result = bpy.props.StringProperty(
                default="CBDK R5 external sentinel")
            try:
                assert hasattr(bpy.types.Scene, "cbdk_modular_result")
                try:
                    module.register()
                except RuntimeError as exc:
                    assert "Scene properties conflict" in str(exc), str(exc)
                else:
                    raise AssertionError("Foreign property accepted")
                assert not module._REGISTERED
                assert not module._OWNED_PROPERTIES
                assert not module._OWNED_PROPERTY_TOKENS
                assert hasattr(bpy.types.Scene, "cbdk_modular_result")
                assert not hasattr(bpy.types.Scene, "cbdk_modular_nudge_offset")
            finally:
                del bpy.types.Scene.cbdk_modular_result
            checks.append("native_preexisting_foreign_collision_preserved")

            # Replace a declaration while CBDK is loaded; do not remove that
            # new declaration when unregistering. This tests descriptor
            # identity on real Blender RNA rather than Python-only mocks.
            module.register()
            original = bpy.types.Scene.__dict__.get("cbdk_modular_result")
            assert original is not None, "Blender RNA descriptor unavailable"
            bpy.types.Scene.cbdk_modular_result = bpy.props.StringProperty(
                default="CBDK R5 replacement sentinel")
            replacement = bpy.types.Scene.__dict__.get("cbdk_modular_result")
            assert replacement is not None and replacement is not original
            try:
                module.unregister()
                assert not module._REGISTERED
                assert not module._OWNED_PROPERTIES
                assert not module._OWNED_PROPERTY_TOKENS
                assert bpy.types.Scene.__dict__.get(
                    "cbdk_modular_result") is replacement
                assert hasattr(bpy.types.Scene, "cbdk_modular_result")
                assert not hasattr(bpy.types.Scene, "cbdk_modular_nudge_offset")
            finally:
                if hasattr(bpy.types.Scene, "cbdk_modular_result"):
                    del bpy.types.Scene.cbdk_modular_result
            checks.append("native_foreign_replacement_preserved")
            module.register()
            module.unregister()
            assert_detached(module)
            checks.append("native_cleanup_and_reregister_after_collision")
        finally:
            if enabled:
                try:
                    addon_utils.disable(PACKAGE, default_set=False)
                except Exception:
                    pass
            if module is not None:
                try:
                    module.unregister()
                except Exception:
                    pass
            if hasattr(bpy.types.Scene, "cbdk_modular_result"):
                try:
                    del bpy.types.Scene.cbdk_modular_result
                except Exception:
                    pass
            sys.path.remove(directory)
    print("CBDK_R5_UI_LIFECYCLE_PASS " + json.dumps({
        "schema_version": 1,
        "blender": bpy.app.version_string,
        "checks": checks,
        "preview_only": True,
        "approved": False,
        "real_blender_headless": True,
        "real_windows_gui_tested": False,
        "third_party_addon_imported": False,
    }, sort_keys=True))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("Expected -- followed by one trusted modular_all ZIP")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 1:
        raise RuntimeError("Exactly one preview ZIP argument required")
    run(Path(args[0]).resolve())
