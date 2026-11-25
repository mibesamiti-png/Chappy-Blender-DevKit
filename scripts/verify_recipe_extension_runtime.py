"""Internal CI-only Blender subprocess. Not a general installer."""
import io
import os
from pathlib import Path
import sys
from types import SimpleNamespace
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
    if case in ("grouped", "dependency"):
        sys.path.insert(0, str(ROOT / "tests"))
        from test_ui_recipe_r17 import make_r23_recipe
        recipe = make_r23_recipe("grouped")
        if case == "dependency":
            from extension_r24_dependency_fixture import dependency_recipe, dependency_catalog, ORDER
            from test_ui_recipe_r17 import R24_REGISTRATION
            recipe = dependency_recipe()
    else:
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
    if case == "dependency":
        with dependency_catalog():
            regenerated = build_recipe_extension_bytes(recipe, preview_unapproved=True)
    else:
        regenerated = build_recipe_extension_bytes(recipe, preview_unapproved=True)
    if blob != regenerated:
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
    trace = []
    real_register, real_unregister = bpy.utils.register_class, bpy.utils.unregister_class
    def observed_register(cls):
        real_register(cls)
        if cls.__module__.startswith(namespace):
            trace.append(("register", cls.bl_idname))
    def observed_unregister(cls):
        real_unregister(cls)
        if cls.__module__.startswith(namespace):
            trace.append(("unregister", cls.bl_idname))
    if case == "dependency":
        bpy.utils.register_class = observed_register
    try:
        module = addon_utils.enable(namespace, default_set=True, persistent=False)
    finally:
        if case == "dependency":
            bpy.utils.register_class = real_register
    if module is None:
        raise AssertionError("R23 Extension enable failed")
    classes = tuple(module._CLASSES)
    try:
        if (module.__name__ != namespace or
                Path(module.__file__).resolve() != package / "__init__.py" or
                not addon_utils.check(namespace)[1] or
                bpy.context.preferences.addons.get(namespace) is None or
                (tuple(module._FEATURE_IDS) != ORDER if case == "dependency"
                 else set(module._FEATURE_IDS) != set(recipe["features"])) or
                any(not c.is_registered for c in classes)):
            raise AssertionError("R23 native Extension registration mismatch")
        if case == "dependency" and trace != [("register", name) for name in R24_REGISTRATION]:
            raise AssertionError("R24 A actual Extension registration order mismatch")
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
        if case in ("grouped", "dependency"):
            panels = module._PANEL_CLASSES
            if [(cls.bl_idname, cls.bl_label) for cls in panels] != [
                    ("VIEW3D_PT_cbdk_modular_primary", "Geometry"),
                    ("VIEW3D_PT_cbdk_modular_secondary", "Editing")]:
                raise AssertionError("R23 combined panel registration mismatch")
            if hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview"):
                raise AssertionError("R23 legacy panel unexpectedly registered")
            class Layout:
                def __init__(self, events, enabled=True):
                    self.events, self.enabled = events, enabled
                def column(self, align=False):
                    return Layout(self.events, self.enabled)
                row = column
                def box(self):
                    return self.column()
                def label(self, *, text):
                    pass
                def prop(self, data, name, *, text):
                    self.events.append(("prop", name, self.enabled))
                def operator(self, identifier, *, text):
                    button = SimpleNamespace(offset=None)
                    self.events.append(("operator", identifier, text, self.enabled, button))
                    return button
            def draw():
                result = []
                for cls in panels:
                    events = []
                    cls.draw(SimpleNamespace(layout=Layout(events),
                        _cbdk_section_indices=cls._cbdk_section_indices), bpy.context)
                    result.append(events)
                return result
            def actions(events):
                return [[e[1:4] for e in row if e[0] == "operator"] for row in events]
            delta = (0.0, 0.0, .25)
            if (scene.cbdk_modular_center_precision != 2
                    or tuple(scene.cbdk_modular_nudge_offset) != delta
                    or scene.bl_rna.properties["cbdk_modular_center_precision"].hard_min != 1
                    or scene.bl_rna.properties["cbdk_modular_center_precision"].hard_max != 4
                    or scene.bl_rna.properties["cbdk_modular_nudge_offset"].hard_min != -1
                    or scene.bl_rna.properties["cbdk_modular_nudge_offset"].hard_max != 1):
                raise AssertionError("R23 combined typed RNA mismatch")
            events = draw()
            if (actions(events) != [[("cbdk.modular_mesh_bounds", "Read bounds", True),
                    ("cbdk.modular_mesh_center", "Read center", True)], []]
                    or ("prop", "cbdk_modular_center_precision", True) not in events[0]
                    or any(e[0] == "prop" and e[1] == "cbdk_modular_nudge_offset" for row in events for e in row)):
                raise AssertionError("R23 combined object panel placement mismatch")
            if (bpy.ops.cbdk.modular_mesh_bounds() != {"FINISHED"} or
                    scene.cbdk_modular_result != "World bounds (base): 6.000 x 4.000 x 8.000"):
                raise AssertionError("R23 combined bounds mismatch")
            if (bpy.ops.cbdk.modular_mesh_center() != {"FINISHED"} or
                    scene.cbdk_modular_result != "World bounds center (base): 11.19, 21.31, 31.69"):
                raise AssertionError("R23 combined initial center mismatch")
            scene.cbdk_modular_center_precision = 1
            if (bpy.ops.cbdk.modular_mesh_center() != {"FINISHED"} or
                    scene.cbdk_modular_result != "World bounds center (base): 11.2, 21.3, 31.7"):
                raise AssertionError("R23 combined updated center mismatch")
            saved = scene.cbdk_modular_result
            if (bpy.ops.cbdk.modular_vertex_nudge(offset=delta) != {"CANCELLED"}
                    or [tuple(v.co) for v in mesh.vertices] != before
                    or scene.cbdk_modular_result != saved):
                raise AssertionError("R23 combined wrong-mode guard failed")
            bpy.context.tool_settings.mesh_select_mode = (True, False, False)
            bpy.ops.object.mode_set(mode="EDIT")
            try:
                bpy.ops.mesh.select_all(action="DESELECT")
                bm = bmesh.from_edit_mesh(mesh)
                bm.verts.ensure_lookup_table()
                snapshot = lambda: [tuple(v.co) for v in bm.verts]
                if (bpy.ops.cbdk.modular_vertex_nudge(offset=delta) != {"CANCELLED"}
                        or snapshot() != before or scene.cbdk_modular_result != saved):
                    raise AssertionError("R23 combined empty-selection guard failed")
                bm.verts[0].select_set(True)
                bm.select_flush_mode()
                bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
                events = draw()
                if (actions(events) != [[], [("cbdk.modular_edit_selection", "Count selection", True),
                        ("cbdk.modular_vertex_nudge", "Move selection", True)]]
                        or ("prop", "cbdk_modular_nudge_offset", True) not in events[1]
                        or any(e[0] == "prop" and e[1] == "cbdk_modular_center_precision" for row in events for e in row)):
                    raise AssertionError("R23 combined edit panel placement mismatch")
                if (bpy.ops.cbdk.modular_edit_selection() != {"FINISHED"}
                        or scene.cbdk_modular_result != "Edit selection: V=1 E=0 F=0"):
                    raise AssertionError("R23 combined selection count mismatch")
                button = next(e[4] for e in events[1] if e[0] == "operator" and e[1] == "cbdk.modular_vertex_nudge")
                if tuple(button.offset) != delta:
                    raise AssertionError("R23 combined UI offset mismatch")
                if (bpy.ops.cbdk.modular_vertex_nudge(offset=button.offset) != {"FINISHED"}
                        or scene.cbdk_modular_result != "Moved 1 selected vertices (local)"):
                    raise AssertionError("R23 combined edit failed")
                if (snapshot() != [(-2,-1,-2.75), *before[1:]]
                        or [v.select for v in bm.verts] != [True,False,False]):
                    raise AssertionError("R23 combined selected-only edit mismatch")
            finally:
                bpy.ops.object.mode_set(mode="OBJECT")
            if [tuple(v.co) for v in mesh.vertices] != [(-2,-1,-2.75), *before[1:]]:
                raise AssertionError("R23 combined committed mesh mismatch")
        elif case == "read":
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
        if case == "dependency":
            bpy.utils.unregister_class = observed_unregister
        try:
            addon_utils.disable(namespace, default_set=True)
        finally:
            if case == "dependency":
                bpy.utils.unregister_class = real_unregister
    if (addon_utils.check(namespace)[1] or
            bpy.context.preferences.addons.get(namespace) is not None or
            any(c.is_registered for c in classes) or module._REGISTERED or
            module._OWNED_PROPERTIES or module._OWNED_PROPERTY_TOKENS or
            any(hasattr(bpy.types.Scene, n) for n in
                ("cbdk_modular_result", "cbdk_modular_nudge_offset", "cbdk_modular_center_precision"))):
        raise AssertionError("R23 registration cleanup incomplete")
    if case in ("grouped", "dependency"):
        if any(hasattr(bpy.types, cls.bl_idname) for cls in panels):
            raise AssertionError("R23 combined panel registration leaked")
        if case == "dependency":
            if trace != ([("register", n) for n in R24_REGISTRATION] +
                         [("unregister", n) for n in reversed(R24_REGISTRATION)]):
                raise AssertionError("R24 A actual Extension reverse order mismatch")
            trace.clear()
            def refuse_midpoint(cls):
                if cls.bl_idname == "cbdk.modular_mesh_center":
                    raise RuntimeError("controlled R24 A midpoint refusal")
                observed_register(cls)
            module.bpy = SimpleNamespace(types=bpy.types, props=bpy.props,
                utils=SimpleNamespace(register_class=refuse_midpoint,
                                      unregister_class=observed_unregister))
            try:
                try:
                    module.register()
                except RuntimeError as exc:
                    if "controlled R24 A midpoint refusal" not in str(exc):
                        raise
                else:
                    raise AssertionError("R24 A midpoint refusal not raised")
                if (trace != [("register", "cbdk.modular_mesh_bounds"),
                              ("register", "cbdk.modular_edit_selection"),
                              ("unregister", "cbdk.modular_edit_selection"),
                              ("unregister", "cbdk.modular_mesh_bounds")]
                        or module._REGISTERED or module._OWNED_PROPERTIES
                        or module._OWNED_PROPERTY_TOKENS
                        or any(c.is_registered for c in classes)
                        or any(hasattr(bpy.types.Scene, n) for n in module._PROPERTY_NAMES)):
                    raise AssertionError("R24 A Extension midpoint rollback incomplete")
            finally:
                module.bpy = bpy
                if module._REGISTERED or module._OWNED_PROPERTIES:
                    module.unregister()
            print("CBDK_R24_A_EXTENSION_ORDER_ROLLBACK_PASS: actual register/reverse, midpoint rollback")
            print("CBDK_R24_DEPENDENCY_EXTENSION_RUNTIME_PASS: requested 1, resolved 4, typed read/edit and cleanup")
        else:
            print("CBDK_R23_A_MULTIPANEL_EXTENSION_VERTICAL_PASS: two panels, four features, typed read/edit and cleanup")
    if case != "dependency":
        print("CBDK_R23_RECIPE_EXTENSION_RUNTIME_PASS: " + case)


if __name__ == "__main__":
    verify()
