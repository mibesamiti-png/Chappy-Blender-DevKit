"""Safe declarative Blender panel layout tests. No user source execution."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.addon_builder import ROOT
from cbdk.ui_layout import plan_ui_layout, validate_ui_layout, validate_nudge_settings


class AuthoredUILayoutTests(unittest.TestCase):
    def test_section_modes_are_fixed_literals_and_preserve_legacy_plan(self):
        original = validate_ui_layout(self.data)
        self.data["sections"][0]["visible_in"] = "object"
        self.data["sections"][1]["visible_in"] = "edit_mesh"
        self.assertEqual(validate_ui_layout(self.data), original)
        self.write()
        _, options = plan_ui_layout(["vertex_nudge"], root=self.root, include_options=True)
        self.assertEqual([s["visible_in"] for s in options["section_styles"]], ["edit_mesh"])
        for mode in ("context.mode == 'OBJECT'", "exec(code)", True, None, []):
            with self.subTest(mode=mode):
                self.data["sections"][0]["visible_in"] = mode
                with self.assertRaises(ValueError):
                    validate_ui_layout(self.data)

    def test_typed_bounds_can_only_narrow_and_contain_default(self):
        spec = validate_nudge_settings({"default": [0, 0, .125], "min": -1, "max": 1})
        self.assertEqual(spec["type"], "float_vector")
        self.assertEqual(spec["size"], 3)
        self.assertEqual(spec["max"], 1.0)
        for override in (
            {"min": -11}, {"max": 11}, {"min": True}, {"max": float("inf")},
            {"min": 1}, {"min": 0, "max": 0}, {"default": [2, 0, 0]},
            {"type": "python_expression"},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                validate_nudge_settings({"default": [0, 0, .125], "min": -1, "max": 1, **override})

    def test_visibility_cannot_make_controls_unreachable(self):
        self.data["sections"][1]["visible_in"] = "object"
        with self.assertRaisesRegex(ValueError, "unreachable"):
            validate_ui_layout(self.data)

    def test_legacy_and_structured_defaults_share_one_contract(self):
        old = validate_nudge_settings([0, 0, .1])
        new = validate_nudge_settings({"default": [0, 0, .1], "min": -10, "max": 10})
        self.assertEqual(old, new)
        self.data["sections"][1]["controls"][1]["parameters"] = {"offset": {"default": [0, 0, .25], "min": -1, "max": 1}}
        self.write()
        _, options = plan_ui_layout(["vertex_nudge"], root=self.root, include_options=True)
        self.assertEqual(options["nudge_offset"]["default"], (0.0, 0.0, .25))
        self.assertEqual(options["nudge_offset"]["min"], -1)

    def test_optional_layout_and_typed_offset_preserve_legacy_plan(self):
        original = validate_ui_layout(self.data)
        self.data["sections"][0].update(layout="row", boxed=False)
        self.data["sections"][1]["controls"][1]["parameters"] = {"offset": [0.125, -0.25, 0.5]}
        self.assertEqual(validate_ui_layout(self.data), original)
        self.write()
        plan, options = plan_ui_layout(["vertex_nudge", "mesh_bounds"], root=self.root, include_options=True)
        self.assertEqual(options["section_styles"][0], {"layout": "row", "boxed": False, "visible_in": "always"})
        self.assertEqual(options["nudge_offset"]["default"], (0.125, -0.25, 0.5))
        self.assertEqual(options["nudge_offset"]["min"], -10)

    def test_bad_parameter_values_and_operator_injection_rejected(self):
        for value in ([0, 0, 0], [True, 0, 1], [float("nan"), 0, 1], [11, 0, 1], [1, 2]):
            with self.subTest(value=value):
                self.data["sections"][1]["controls"][1]["parameters"] = {"offset": value}
                with self.assertRaises(ValueError):
                    validate_ui_layout(self.data)
        self.data["sections"][1]["controls"][1]["parameters"] = {"execute": "unknown.py"}
        with self.assertRaises(ValueError):
            validate_ui_layout(self.data)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        path = self.root / "catalog/ui_layouts.json"
        path.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "catalog/ui_layouts.json", path)
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))

    def write(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

    def test_whole_catalog_is_complete_and_ordered(self):
        actual = plan_ui_layout(
            ["edit_selection", "object_selection", "mesh_bounds",
             "modifier_summary", "vertex_nudge"], root=self.root)
        self.assertEqual([title for title, _ in actual], ["Inspection", "Edit Mode"])
        self.assertEqual(
            [feature for _, controls in actual for feature, _ in controls],
            ["object_selection", "mesh_bounds", "modifier_summary",
             "edit_selection", "vertex_nudge"])

    def test_subset_hides_empty_sections(self):
        self.assertEqual(
            plan_ui_layout(["vertex_nudge"], root=self.root),
            (("Edit Mode", (("vertex_nudge", "Nudge Vertices"),)),))

    def test_selected_feature_order_cannot_reorder_panel(self):
        a = plan_ui_layout(["object_selection", "edit_selection"], root=self.root)
        b = plan_ui_layout(["edit_selection", "object_selection"], root=self.root)
        self.assertEqual(a, b)

    def test_missing_or_repeated_feature_rejected(self):
        self.data["sections"][1]["controls"].pop()
        with self.assertRaisesRegex(ValueError, "exactly all"):
            validate_ui_layout(self.data)
        self.data = json.loads((ROOT / "catalog/ui_layouts.json").read_text())
        self.data["sections"][1]["controls"][0]["feature_id"] = "object_selection"
        with self.assertRaisesRegex(ValueError, "repeated"):
            validate_ui_layout(self.data)

    def test_unknown_feature_and_arbitrary_operator_key_rejected(self):
        self.data["sections"][0]["controls"][0]["feature_id"] = "not_in_allowlist"
        with self.assertRaises(ValueError):
            validate_ui_layout(self.data)
        self.data = json.loads((ROOT / "catalog/ui_layouts.json").read_text())
        self.data["sections"][0]["controls"][0]["python"] = "bpy.ops.wm.open_mainfile()"
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            validate_ui_layout(self.data)

    def test_invalid_labels_and_ids_rejected(self):
        for label in ("", "hello\nworld", "\u202e", "x" * 73, 1):
            with self.subTest(label=label):
                doc = copy.deepcopy(self.data)
                doc["sections"][0]["controls"][0]["label"] = label
                with self.assertRaises(ValueError):
                    validate_ui_layout(doc)
        self.data["sections"][0]["id"] = "../private"
        with self.assertRaises(ValueError):
            validate_ui_layout(self.data)

    def test_duplicate_json_keys_refused(self):
        self.path.write_text(self.path.read_text()[:-2] + ', "sections": []}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate key"):
            plan_ui_layout(["mesh_bounds"], root=self.root)

    def test_unknown_selection_rejected(self):
        for value in ([], ["mesh_bounds", "mesh_bounds"], ["external"], "mesh_bounds", [None]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    plan_ui_layout(value, root=self.root)

    def test_unexpected_schema_and_disallowed_flags_rejected(self):
        for key, value in (("schema_version", True), ("preview_only", False),
                           ("kind", "arbitrary_python")):
            doc = copy.deepcopy(self.data)
            doc[key] = value
            with self.assertRaises(ValueError):
                validate_ui_layout(doc)

    def test_external_symlink_and_missing_source_rejected(self):
        outside = self.root / "outside.json"
        self.path.rename(outside)
        try:
            self.path.symlink_to(outside)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaisesRegex(ValueError, "unsafe trusted"):
            plan_ui_layout(["mesh_bounds"], root=self.root)


if __name__ == "__main__":
    unittest.main()
