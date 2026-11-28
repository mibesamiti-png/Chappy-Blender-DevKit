"""Disambiguate AST same-class self references without claiming runtime binding."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbdk.glb_property_map import map_repair_plan_properties
from cbdk.glb_property_usage import trace_property_references


def plan(*names):
    return {
        "schema_version": 1, "kind": "cbdk_glb_repair_plan",
        "status": "review_only",
        "recommendation_count": 1,
        "recommendations": [{
            "target": "Ball", "suspected_category": "part_size_parameter",
            "requires_human_parameter_mapping": True,
            "possible_parameter_families": list(names),
        }],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
        "unmapped_difference_codes": [],
    }


class GLBPropertyBindingHintTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def source(self, name, text):
        file = self.root / name
        file.write_text(text, encoding="utf-8")
        return file

    def match(self, sources):
        report = map_repair_plan_properties(plan("ball_diameter"), sources)
        self.assertEqual(report["recommendation_count"], 1)
        self.assertTrue(report["recommendations"][0]["has_declared_name_match"])
        item = report["recommendations"][0]["exact_name_matches"][0]
        return report, item["same_class_reference_review"], item["possible_code_references"]

    def test_same_class_self_read_is_a_hint_not_a_verified_binding(self):
        source = self.source("private.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "    def inspect(self):\n"
            "        return self.ball_diameter\n")
        report, hint, refs = self.match([source])
        self.assertEqual(hint["classification"],
                         "syntactic_same_source_class_self_reference_found")
        self.assertEqual(hint["possible_same_source_class_self_count"], 1)
        self.assertEqual(hint["possible_access_counts"]["read"], 1)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 0)
        self.assertFalse(hint["actual_receiver_binding_verified"])
        self.assertFalse(hint["registered_in_blender_verified"])
        self.assertFalse(hint["geometry_effect_verified"])
        self.assertTrue(hint["requires_manual_review"])
        self.assertFalse(report["recommendations"][0]["validated_geometry_effect"])
        self.assertFalse(refs["receiver_binding_verified"])

    def test_other_receiver_in_same_method_remains_unresolved(self):
        src = self.source("local.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "    def check(self, other):\n"
            "        return other.ball_diameter\n")
        _, hint, refs = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 0)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 1)
        self.assertEqual(hint["classification"],
                         "no_same_source_class_self_reference_found")
        self.assertEqual(refs["examples"][0]["receiver_kind"], "unverified_variable")

    def test_other_class_self_is_not_same_declaration_class(self):
        src = self.source("local.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "class Unrelated:\n"
            "    def inspect(self):\n"
            "        return self.ball_diameter\n")
        _, hint, _ = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 0)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 1)

    def test_same_class_name_in_different_file_never_cross_links(self):
        declared = self.source("a_private.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n")
        unrelated = self.source("b_private.py",
            "class Settings:\n"
            "    def inspect(self):\n        return self.ball_diameter\n")
        _, hint, refs = self.match([declared, unrelated])
        self.assertEqual(hint["possible_same_source_class_self_count"], 0)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 1)
        self.assertEqual(refs["syntactic_self_scopes"][0]["source_label"], "source_2.py")

    def test_class_and_source_match_with_cross_class_reference(self):
        src = self.source("single.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "    def read(self):\n        return self.ball_diameter\n"
            "class Other:\n"
            "    def read(self):\n        return self.ball_diameter\n")
        _, hint, refs = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 1)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 1)
        self.assertEqual(len(refs["syntactic_self_scopes"]), 2)

    def test_write_and_augassign_and_delete_separate_counts(self):
        src = self.source("actions.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty()\n"
            "    def run(self):\n"
            "        self.ball_diameter = 2\n"
            "        self.ball_diameter += 1\n"
            "        del self.ball_diameter\n")
        _, hint, _ = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 3)
        self.assertEqual(hint["possible_access_counts"],
                         {"read": 0, "write": 1, "delete": 1, "read_write": 1})

    def test_global_self_name_outside_class_not_associated(self):
        src = self.source("local.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "def foo(self):\n    return self.ball_diameter\n")
        _, hint, refs = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 0)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 1)
        self.assertEqual(refs["syntactic_self_scopes"], [])

    def test_capped_examples_do_not_corrupt_total_scope_count(self):
        lines = ("        print(self.ball_diameter)\n" * 25)
        src = self.source("many.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def inspect(self):\n" + lines)
        _, hint, refs = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 25)
        self.assertEqual(refs["possible_reference_count"], 25)
        self.assertTrue(refs["examples_truncated"])
        self.assertEqual(len(refs["examples"]), 16)

    def test_self_scope_count_is_deterministic_across_methods(self):
        src = self.source("complex.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def one(self):\n        return self.ball_diameter\n"
            "    def two(self):\n        return self.ball_diameter + self.ball_diameter\n")
        first = map_repair_plan_properties(plan("ball_diameter"), [src])
        self.assertEqual(first, map_repair_plan_properties(plan("ball_diameter"), [src]))
        hint = first["recommendations"][0]["exact_name_matches"][0]["same_class_reference_review"]
        self.assertEqual(hint["possible_same_source_class_self_count"], 3)

    def test_dynamic_getattr_is_not_invented_as_direct_attribute(self):
        src = self.source("dynamic.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n"
            "    def inspect(self):\n        return getattr(self, 'ball_diameter')\n")
        _, hint, refs = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 0)
        self.assertEqual(refs["possible_reference_count"], 0)

    def test_no_exec_or_private_literals_or_full_paths_in_report(self):
        marker = self.root / "NEVER_CREATED"
        private = "SECRET_ANALYSIS_VALUE_NOT_FOR_REPORT"
        src = self.source("sensitive.py",
            "from bpy.props import FloatProperty\n"
            f"open({str(marker)!r}, 'w').write('BAD')\n"
            "class Settings:\n"
            f"    ball_diameter: FloatProperty(description={private!r})\n"
            "    def inspect(self):\n"
            f"        print({private!r})\n"
            "        return self.ball_diameter\n")
        report = map_repair_plan_properties(plan("ball_diameter"), [src])
        output = json.dumps(report)
        self.assertFalse(marker.exists())
        self.assertNotIn(private, output)
        self.assertNotIn(str(self.root), output)
        self.assertNotIn("sensitive.py", output)
        self.assertIn("source_1.py", output)
        self.assertFalse(report["safety"]["source_executed"])

    def test_same_class_reference_still_not_blender_registration_proof(self):
        src = self.source("unregistered.py",
            "from bpy.props import FloatProperty\n"
            "class NotRegistered:\n    ball_diameter: FloatProperty()\n"
            "    def fake(self):\n        return self.ball_diameter\n")
        result, hint, _ = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 1)
        self.assertFalse(hint["registered_in_blender_verified"])
        self.assertFalse(result["recommendations"][0]["validated_geometry_effect"])

    def test_empty_references_returns_zero_counts(self):
        src = self.source("declaration.py",
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty()\n")
        _, hint, refs = self.match([src])
        self.assertEqual(hint["possible_same_source_class_self_count"], 0)
        self.assertEqual(hint["other_or_unresolved_attribute_reference_count"], 0)
        self.assertEqual(refs["syntactic_self_scopes"], [])

    def test_visitor_self_scope_reports_no_runtime_proof(self):
        src = self.source("usage.py",
            "class Settings:\n"
            "    def check(self):\n"
            "        return self.ball_diameter\n")
        result = trace_property_references([src], {"ball_diameter"})
        scope = result["ball_diameter"]["syntactic_self_scopes"][0]
        self.assertEqual(scope["source_label"], "source_1.py")
        self.assertEqual(scope["class_name"], "Settings")
        self.assertEqual(scope["access_counts"]["read"], 1)
        self.assertFalse(scope["actual_property_binding_verified"])


if __name__ == "__main__":
    unittest.main()
