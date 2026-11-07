"""Mode-scoped composition and bounded cleanup for the CBDK-authored preview."""
from __future__ import annotations

import ast
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, build_addon
from cbdk.ui_layout import plan_ui_layout, validate_ui_layout


SOURCES = (
    "catalog/authored_parts.json", "catalog/addon_features.json",
    "catalog/ui_layouts.json",
    "parts/blender/context.py", "parts/blender/edit_mesh.py",
    "parts/blender/edit_transform.py", "parts/blender/edit_audit.py",
    "parts/blender/measure.py", "parts/blender/modifiers.py",
    "templates/modular_preview/__init__.py",
    "templates/modular_preview/features/object_selection.py",
    "templates/modular_preview/features/edit_selection.py",
    "templates/modular_preview/features/mesh_bounds.py",
    "templates/modular_preview/features/modifier_summary.py",
    "templates/modular_preview/features/vertex_nudge.py",
)


class ComposedPreviewTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for relative in SOURCES:
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, dest)
        self.catalog = self.root / "catalog/ui_layouts.json"
        self.doc = json.loads(self.catalog.read_text(encoding="utf-8"))

    def save(self):
        self.catalog.write_text(json.dumps(self.doc), encoding="utf-8")

    def combine(self):
        # One mixed panel: Object and Edit controls are independently shown,
        # without adding any feature, source path, or executable operator.
        nudge = self.doc["sections"][1]["controls"].pop()
        nudge["visible_in"] = "edit_mesh"
        self.doc["sections"][0]["controls"][0]["visible_in"] = "object"
        self.doc["sections"][0]["controls"].append(nudge)
        self.save()

    def test_legacy_catalog_includes_default_always_modes(self):
        plan, options = plan_ui_layout(
            ["object_selection", "vertex_nudge"], root=self.root, include_options=True)
        self.assertEqual([len(section[1]) for section in plan], [1, 1])
        self.assertEqual(options["control_visibility"], (("always",), ("always",)))

    def test_mixed_panel_mode_filter_and_order(self):
        self.combine()
        validate_ui_layout(self.doc)
        plan, options = plan_ui_layout(
            ["vertex_nudge", "object_selection"], root=self.root, include_options=True)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0][0], "Inspection")
        self.assertEqual([item[0] for item in plan[0][1]],
                         ["object_selection", "vertex_nudge"])
        self.assertEqual(options["control_visibility"], (("object", "edit_mesh"),))
        self.assertEqual(options["section_styles"][0]["visible_in"], "always")

    def test_reject_wrong_modes_unknown_keys_and_expression(self):
        for feature_index, mode in ((0, "edit_mesh"), (0, "context.mode"),
                                    (0, True), (0, None)):
            with self.subTest(mode=mode):
                candidate = json.loads(self.catalog.read_text(encoding="utf-8"))
                candidate["sections"][0]["controls"][feature_index]["visible_in"] = mode
                with self.assertRaises(ValueError):
                    validate_ui_layout(candidate)
        self.doc["sections"][1]["controls"][1]["visible_in"] = "object"
        with self.assertRaises(ValueError):
            validate_ui_layout(self.doc)
        del self.doc["sections"][1]["controls"][1]["visible_in"]
        self.doc["sections"][0]["controls"][0]["operator_id"] = "bpy.ops.wm.quit_blender"
        with self.assertRaises(ValueError):
            validate_ui_layout(self.doc)

    def test_generated_zip_preserves_mode_plan_without_new_operator(self):
        self.combine()
        recipe = {
            "schema_version": 2, "template": "modular_preview",
            "package_id": "cbdk_modular_preview", "display_name": "Composed UI Preview",
            "features": ["vertex_nudge", "object_selection"],
            "purpose": "local_development_preview",
        }
        recipe_file = self.root / "recipe.json"
        recipe_file.write_text(json.dumps(recipe), encoding="utf-8")
        archive_file = self.root / "preview.zip"
        build_addon(recipe_file, archive_file,
                    preview_unapproved=True, root=self.root)
        with ZipFile(archive_file) as archive:
            folder = "cbdk_modular_preview/"
            source = archive.read(folder + "__init__.py").decode("utf-8")
            info = json.loads(archive.read(folder + "CBDK_BUILD_INFO.json"))
        ast.parse(source)
        self.assertEqual(info["ui_options"]["control_visibility"],
                         [["object", "edit_mesh"]])
        self.assertEqual(info["features"], ["object_selection", "vertex_nudge"])
        self.assertFalse(info["approved"])
        self.assertIn('if not visible_buttons:', source)
        self.assertIn('for feature_id, label in visible_buttons:', source)

    def test_invalid_visibility_prevents_archive_creation(self):
        self.doc["sections"][0]["controls"][0]["visible_in"] = "edit_mesh"
        self.save()
        path = self.root / "recipe.json"
        path.write_text(json.dumps({
            "schema_version": 2, "template": "modular_preview",
            "package_id": "cbdk_modular_preview",
            "display_name": "Invalid Scoped UI",
            "features": ["object_selection"], "purpose": "local_development_preview",
        }), encoding="utf-8")
        output = self.root / "bad.zip"
        with self.assertRaises(ValueError):
            build_addon(path, output, preview_unapproved=True, root=self.root)
        self.assertFalse(output.exists())


