"""Regression tests for AST-only parameter inventory and review-plan linking."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.glb_property_map import (
    MAX_SOURCE_BYTES, PropertyMappingError, _inventory,
    map_repair_plan_properties, map_properties_from_file, write_local_mapping,
)


def review_plan(candidates=("ball_diameter", "socket_opening_diameter", "shaft_diameter")):
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_repair_plan",
        "status": "review_only",
        "recommendation_count": 1,
        "recommendations": [{
            "target": "Ball",
            "suspected_category": "part_size_parameter",
            "requires_human_parameter_mapping": True,
            "possible_parameter_families": list(candidates),
        }],
        "unmapped_difference_codes": [],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
    }


class GLBPropertyMapTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def make_source(self, content, name="private_input.py"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_ast_annotated_float_property_matches_exact_only(self):
        source = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty(name='Ball Diameter', default=2.0)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["source_files_scanned"], 1)
        self.assertEqual(out["static_property_declarations_found"], 1)
        row = out["recommendations"][0]
        self.assertTrue(row["has_declared_name_match"])
        match = row["exact_name_matches"][0]
        self.assertEqual(match["candidate_family"], "ball_diameter")
        self.assertEqual(match["match"], "exact_declaration_name_only")
        self.assertEqual(match["declarations"][0]["class_name"], "Settings")
        self.assertEqual(match["declarations"][0]["property_constructor"], "FloatProperty")
        self.assertEqual(match["declarations"][0]["line"], 3)
        self.assertEqual(row["unmatched_parameter_families"],
                         ["socket_opening_diameter", "shaft_diameter"])
        self.assertFalse(row["validated_geometry_effect"])
        self.assertFalse(out["safety"]["source_executed"])

    def test_bpy_props_dot_constructor(self):
        source = self.make_source(
            "import bpy\nclass Props:\n"
            "    ball_diameter = bpy.props.FloatProperty(default=2.0)\n")
        out = map_repair_plan_properties(review_plan(("ball_diameter",)), [source])
        self.assertEqual(out["static_property_declarations_found"], 1)
        self.assertEqual(out["recommendations"][0]["exact_name_matches"][0]
                         ["declarations"][0]["property_constructor"], "FloatProperty")

    def test_bpy_alias_and_from_bpy_props_alias(self):
        source = self.make_source(
            "import bpy as blender\nfrom bpy import props as property_api\n"
            "class Config:\n"
            "    ball_diameter: blender.props.FloatProperty(default=2)\n"
            "    shaft_diameter: property_api.FloatProperty(default=3)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 2)
        self.assertEqual(len(out["recommendations"][0]["exact_name_matches"]), 2)

    def test_from_bpy_props_named_alias(self):
        source = self.make_source(
            "from bpy.props import FloatProperty as FP\n"
            "class Config:\n    ball_diameter: FP(default=2)\n")
        out = map_repair_plan_properties(review_plan(("ball_diameter",)), [source])
        self.assertEqual(out["static_property_declarations_found"], 1)
        self.assertEqual(out["recommendations"][0]["exact_name_matches"][0]
                         ["declarations"][0]["property_constructor"], "FloatProperty")

    def test_plain_unimported_property_function_is_not_trusted(self):
        source = self.make_source(
            "def FloatProperty(**kwargs):\n    return None\n"
            "class Settings:\n    ball_diameter: FloatProperty(default=3)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 0)

    def test_function_locals_and_instance_fields_are_not_class_declarations(self):
        source = self.make_source(
            "import bpy\n"
            "def create():\n    ball_diameter = bpy.props.FloatProperty(default=5)\n"
            "class Settings:\n"
            "    def __init__(self):\n"
            "        self.ball_diameter = bpy.props.FloatProperty(default=8)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 0)

    def test_no_execution_of_malicious_top_level_code(self):
        marker = self.root / "should_never_exist.txt"
        source = self.make_source(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('BAD')\n"
            "raise RuntimeError('MUST NOT EXECUTE')\n"
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty(default=2)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 1)
        self.assertFalse(marker.exists())

    def test_private_source_content_or_paths_never_enter_report(self):
        sensitive = "PRIVATE_VALUE_DO_NOT_LEAK"
        src = self.make_source(
            "from bpy.props import StringProperty\n"
            "class Secrets:\n"
            "    ball_diameter: StringProperty(default='PRIVATE_VALUE_DO_NOT_LEAK')\n",
            "private_project/secret_journal.py")
        report = map_repair_plan_properties(review_plan(("ball_diameter",)), [src])
        encoded = json.dumps(report)
        self.assertNotIn(sensitive, encoded)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("secret_journal.py", encoded)
        self.assertIn("source_1.py", encoded)

    def test_renamed_properties_remain_unmatched_not_verified(self):
        source = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Props:\n    diameter_ball: FloatProperty(default=3)\n")
        output = map_repair_plan_properties(review_plan(("ball_diameter",)), [source])
        self.assertFalse(output["recommendations"][0]["has_declared_name_match"])
        self.assertEqual(output["recommendations"][0]["exact_name_matches"], [])

    def test_multifile_and_duplicate_declaration_are_reported_as_ambiguous(self):
        a = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class A:\n    ball_diameter: FloatProperty()\n", "a.py")
        b = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class B:\n    ball_diameter: FloatProperty()\n", "b.py")
        result = map_repair_plan_properties(review_plan(("ball_diameter",)), [a, b])
        declarations = result["recommendations"][0]["exact_name_matches"][0]["declarations"]
        self.assertEqual(len(declarations), 2)
        self.assertEqual({x["source_label"] for x in declarations}, {"source_1.py", "source_2.py"})
        self.assertTrue(all(x["registered_in_blender"] == "not_checked" for x in declarations))

    def test_other_property_types_recognized(self):
        source = self.make_source(
            "from bpy.props import EnumProperty, BoolProperty, IntVectorProperty\n"
            "class Options:\n"
            "    split_mode: EnumProperty(items=[])\n"
            "    is_visible: BoolProperty(default=True)\n"
            "    segment_count: IntVectorProperty(size=3)\n")
        result = map_repair_plan_properties(review_plan(("split_mode", "segment_count")), [source])
        self.assertEqual(result["static_property_declarations_found"], 3)
        self.assertEqual(len(result["recommendations"][0]["exact_name_matches"]), 2)

    def test_static_parse_syntax_error_refused(self):
        source = self.make_source("not valid Python code !!!")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [source])

    def test_source_file_size_and_extension_checked(self):
        large = self.make_source("x" * (MAX_SOURCE_BYTES + 2))
        with self.assertRaisesRegex(PropertyMappingError, "size"):
            map_repair_plan_properties(review_plan(), [large])
        text_file = self.make_source("class Settings: pass\n", "data.txt")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [text_file])

    def test_symlinked_source_is_rejected(self):
        source = self.make_source("from bpy.props import FloatProperty\n")
        link = self.root / "link.py"
        try:
            link.symlink_to(source)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [link])

    def test_plan_inconsistent_count_rejected(self):
        plan = review_plan()
        plan["recommendation_count"] = 2
        source = self.make_source("class Empty: pass")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(plan, [source])

    def test_approval_flags_cannot_be_forged(self):
        source = self.make_source("class Empty: pass")
        for key in ("edits_code", "applies_parameters", "auto_approves",
                    "private_geometry_required", "runs_untrusted_addons", "auto_merges"):
            plan = review_plan()
            plan["safety"][key] = True
            with self.subTest(key=key), self.assertRaises(PropertyMappingError):
                map_repair_plan_properties(plan, [source])

    def test_candidate_identifier_validation(self):
        source = self.make_source("class Empty: pass")
        for candidate in ("a.b", "../secret", "bad\nname", "x" * 130, 123, None):
            with self.subTest(candidate=repr(candidate)):
                with self.assertRaises(PropertyMappingError):
                    map_repair_plan_properties(review_plan((candidate,)), [source])

    def test_empty_sources_and_limits_rejected(self):
        source = self.make_source("class Empty: pass")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [])
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [source] * 17)

    def test_duplicate_json_keys_refused(self):
        file = self.root / "plan.json"
        json_text = json.dumps(review_plan())
        file.write_text(json_text[:-1] + ', "status":"review_only"}', encoding="utf-8")
        source = self.make_source("class Empty: pass")
        with self.assertRaisesRegex(PropertyMappingError, "Duplicate"):
            map_properties_from_file(file, [source], root=self.root)

    def test_write_only_ignored_local_report_without_overwriting(self):
        src = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty(default=3)\n")
        plan = self.root / "plan.json"
        plan.write_text(json.dumps(review_plan()), encoding="utf-8")
        out = "reports/latest/property_map.json"
        report = map_properties_from_file(plan, [src], out, root=self.root)
        saved = self.root / out
        self.assertEqual(json.loads(saved.read_text("utf-8")), report)
        self.assertEqual(report["kind"], "cbdk_glb_property_mapping")
        self.assertEqual(report["recommendations"][0]["exact_name_matches"][0]
                         ["candidate_family"], "ball_diameter")
        with self.assertRaises(FileExistsError):
            map_properties_from_file(plan, [src], out, root=self.root)
        self.assertFalse((self.root / "addon_generated.py").exists())

    def test_output_absolute_and_traversal_rejected(self):
        result = {"kind": "cbdk_glb_property_mapping"}
        for dest in ("/tmp/mapping.json", "../mapping.json", "reports/latest/../../../escape.json",
                     "reports/ci/mapping.json", "dist/mapping.json"):
            with self.subTest(dest=dest), self.assertRaises(PropertyMappingError):
                write_local_mapping(result, dest, root=self.root)

    def test_output_symlink_escape_refused(self):
        external = self.root / "external"
        external.mkdir()
        rep = self.root / "reports"
        rep.mkdir()
        try:
            (rep / "latest").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PropertyMappingError):
            write_local_mapping({"kind": "cbdk_glb_property_mapping"},
                                "reports/latest/output.json", root=self.root)
        self.assertEqual(list(external.iterdir()), [])

    def test_no_matches_does_not_claim_a_fix(self):
        source = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    other_thing: FloatProperty()\n")
        report = map_repair_plan_properties(review_plan(("socket_opening_diameter",)), [source])
        self.assertEqual(report["recommendations"][0]["unmatched_parameter_families"],
                         ["socket_opening_diameter"])
        self.assertFalse(report["recommendations"][0]["validated_geometry_effect"])
        self.assertEqual(report["next_action"], "review_exact_declarations_and_actual_blender_registration")

    def test_cli_wiring_no_implicit_source_scan(self):
        with patch("cbdk.__main__.map_properties_from_file", return_value={
            "kind": "cbdk_glb_property_mapping", "source_files_scanned": 1
        }) as mapped:
            import contextlib
            import io
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["glb-map-properties", "reports/latest/repair_plan.json",
                               "--source", "input_sources_private/addon.py",
                               "--output", "reports/latest/map.json"])
        self.assertEqual(result, 0)
        mapped.assert_called_once_with("reports/latest/repair_plan.json",
                                       ["input_sources_private/addon.py"],
                                       "reports/latest/map.json")
        self.assertIn("cbdk_glb_property_mapping", output.getvalue())


if __name__ == "__main__":
    unittest.main()
