"""Team C R5/R6 Blender lifecycle probe for a CBDK-authored preview.

Explicit opt-in, standalone. Team A's Blender workflow already invokes
this script on three official versions. Use only factory-startup and a
locally generated `modular_all` preview ZIP. No private addon/user .blend.
"""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import addon_utils
import bmesh
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

            # R6: two objects may share a single mesh datablock.  Selection
            # is deliberately nonempty, so the nudge must be refused by the
            # shared-data preflight rather than the zero-selection guard.
            other = bpy.data.objects.new("CBDK_R6_shared", mesh)
            bpy.context.scene.collection.objects.link(other)
            other.select_set(False)
            assert mesh.users == 2, mesh.users
            try:
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                assert bpy.context.mode == "EDIT_MESH"
                assert len([item for item in bpy.context.objects_in_mode_unique_data
                            if item.type == "MESH"]) == 1
                shared_ui, _ = panel_events(module)
                assert not shared_ui[IDS["vertex_nudge"]], shared_ui
                assert "Shared mesh datablocks" in module._preview_unavailable_reason(
                    "vertex_nudge", bpy.context)
                before_result = bpy.context.scene.cbdk_modular_result
                assert bpy.ops.cbdk.modular_vertex_nudge() == {"CANCELLED"}
                assert bpy.context.scene.cbdk_modular_result == before_result
                bpy.ops.object.mode_set(mode="OBJECT")
                assert tuple(tuple(v.co) for v in mesh.vertices) == before
            finally:
                if bpy.context.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.data.objects.remove(other, do_unlink=True)
            assert mesh.users == 1
            checks.append("native_r6_shared_mesh_nudge_refused_no_mutation")

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

            # R6: importlib.reload must refuse to discard an active module's
            # ledgers. An explicit unregister followed by reload is allowed.
            module.register()
            old_classes = tuple(module._REGISTERED)
            old_tokens = dict(module._OWNED_PROPERTY_TOKENS)
            assert old_classes and all(old_tokens.values())
            try:
                importlib.reload(module)
            except RuntimeError as exc:
                assert "unregistered before module reload" in str(exc), str(exc)
            else:
                raise AssertionError("Live reload silently lost Scene ownership")
            assert tuple(module._REGISTERED) == old_classes
            assert all(module._OWNED_PROPERTY_TOKENS.get(key) is value
                       for key, value in old_tokens.items())
            assert all(hasattr(bpy.types.Scene, name) for name in PROPERTIES)
            module.unregister()
            assert_detached(module)
            checks.append("native_r6_live_reload_rejected_without_leaks")

            assert importlib.reload(module) is module
            module.register()
            module.unregister()
            assert_detached(module)
            checks.append("native_r6_detached_reload_reregistered")

            # R6: do not remove *either* foreign declaration after replacing
            # both CBDK-owned RNA descriptors while the addon is loaded.
            module.register()
            original_result = bpy.types.Scene.__dict__.get(PROPERTIES[0])
            original_offset = bpy.types.Scene.__dict__.get(PROPERTIES[1])
            assert original_result is not None and original_offset is not None
            bpy.types.Scene.cbdk_modular_result = bpy.props.StringProperty(
                default="CBDK R6 external replacement")
            bpy.types.Scene.cbdk_modular_nudge_offset = bpy.props.FloatVectorProperty(
                size=3, default=(0.0, 0.0, 0.25))
            new_result = bpy.types.Scene.__dict__.get(PROPERTIES[0])
            new_offset = bpy.types.Scene.__dict__.get(PROPERTIES[1])
            assert new_result is not None and new_result is not original_result
            assert new_offset is not None and new_offset is not original_offset
            try:
                module.unregister()
                assert not module._REGISTERED
                assert not module._OWNED_PROPERTIES
                assert not module._OWNED_PROPERTY_TOKENS
                assert bpy.types.Scene.__dict__.get(PROPERTIES[0]) is new_result
                assert bpy.types.Scene.__dict__.get(PROPERTIES[1]) is new_offset
                try:
                    module.register()
                except RuntimeError as exc:
                    assert "Scene properties conflict" in str(exc)
                else:
                    raise AssertionError("Foreign RNA replacement accepted")
            finally:
                for name in reversed(PROPERTIES):
                    if name in bpy.types.Scene.__dict__:
                        delattr(bpy.types.Scene, name)
            assert_detached(module)
            checks.append("native_r6_dual_foreign_descriptors_preserved")

            # R6: controlled failure on the second class registration keeps
            # the original exception visible and can be retried cleanly.
            native_register = bpy.utils.register_class
            call_count = [0]
            def fail_second_registration(cls):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise RuntimeError("CBDK R6 injected registration failure")
                return native_register(cls)
            bpy.utils.register_class = fail_second_registration
            try:
                try:
                    module.register()
                except RuntimeError as exc:
                    assert "R6 injected registration failure" in str(exc)
                else:
                    raise AssertionError("Injected registration failure ignored")
            finally:
                bpy.utils.register_class = native_register
            assert_detached(module)
            module.register()
            module.unregister()
            assert_detached(module)
            checks.append("native_r6_partial_registration_retry")

            # R7: fail partway through registering operator classes, after
            # one real class is attached. During the error, one CBDK Scene
            # property disappears and the other is replaced with a controlled
            # *foreign stand-in*. Rollback must clean only what CBDK still owns.
            for missing, replaced in (
                    (PROPERTIES[0], PROPERTIES[1]),
                    (PROPERTIES[1], PROPERTIES[0])):
                native_register = bpy.utils.register_class
                calls = [0]
                foreign_descriptor = [None]

                def fail_after_foreign_mutation(cls):
                    calls[0] += 1
                    if calls[0] == 2:
                        assert len(module._REGISTERED) == 1
                        assert all(name in bpy.types.Scene.__dict__
                                   for name in PROPERTIES)
                        # Re-entering importlib.reload during partial
                        # registration must not erase the live ownership ledger.
                        try:
                            importlib.reload(module)
                        except RuntimeError as exc:
                            assert "unregistered before module reload" in str(exc)
                        else:
                            raise AssertionError("Partial registration reload accepted")
                        assert len(module._REGISTERED) == 1
                        delattr(bpy.types.Scene, missing)
                        if replaced == PROPERTIES[0]:
                            bpy.types.Scene.cbdk_modular_result = (
                                bpy.props.StringProperty(
                                    default="CBDK R7 foreign result"))
                        else:
                            bpy.types.Scene.cbdk_modular_nudge_offset = (
                                bpy.props.FloatVectorProperty(
                                    size=3, default=(0.0, 0.0, 0.35)))
                        foreign_descriptor[0] = (
                            bpy.types.Scene.__dict__.get(replaced))
                        assert foreign_descriptor[0] is not None
                        raise RuntimeError("CBDK R7 injected mid-register failure")
                    return native_register(cls)

                bpy.utils.register_class = fail_after_foreign_mutation
                try:
                    try:
                        module.register()
                    except RuntimeError as exc:
                        assert "R7 injected mid-register failure" in str(exc)
                    else:
                        raise AssertionError("R7 controlled failure was ignored")
                finally:
                    bpy.utils.register_class = native_register

                try:
                    assert calls[0] == 2
                    assert not module._REGISTERED
                    assert not module._OWNED_PROPERTIES
                    assert not module._OWNED_PROPERTY_TOKENS
                    assert missing not in bpy.types.Scene.__dict__
                    assert bpy.types.Scene.__dict__.get(replaced) is (
                        foreign_descriptor[0])
                    assert not hasattr(
                        bpy.types, "VIEW3D_PT_cbdk_modular_preview")
                    # Reload after *successful rollback* is allowed even if
                    # the foreign RNA declaration still occupies one name.
                    assert importlib.reload(module) is module
                    assert bpy.types.Scene.__dict__.get(replaced) is (
                        foreign_descriptor[0])
                    try:
                        module.register()
                    except RuntimeError as exc:
                        assert "Scene properties conflict" in str(exc)
                    else:
                        raise AssertionError("Foreign Scene name not protected")
                    assert not module._REGISTERED
                    assert not module._OWNED_PROPERTIES
                    assert not module._OWNED_PROPERTY_TOKENS
                    assert bpy.types.Scene.__dict__.get(replaced) is (
                        foreign_descriptor[0])
                finally:
                    # Remove only our controlled synthetic foreign stand-in.
                    if (bpy.types.Scene.__dict__.get(replaced)
                            is foreign_descriptor[0]):
                        delattr(bpy.types.Scene, replaced)
                assert_detached(module)
                module.register()
                module.unregister()
                assert_detached(module)
            checks.append("native_r7_mid_register_missing_foreign_rollback")
            checks.append("native_r7_partial_live_reload_rejected")
            checks.append("native_r7_foreign_reload_collision_preserved")

            # R7: after both interrupted registrations are recovered, use
            # Blender's actual addon enable/disable API repeatedly. This is
            # independent of merely invoking module.register() by hand.
            for _ in range(2):
                module = addon_utils.enable(
                    PACKAGE, default_set=False, persistent=False)
                assert module is not None
                enabled = True
                assert all(hasattr(bpy.types.Scene, name) for name in PROPERTIES)
                assert len(module._REGISTERED) == len(module._CLASSES)
                addon_utils.disable(PACKAGE, default_set=False)
                enabled = False
                assert_detached(module)
            checks.append("native_r7_enable_disable_after_recovery_2")

            # R8: class *unregistration* fails, not registration. It leaves
            # exactly one actual Blender class live while a CBDK-owned Scene
            # descriptor is replaced with a synthetic foreign declaration.
            # The first unregister must preserve it despite the partial
            # failure; the retry must release the remaining class only.
            for replaced in PROPERTIES:
                module.register()
                fail_class = module._REGISTERED[-1]
                previous = bpy.types.Scene.__dict__.get(replaced)
                assert previous is not None
                native_unregister = bpy.utils.unregister_class
                injection = [False]
                foreign_descriptor = [None]

                def fail_once_during_unregister(cls):
                    if cls is fail_class and not injection[0]:
                        injection[0] = True
                        if replaced == PROPERTIES[0]:
                            bpy.types.Scene.cbdk_modular_result = (
                                bpy.props.StringProperty(
                                    default="CBDK R8 synthetic foreign"))
                        else:
                            bpy.types.Scene.cbdk_modular_nudge_offset = (
                                bpy.props.FloatVectorProperty(
                                    size=3, default=(0.0, 0.0, 0.75)))
                        foreign_descriptor[0] = (
                            bpy.types.Scene.__dict__.get(replaced))
                        assert (foreign_descriptor[0] is not None
                                and foreign_descriptor[0] is not previous)
                        raise RuntimeError(
                            "CBDK R8 injected unregister_class failure")
                    return native_unregister(cls)

                bpy.utils.unregister_class = fail_once_during_unregister
                try:
                    try:
                        module.unregister()
                    except RuntimeError as exc:
                        assert "cleanup incomplete" in str(exc), str(exc)
                    else:
                        raise AssertionError("R8 class detach failure swallowed")
                finally:
                    bpy.utils.unregister_class = native_unregister

                try:
                    assert injection[0]
                    assert module._REGISTERED == [fail_class]
                    assert not module._OWNED_PROPERTIES
                    assert not module._OWNED_PROPERTY_TOKENS
                    assert bpy.types.Scene.__dict__.get(replaced) is (
                        foreign_descriptor[0])
                    # A partial detach is still live; R6's guard must not
                    # silently reinitialize ownership on importlib.reload.
                    try:
                        importlib.reload(module)
                    except RuntimeError as exc:
                        assert "unregistered before module reload" in str(exc)
                    else:
                        raise AssertionError("R8 partial detach reload accepted")
                    assert module._REGISTERED == [fail_class]
                    assert bpy.types.Scene.__dict__.get(replaced) is (
                        foreign_descriptor[0])
                    module.unregister()
                    assert not module._REGISTERED
                    assert not module._OWNED_PROPERTIES
                    assert not module._OWNED_PROPERTY_TOKENS
                    assert not hasattr(
                        bpy.types, "VIEW3D_PT_cbdk_modular_preview")
                    assert bpy.types.Scene.__dict__.get(replaced) is (
                        foreign_descriptor[0])
                    try:
                        module.register()
                    except RuntimeError as exc:
                        assert "Scene properties conflict" in str(exc), str(exc)
                    else:
                        raise AssertionError("R8 foreign descriptor overwritten")
                finally:
                    # Remove only the CBDK-authored foreign stand-in, never
                    # arbitrary third-party or input Scene properties.
                    if (bpy.types.Scene.__dict__.get(replaced)
                            is foreign_descriptor[0]):
                        delattr(bpy.types.Scene, replaced)
                assert_detached(module)
                assert importlib.reload(module) is module
                module.register()
                module.unregister()
                assert_detached(module)
            checks.append("native_r8_partial_unregister_foreign_retry")
            checks.append("native_r8_partial_unregister_reload_fail_closed")

            # R8: canceled edit operators must not alter the input mesh,
            # vertex/edge/face selection, active object or current mode.
            # Read Blender's *live Edit BMesh* instead of stale Mesh.vertices
            # flags while an object is in Edit Mode.
            module.register()
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            assert bpy.context.mode == "EDIT_MESH"

            def edit_input_snapshot():
                bm = bmesh.from_edit_mesh(mesh)
                return (
                    tuple((tuple(float(v.co[i]) for i in range(3)),
                           bool(v.select), bool(v.hide)) for v in bm.verts),
                    tuple((bool(e.select), bool(e.hide)) for e in bm.edges),
                    tuple((bool(f.select), bool(f.hide)) for f in bm.faces),
                    bpy.context.mode,
                    bpy.context.view_layer.objects.active,
                )

            try:
                bpy.ops.mesh.select_all(action="DESELECT")
                snapshot = edit_input_snapshot()
                last_result = bpy.context.scene.cbdk_modular_result
                assert bpy.ops.cbdk.modular_vertex_nudge() == {"CANCELLED"}
                assert edit_input_snapshot() == snapshot
                assert bpy.context.scene.cbdk_modular_result == last_result
                checks.append("native_r8_validation_cancel_input_unchanged")

                bpy.ops.mesh.select_all(action="SELECT")
                assert any(v.select for v in bmesh.from_edit_mesh(mesh).verts)
                snapshot = edit_input_snapshot()
                last_result = bpy.context.scene.cbdk_modular_result
                nudge = module._FEATURE_MODULES["vertex_nudge"]
                counter = module._FEATURE_MODULES["edit_selection"]
                original_translate = nudge.translate_selected_vertices
                original_count = counter.count_edit_selection

                def raise_nudge_validation(context, offset):
                    raise nudge.BlenderContextError(
                        "CBDK R8 controlled nudge validation")

                def raise_count_validation(context):
                    raise counter.BlenderContextError(
                        "CBDK R8 controlled selection read failure")

                try:
                    nudge.translate_selected_vertices = raise_nudge_validation
                    counter.count_edit_selection = raise_count_validation
                    assert bpy.ops.cbdk.modular_vertex_nudge() == {"CANCELLED"}
                    assert edit_input_snapshot() == snapshot
                    assert bpy.context.scene.cbdk_modular_result == last_result
                    assert bpy.ops.cbdk.modular_edit_selection() == {"CANCELLED"}
                    assert edit_input_snapshot() == snapshot
                    assert bpy.context.scene.cbdk_modular_result == last_result
                finally:
                    nudge.translate_selected_vertices = original_translate
                    counter.count_edit_selection = original_count
                checks.append("native_r8_guarded_exception_cancel_input_unchanged")
            finally:
                if bpy.context.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                module.unregister()
                assert_detached(module)
            assert tuple(tuple(v.co) for v in mesh.vertices) == before
            checks.append("native_r8_edit_mode_cleanup_after_cancellation")
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