class RecoveryTests(unittest.TestCase):
    """Execute ONLY the repository-owned register/unregister template functions."""

    def setUp(self):
        class Scene:
            pass

        class FakeUtils:
            def __init__(self):
                self.active = set()
                self.fail_register = None
                self.fail_unregister = None

            def register_class(self, cls):
                if cls is self.fail_register:
                    raise RuntimeError("controlled registration refusal")
                self.active.add(cls)

            def unregister_class(self, cls):
                if cls is self.fail_unregister:
                    self.fail_unregister = None
                    raise RuntimeError("controlled unregister refusal")
                self.active.remove(cls)

        self.utils = FakeUtils()
        self.first = type("CBDK_Test_One", (), {})
        self.second = type("CBDK_Test_Two", (), {})
        props = SimpleNamespace(StringProperty=lambda **kw: kw,
                                FloatVectorProperty=lambda **kw: kw)
        bpy = SimpleNamespace(types=SimpleNamespace(Scene=Scene),
                              props=props, utils=self.utils)
        source = (ROOT / "templates/modular_preview/__init__.py").read_text()
        tree = ast.parse(source)
        functions = [n for n in tree.body
                     if isinstance(n, ast.FunctionDef)
                     and n.name in ("register", "unregister")]
        self.assertEqual(len(functions), 2)
        self.namespace = {
            "bpy": bpy, "_CLASSES": (self.first, self.second),
            "_REGISTERED": [], "_OWNED_PROPERTIES": [], "_OWNED_PROPERTY_TOKENS": {},
            "_PROPERTY_NAMES": ("cbdk_modular_result", "cbdk_modular_nudge_offset"),
            "_UI_OPTIONS": {"nudge_offset": {
                "size": 3, "default": (0., 0., .1), "min": -10., "max": 10.}},
        }
        compiled = compile(ast.fix_missing_locations(
            ast.Module(body=functions, type_ignores=[])), "<trusted-CBDK-template>", "exec")
        exec(compiled, self.namespace)

    def test_register_failure_cleans_own_classes_and_properties(self):
        self.utils.fail_register = self.second
        with self.assertRaisesRegex(RuntimeError, "controlled registration refusal"):
            self.namespace["register"]()
        self.assertFalse(self.utils.active)
        self.assertFalse(self.namespace["_REGISTERED"])
        self.assertFalse(self.namespace["_OWNED_PROPERTIES"])
        self.assertFalse(hasattr(self.namespace["bpy"].types.Scene, "cbdk_modular_result"))
        self.utils.fail_register = None
        self.namespace["register"]()
        self.namespace["unregister"]()
        self.assertFalse(self.utils.active)

    def test_unregister_failure_continues_properties_and_is_retryable(self):
        self.namespace["register"]()
        self.utils.fail_unregister = self.first
        with self.assertRaisesRegex(RuntimeError, "cleanup incomplete"):
            self.namespace["unregister"]()
        self.assertEqual(self.namespace["_REGISTERED"], [self.first])
        self.assertEqual(self.namespace["_OWNED_PROPERTIES"], [])
        self.assertNotIn(self.second, self.utils.active)
        self.assertFalse(hasattr(self.namespace["bpy"].types.Scene, "cbdk_modular_result"))
        with self.assertRaisesRegex(RuntimeError, "already registered"):
            self.namespace["register"]()
        self.namespace["unregister"]()
        self.assertFalse(self.utils.active)
        self.assertFalse(self.namespace["_REGISTERED"])

    def test_primary_registration_error_kept_if_rollback_fails(self):
        self.utils.fail_register = self.second
        self.utils.fail_unregister = self.first
        with self.assertRaisesRegex(RuntimeError, "controlled registration refusal") as raised:
            self.namespace["register"]()
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        self.assertEqual(self.namespace["_REGISTERED"], [self.first])
        self.assertFalse(self.namespace["_OWNED_PROPERTIES"])
        self.namespace["unregister"]()
        self.assertFalse(self.utils.active)


if __name__ == "__main__":
    unittest.main()
