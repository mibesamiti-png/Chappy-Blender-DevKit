"""R17 recipe-specific declarative UI: plan, package and native fixture.

The native function is called by the existing C-owned Blender lifecycle
script. Ordinary unittest never imports bpy or executes generated code.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, build_addon
from cbdk.modular_builder import (
    PACKAGE_ID, build_modular, plan_modular_recipe, validate_modular_recipe,
)


def make_recipe(variant):
    recipe = json.loads((ROOT / "recipes/modular_all.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "catalog/ui_layouts.json").read_text(encoding="utf-8"))
    objects, edit = data["sections"]
    # The R17 fixtures continue to cover exactly their original five features.
    objects["controls"] = [c for c in objects["controls"]
                           if c["feature_id"] in recipe["features"]]
    if variant == "compact":
        recipe["display_name"] = "CBDK Compact Preview"
        objects.update(title="Quick inspection", layout="row", boxed=False,
                       visible_in="object")
        edit.update(title="Small edits", visible_in="edit_mesh")
        objects["controls"][0]["label"] = "Count meshes"
        edit["controls"][1]["label"] = "Step Z"
        edit["controls"][1]["parameters"] = {
            "offset": {"default": [0, 0, .25], "min": -1, "max": 1}}
    elif variant == "grouped":
        recipe["display_name"] = "CBDK Grouped Preview"
        objects.update(title="Geometry tools", boxed=True, visible_in="object")
        selection = objects["controls"].pop(0)
        selection["label"] = "Mesh count"
        edit.update(title="Precision edit", layout="row", boxed=False,
                    visible_in="edit_mesh")
        edit["controls"].reverse()
        edit["controls"][0]["label"] = "Precision shift"
        edit["controls"][0]["parameters"] = {
            "offset": {"default": [.125, 0, 0], "min": -.5, "max": .5}}
        data["sections"] = [edit, {"id": "selection", "title": "Selection tools",
                                   "visible_in": "object", "controls": [selection]},
                            objects]
    else:
        raise ValueError("Unknown test fixture")
    recipe["ui_layout"] = data
    return recipe


class RecipeLayoutR17Tests(unittest.TestCase):
    def test_plan_build_two_independent_layouts_and_legacy(self):
        legacy = json.loads((ROOT / "recipes/modular_all.json").read_text(encoding="utf-8"))
        default = plan_modular_recipe(legacy, root=ROOT, include_ui=True)
        self.assertEqual([t for t, _ in default["ui_layout"]["sections"]],
                         ["Inspection", "Edit Mode"])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            results = []
            for variant in ("compact", "grouped"):
                recipe = make_recipe(variant)
                plans = [plan_modular_recipe(recipe, root=ROOT, target_blender=v,
                                             include_ui=True)
                         for v in ("4.4.3", "4.5.15", "5.2.1")]
                self.assertTrue(all(p["ui_layout"] == plans[0]["ui_layout"] for p in plans))
                plan = plans[0]
                self.assertEqual(plan["ordered_features"], default["ordered_features"])
                self.assertEqual(plan["part_ids"], default["part_ids"])
                self.assertFalse(plan["ui_layout"]["runtime_verified"])
                recipe_path = root / (variant + ".json")
                recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
                target = root / (variant + ".zip")
                build_addon(recipe_path, target, root=ROOT, preview_unapproved=True)
                with ZipFile(target) as archive:
                    metadata = json.loads(archive.read(PACKAGE_ID + "/CBDK_BUILD_INFO.json"))
                    tree = ast.parse(archive.read(PACKAGE_ID + "/__init__.py"))
                    assignments = {n.targets[0].id: n.value for n in tree.body
                                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
                    sections = ast.literal_eval(assignments["_UI_SECTIONS"])
                    options = ast.literal_eval(assignments["_UI_OPTIONS"])
                    self.assertEqual(sections, plan["ui_layout"]["sections"])
                    self.assertEqual(options, plan["ui_layout"]["options"])
                    self.assertEqual(metadata["ui_layout"], "recipe.ui_layout")
                    self.assertEqual(metadata["ui_options"], json.loads(json.dumps(options)))
                    self.assertFalse(metadata["approved"])
                    self.assertFalse(metadata["blender_runtime_verified_for_this_build"])
                repeat = root / (variant + "-repeat.zip")
                build_modular(recipe, repeat, root=ROOT, preview_unapproved=True)
                self.assertEqual(target.read_bytes(), repeat.read_bytes())
                results.append((sections, options))
            self.assertNotEqual(results[0], results[1])
            self.assertEqual(default, plan_modular_recipe(legacy, root=ROOT, include_ui=True))

    def test_explicit_subset_has_exact_resolved_coverage(self):
        recipe = make_recipe("compact")
        recipe["features"] = ["vertex_nudge"]
        edit = recipe["ui_layout"]["sections"][1]
        edit["controls"] = [edit["controls"][1]]
        recipe["ui_layout"]["sections"] = [edit]
        plan = plan_modular_recipe(recipe, root=ROOT, include_ui=True)
        self.assertEqual(plan["ui_layout"]["sections"],
                         (("Small edits", (("vertex_nudge", "Step Z"),)),))

    def test_invalid_layouts_are_refused_before_output_even_without_ui_plan(self):
        bad = []
        for value in (None, "catalog/elsewhere.json", [], {"python": "arbitrary"}):
            recipe = make_recipe("compact")
            recipe["ui_layout"] = value
            bad.append(recipe)
        for field, value in (("operator", "wm.open_mainfile"),
                             ("source", "../external.py"), ("label", "bad\nlabel"),
                             ("visible_in", "edit_mesh")):
            recipe = make_recipe("compact")
            recipe["ui_layout"]["sections"][0]["controls"][0][field] = value
            bad.append(recipe)
        recipe = make_recipe("compact")
        recipe["ui_layout"]["sections"][0]["controls"].pop()
        bad.append(recipe)
        recipe = make_recipe("compact")
        recipe["ui_layout"]["sections"][1]["controls"][1]["parameters"]["offset"]["max"] = 11
        bad.append(recipe)
        recipe = make_recipe("compact")
        recipe["features"] = ["vertex_nudge"]
        bad.append(recipe)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "invalid.zip"
            for recipe in bad:
                with self.subTest(recipe=recipe):
                    with self.assertRaises(ValueError):
                        plan_modular_recipe(recipe, root=ROOT)
                    with self.assertRaises(ValueError):
                        build_modular(recipe, path, root=ROOT, preview_unapproved=True)
                    self.assertFalse(path.exists())

    def test_native_fixture_has_only_fixed_trusted_imports(self):
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        allowed = {"ast", "json", "pathlib", "tempfile", "unittest", "zipfile",
                   "__future__", "cbdk.addon_builder", "cbdk.modular_builder",
                   "importlib", "sys", "types", "bmesh", "bpy"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(a.name in allowed for a in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertIn(node.module, allowed)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__"})
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                    self.assertEqual(ast.unparse(node.args[0]), "PACKAGE_ID")
        self.assertEqual(PACKAGE_ID, "cbdk_modular_preview")

    def test_legacy_planner_refuses_custom_rather_than_misreport_global(self):
        with self.assertRaisesRegex(ValueError, "plan_modular_recipe"):
            validate_modular_recipe(make_recipe("compact"))


def run_native():
    """Generate two authored ZIPs, verify draw and real operators in Blender."""
    import importlib
    import sys
    from types import SimpleNamespace
    import bmesh
    import bpy

    ids = {
        "object_selection": "cbdk.modular_selected_meshes",
        "mesh_bounds": "cbdk.modular_mesh_bounds",
        "modifier_summary": "cbdk.modular_modifier_summary",
        "edit_selection": "cbdk.modular_edit_selection",
        "vertex_nudge": "cbdk.modular_vertex_nudge",
    }

    class RecordingLayout:
        def __init__(self, events=None, path=(), enabled=True):
            self.events = [] if events is None else events
            self.path = path
            self.enabled = enabled

        def child(self, kind):
            return RecordingLayout(self.events, self.path + (kind,), self.enabled)

        def column(self, align=False):
            return self.child("column")

        def row(self, align=False):
            return self.child("row")

        def box(self):
            return self.child("box")

        def label(self, *, text):
            self.events.append(("label", text))

        def prop(self, data, name, *, text):
            self.events.append(("prop", name, self.enabled))

        def operator(self, identifier, *, text):
            button = SimpleNamespace(offset=None)
            self.events.append(("operator", identifier, text, self.path, self.enabled, button))
            return button

    def purge_detached_preview():
        old = sys.modules.get(PACKAGE_ID)
        if old is not None:
            assert not old._REGISTERED and not old._OWNED_PROPERTIES
            assert not old._OWNED_PROPERTY_TOKENS
        assert not hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview")
        for name in list(sys.modules):
            if name == PACKAGE_ID or name.startswith(PACKAGE_ID + "."):
                del sys.modules[name]

    markers = []
    for variant in ("compact", "grouped"):
        purge_detached_preview()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        recipe = make_recipe(variant)
        version = ".".join(map(str, bpy.app.version))
        plan = plan_modular_recipe(recipe, root=ROOT, target_blender=version,
                                   include_ui=True)["ui_layout"]
        with tempfile.TemporaryDirectory(prefix="cbdk-r17-") as directory:
            root = Path(directory)
            target = root / "preview.zip"
            build_modular(recipe, target, root=ROOT, preview_unapproved=True,
                          target_blender=version)
            with ZipFile(target) as archive:
                assert all(n.startswith(PACKAGE_ID + "/") and
                           not any(p in ("", ".", "..") for p in n.split("/"))
                           for n in archive.namelist())
                archive.extractall(root)
            sys.path.insert(0, directory)
            module = None
            registered = False
            try:
                importlib.invalidate_caches()
                module = importlib.import_module(PACKAGE_ID)
                assert Path(module.__file__).resolve().is_relative_to(root.resolve())
                assert module._UI_SECTIONS == plan["sections"]
                assert module._UI_OPTIONS == plan["options"]
                module.register()
                registered = True
                assert set(module._FEATURE_IDS) == set(ids)
                spec = plan["options"]["nudge_offset"]
                scene = bpy.context.scene
                assert tuple(scene.cbdk_modular_nudge_offset) == spec["default"]
                assert not hasattr(bpy.types.Scene, "cbdk_modular_center_precision")
                rna = scene.bl_rna.properties["cbdk_modular_nudge_offset"]
                assert rna.array_length == 3
                assert rna.hard_min == spec["min"] and rna.hard_max == spec["max"]

                mesh = bpy.data.meshes.new("CBDK_R17_triangle")
                mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
                mesh.update()
                obj = bpy.data.objects.new("CBDK_R17_object", mesh)
                scene.collection.objects.link(obj)
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                def draw(mode):
                    recorder = RecordingLayout()
                    module.VIEW3D_PT_cbdk_modular_preview.draw(
                        SimpleNamespace(layout=recorder), bpy.context)
                    events = [e for e in recorder.events if e[0] == "operator"]
                    expected = []
                    titles = []
                    for index, (title, controls) in enumerate(plan["sections"]):
                        style = plan["options"]["section_styles"][index]
                        if style["visible_in"] not in ("always", mode):
                            continue
                        visible = [(f, l) for (f, l), m in
                                   zip(controls, plan["options"]["control_visibility"][index])
                                   if m in ("always", mode)]
                        if not visible:
                            continue
                        titles.append(title)
                        group_path = ("column", "box" if style["boxed"] else "column")
                        if style["layout"] == "row":
                            group_path += ("row",)
                        for feature, label in visible:
                            path = group_path + ("row",)
                            if feature == "vertex_nudge":
                                path += ("row",)
                            expected.append((ids[feature], label, path, True))
                    assert [e[1:5] for e in events] == expected, (variant, events, expected)
                    assert all(("label", title) in recorder.events for title in titles)
                    return {e[1]: e[5] for e in events}

                assert bpy.context.mode == "OBJECT"
                assert set(draw("object")) == {ids[f] for f in
                                              ("object_selection", "mesh_bounds", "modifier_summary")}
                for call in (bpy.ops.cbdk.modular_selected_meshes,
                             bpy.ops.cbdk.modular_mesh_bounds,
                             bpy.ops.cbdk.modular_modifier_summary):
                    assert call() == {"FINISHED"}
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="DESELECT")
                bm = bmesh.from_edit_mesh(mesh)
                bm.verts.ensure_lookup_table()
                bm.verts[0].select_set(True)
                bm.select_flush_mode()
                bmesh.update_edit_mesh(mesh)
                assert sum(v.select for v in bm.verts) == 1
                buttons = draw("edit_mesh")
                assert set(buttons) == {ids["edit_selection"], ids["vertex_nudge"]}
                assert bpy.ops.cbdk.modular_edit_selection() == {"FINISHED"}
                offset = tuple(buttons[ids["vertex_nudge"]].offset)
                assert offset == spec["default"]
                before = tuple(tuple(v.co) for v in bm.verts)
                assert bpy.ops.cbdk.modular_vertex_nudge(offset=offset) == {"FINISHED"}
                after = tuple(tuple(v.co) for v in bmesh.from_edit_mesh(mesh).verts)
                for i, coords in enumerate(before):
                    assert all(abs(after[i][a] - coords[a] -
                                   (offset[a] if i == 0 else 0.0)) < 1e-6
                               for a in range(3))
                bpy.ops.object.mode_set(mode="OBJECT")
                module.unregister()
                registered = False
                assert not module._REGISTERED and not module._OWNED_PROPERTIES
                assert not module._OWNED_PROPERTY_TOKENS
                assert not hasattr(bpy.types, "VIEW3D_PT_cbdk_modular_preview")
                assert not hasattr(bpy.types.Scene, "cbdk_modular_result")
                assert not hasattr(bpy.types.Scene, "cbdk_modular_nudge_offset")
                markers.append("native_r17_recipe_" + variant + "_plan_draw_execute_cleanup")
            finally:
                if bpy.context.mode == "EDIT_MESH":
                    bpy.ops.object.mode_set(mode="OBJECT")
                if registered:
                    module.unregister()
                purge_detached_preview()
                sys.path.remove(directory)
    # R18 uses the same trusted build/import/draw/cleanup lane, separately
    # from the two unchanged five-feature R17 regression fixtures.
    for inline, typed in ((False, False), (True, False), (False, True), (True, True)):
        purge_detached_preview()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        recipe = make_r18_recipe(inline)
        if typed and inline:
            recipe["ui_layout"]["sections"][0]["controls"][0]["parameters"] = {
                "precision": {"default": 1, "min": 1, "max": 4}}
        version = ".".join(map(str, bpy.app.version))
        plan = plan_modular_recipe(recipe, root=ROOT, target_blender=version,
                                   include_ui=True)
        with tempfile.TemporaryDirectory(prefix="cbdk-r18-") as directory:
            root = Path(directory)
            target = root / "preview.zip"
            build_modular(recipe, target, root=ROOT, preview_unapproved=True,
                          target_blender=version)
            with ZipFile(target) as archive:
                assert all(n.startswith(PACKAGE_ID + "/") and
                           not any(p in ("", ".", "..") for p in n.split("/"))
                           for n in archive.namelist())
                archive.extractall(root)
            sys.path.insert(0, directory)
            module = None
            registered = False
            try:
                importlib.invalidate_caches()
                module = importlib.import_module(PACKAGE_ID)
                assert Path(module.__file__).resolve().is_relative_to(root.resolve())
                assert module._UI_SECTIONS == plan["ui_layout"]["sections"]
                assert module._UI_OPTIONS == plan["ui_layout"]["options"]
                assert set(module._FEATURE_IDS) == {"mesh_bounds", "mesh_center"}
                module.register()
                registered = True
                mesh = bpy.data.meshes.new("CBDK_R18_asymmetric")
                mesh.from_pydata([(-2, 0, 1), (4, 1, 5), (0, 3, 2)], [], [(0, 1, 2)])
                mesh.update()
                scene = bpy.context.scene
                obj = bpy.data.objects.new("CBDK_R18_object", mesh)
                scene.collection.objects.link(obj)
                obj.location = (10, -2, 1)
                obj.scale = (2, 1, 3)
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.context.view_layer.update()
                before = tuple(tuple(v.co) for v in mesh.vertices)
                recorder = RecordingLayout()
                module.VIEW3D_PT_cbdk_modular_preview.draw(
                    SimpleNamespace(layout=recorder), bpy.context)
                events = [e for e in recorder.events if e[0] == "operator"]
                assert {e[1] for e in events} == {"cbdk.modular_mesh_bounds", "cbdk.modular_mesh_center"}
                assert all(e[4] for e in events)
                assert [e[2] for e in events] == [
                    label for _, controls in plan["ui_layout"]["sections"]
                    for _, label in controls]
                assert bpy.ops.cbdk.modular_mesh_bounds() == {"FINISHED"}
                assert bpy.ops.cbdk.modular_mesh_center() == {"FINISHED"}
                # Independent: local box [-2,0,1]..[4,3,5]; diagonal scale
                # and translation yield world center (12,-0.5,10).
                expected = "World bounds center (base): 12.0, -0.5, 10.0" if typed and inline else "World bounds center (base): 12.000, -0.500, 10.000"
                assert scene.cbdk_modular_result == expected
                if typed:
                    rna = scene.bl_rna.properties["cbdk_modular_center_precision"]
                    assert rna.type == "INT"
                    assert scene.cbdk_modular_center_precision == (1 if inline else 3)
                    assert (rna.hard_min, rna.hard_max) == ((1, 4) if inline else (0, 6))
                    assert ("prop", "cbdk_modular_center_precision", True) in recorder.events
                    scene.cbdk_modular_center_precision = 2
                    assert bpy.ops.cbdk.modular_mesh_center() == {"FINISHED"}
                    expected = "World bounds center (base): 12.00, -0.50, 10.00"
                    assert scene.cbdk_modular_result == expected
                assert tuple(tuple(v.co) for v in mesh.vertices) == before
                assert bpy.context.view_layer.objects.active == obj and obj.select_get()
                bpy.ops.object.mode_set(mode="EDIT")
                assert bpy.ops.cbdk.modular_mesh_center() == {"CANCELLED"}
                assert scene.cbdk_modular_result == expected
                bpy.ops.object.mode_set(mode="OBJECT")
                module.unregister()
                registered = False
                assert not module._REGISTERED and not module._OWNED_PROPERTIES
                assert not module._OWNED_PROPERTY_TOKENS
                assert not hasattr(bpy.types.Scene, "cbdk_modular_result")
                assert not hasattr(bpy.types.Scene, "cbdk_modular_center_precision")
                if typed:
                    # Foreign property collision must be detected before any registration.
                    bpy.types.Scene.cbdk_modular_center_precision = bpy.props.IntProperty(default=5)
                    token = bpy.types.Scene.__dict__["cbdk_modular_center_precision"]
                    try:
                        try:
                            module.register()
                        except RuntimeError as exc:
                            assert "conflict" in str(exc)
                        else:
                            raise AssertionError("Foreign precision property accepted")
                        assert bpy.types.Scene.__dict__["cbdk_modular_center_precision"] is token
                        assert not module._REGISTERED and not module._OWNED_PROPERTIES
                    finally:
                        del bpy.types.Scene.cbdk_modular_center_precision
                    module.register()
                    registered = True
                    module.unregister()
                    registered = False
                    assert not hasattr(bpy.types.Scene, "cbdk_modular_center_precision")
                markers.append(("native_r19_typed_" if typed else "native_r18_center_") +
                               ("inline" if inline else "global") +
                               "_plan_draw_execute_cleanup")
            finally:
                if bpy.context.mode == "EDIT_MESH":
                    bpy.ops.object.mode_set(mode="OBJECT")
                if registered:
                    module.unregister()
                purge_detached_preview()
                sys.path.remove(directory)
    return markers


def make_r18_recipe(inline=False):
    recipe = json.loads((ROOT / "recipes/modular_geometry.json").read_text(encoding="utf-8"))
    recipe["features"] = ["mesh_bounds", "mesh_center"]
    if inline:
        recipe["ui_layout"] = {"schema_version": 1,
            "kind": "cbdk_authored_preview_ui_layout", "preview_only": True,
            "sections": [{"id": "center", "title": "Center", "visible_in": "object",
                "layout": "row", "controls": [
                    {"feature_id": "mesh_center", "label": "Find center"},
                    {"feature_id": "mesh_bounds", "label": "Read bounds"}]}]}
    return recipe


class DescriptorR18Tests(unittest.TestCase):
    def test_new_feature_global_and_inline_and_legacy(self):
        legacy = json.loads((ROOT / "recipes/modular_all.json").read_text(encoding="utf-8"))
        self.assertEqual(set(plan_modular_recipe(legacy, root=ROOT)["ordered_features"]),
                         {"mesh_bounds", "modifier_summary", "vertex_nudge",
                          "edit_selection", "object_selection"})
        with tempfile.TemporaryDirectory() as directory:
            for inline in (False, True):
                recipe = make_r18_recipe(inline)
                plan = plan_modular_recipe(recipe, root=ROOT, include_ui=True)
                self.assertEqual(set(plan["ordered_features"]), {"mesh_center", "mesh_bounds"})
                self.assertEqual(plan["part_ids"], ["BLCTX-001", "BLGEO-001"])
                target = Path(directory) / (str(inline) + ".zip")
                build_modular(recipe, target, root=ROOT, preview_unapproved=True)
                with ZipFile(target) as archive:
                    tree = ast.parse(archive.read(PACKAGE_ID + "/__init__.py"))
                    assignments = {n.targets[0].id: n.value for n in tree.body
                                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
                    contract = ast.literal_eval(assignments["_FEATURE_CONTRACT"])
                    self.assertEqual(set(contract), {"mesh_bounds", "mesh_center"})
                    self.assertEqual(contract["mesh_center"]["operator"], "cbdk.modular_mesh_center")
                    self.assertEqual(contract["mesh_center"]["mode"], "OBJECT")
                    self.assertIn(PACKAGE_ID + "/features/mesh_center.py", archive.namelist())
                    self.assertNotIn(PACKAGE_ID + "/features/vertex_nudge.py", archive.namelist())
                    self.assertEqual(ast.literal_eval(assignments["_UI_SECTIONS"]),
                                     plan["ui_layout"]["sections"])

    def test_unknown_and_unselected_features_and_injected_descriptor_rejected(self):
        for mutate in ("unknown", "unselected", "operator"):
            recipe = make_r18_recipe(True)
            if mutate == "unknown":
                recipe["features"].append("unknown")
            elif mutate == "unselected":
                recipe["features"].remove("mesh_center")
            else:
                recipe["ui_layout"]["sections"][0]["controls"][0]["operator"] = "wm.open_mainfile"
            with self.assertRaises(ValueError):
                plan_modular_recipe(recipe, root=ROOT, include_ui=True)


if __name__ == "__main__":
    unittest.main()
