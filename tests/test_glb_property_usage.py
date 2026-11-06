"""Static property usage tracing: potential references, never a geometry proof."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cbdk.glb_property_map import map_repair_plan_properties
from cbdk.glb_property_usage import (
    MAX_EXAMPLES_PER_PROPERTY, PropertyUsageError, trace_property_references,
)


def plan():
    return {
        "kind": "cbdk_glb_repair_plan", "status": "review_only",
        "schema_version": 1, "recommendation_count": 1,
        "recommendations": [{
            "target": "Ball", "suspected_category": "part_size_parameter",
            "requires_human_parameter_mapping": True,
            "possible_parameter_families": ["ball_diameter", "shaft_diameter"],
        }],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
        "unmapped_difference_codes": [],
    }


class GLBPropertyUsageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def source(self, content, name="input.py"):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def trace(self, content, names=None):
        return trace_property_references([self.source(content)],
                                         names if names is not None else {"ball_diameter"})

    def test_direct_reads_and_function_scope(self):
        output = self.trace(
            "class Settings:\n"
            "    def inspect(self):\n"
            "        return self.ball_diameter + self.ball_diameter\n")
        data = output["ball_diameter"]
        self.assertEqual(data["possible_reference_count"], 2)
        self.assertEqual(data["access_counts"]["read"], 2)
        self.assertEqual(data["examples"][0]["class_name"], "Settings")
        self.assertEqual(data["examples"][0]["function_name"], "inspect")
        self.assertEqual(data["examples"][0]["source_label"], "source_1.py")
        self.assertEqual(data["examples"][0]["receiver_kind"], "self")
        self.assertEqual(data["examples"][0]["line"], 3)
        self.assertFalse(data["receiver_binding_verified"])

    def test_simple_assignment_write(self):
        out = self.trace("def edit(x):\n    x.ball_diameter = 3\n")
        row = out["ball_diameter"]
        self.assertEqual(row["access_counts"]["write"], 1)
        self.assertEqual(row["access_counts"]["read"], 0)

    def test_augassign_read_write(self):
        out = self.trace("def edit(self):\n    self.ball_diameter += 2\n")
        self.assertEqual(out["ball_diameter"]["access_counts"]["read_write"], 1)
        self.assertEqual(out["ball_diameter"]["possible_reference_count"], 1)

    def test_delete(self):
        out = self.trace("def edit(self):\n    del self.ball_diameter\n")
        self.assertEqual(out["ball_diameter"]["access_counts"]["delete"], 1)

    def test_annassign_attribute_write(self):
        out = self.trace("def edit(self):\n    self.ball_diameter: float = 2\n")
        self.assertEqual(out["ball_diameter"]["access_counts"]["write"], 1)

    def test_context_receiver_is_only_heuristic(self):
        out = self.trace(
            "def draw(context):\n    print(context.scene.ball_diameter)\n")
        site = out["ball_diameter"]["examples"][0]
        self.assertEqual(site["receiver_kind"], "context_attribute")
        self.assertEqual(site["association_with_declared_property"], "not_verified")
        self.assertEqual(site["geometry_effect"], "not_verified")

    def test_unrelated_variable_with_same_attribute_is_not_verified(self):
        out = self.trace(
            "def external(unrelated):\n    return unrelated.ball_diameter\n")
        site = out["ball_diameter"]["examples"][0]
        self.assertEqual(site["receiver_kind"], "unverified_variable")
        self.assertFalse(out["ball_diameter"]["runtime_effect_verified"])

    def test_nested_expression_does_not_expose_receiver_expression(self):
        token = "PRIVATE_OBJECT_KEY"
        out = self.trace(
            "def f(obj):\n"
            "    return getattr(obj, 'PRIVATE_OBJECT_KEY').ball_diameter\n")
        encoded = json.dumps(out)
        self.assertNotIn(token, encoded)
        self.assertEqual(out["ball_diameter"]["examples"][0]["receiver_kind"],
                         "unverified_expression")

    def test_dynamic_getattr_not_assumed_a_direct_reference(self):
        out = self.trace("def f(obj):\n    return getattr(obj, 'ball_diameter')\n")
        self.assertEqual(out["ball_diameter"]["possible_reference_count"], 0)

    def test_no_match_in_string_comments_and_annotation(self):
        out = self.trace(
            "# self.ball_diameter\n"
            "MESSAGE = 'ball_diameter'\n"
            "def no_usage():\n"
            "    return 'ball_diameter'\n")
        self.assertEqual(out["ball_diameter"]["possible_reference_count"], 0)

    def test_class_level_non_function_is_not_claimed_runtime_usage(self):
        out = self.trace("class C:\n    thing = other.ball_diameter\n")
        self.assertEqual(out["ball_diameter"]["possible_reference_count"], 0)

    def test_async_and_nested_function_provenance(self):
        out = self.trace(
            "class A:\n"
            "    async def perform(self):\n"
            "        def helper():\n"
            "            return self.ball_diameter\n"
            "        return helper()\n")
        site = out["ball_diameter"]["examples"][0]
        self.assertEqual(site["class_name"], "A")
        self.assertEqual(site["function_name"], "perform.helper")

    def test_lambda_is_labeled_but_not_executed(self):
        out = self.trace(
            "def make(self):\n    return lambda: self.ball_diameter\n")
        self.assertEqual(out["ball_diameter"]["examples"][0]["function_name"],
                         "make.<lambda>")

    def test_unrecognized_property_has_no_evidence(self):
        out = self.trace("def f(self):\n    return self.ball_diameter\n",
                         {"shaft_diameter"})
        self.assertEqual(out["shaft_diameter"]["possible_reference_count"], 0)

    def test_multiple_sources_keep_anonymous_identifiers(self):
        a = self.source("def f(obj):\n    return obj.ball_diameter\n", "secret_a.py")
        b = self.source("def f(obj):\n    return obj.ball_diameter\n", "secret_b.py")
        out = trace_property_references([a, b], {"ball_diameter"})
        self.assertEqual(out["ball_diameter"]["possible_reference_count"], 2)
        self.assertEqual([x["source_label"] for x in out["ball_diameter"]["examples"]],
                         ["source_1.py", "source_2.py"])
        self.assertNotIn(str(self.root), json.dumps(out))
        self.assertNotIn("secret_a.py", json.dumps(out))

    def test_example_list_is_capped_but_total_is_correct(self):
        src = "def foo(self):\n" + "    print(self.ball_diameter)\n" * 19
        output = self.trace(src)["ball_diameter"]
        self.assertEqual(output["possible_reference_count"], 19)
        self.assertEqual(len(output["examples"]), MAX_EXAMPLES_PER_PROPERTY)
        self.assertTrue(output["examples_truncated"])

    def test_excess_references_are_rejected_not_silently_truncated(self):
        src = "def foo(self):\n" + "    print(self.ball_diameter)\n" * 4100
        with self.assertRaises(PropertyUsageError):
            self.trace(src)

    def test_invalid_source_and_symlink_refused(self):
        source = self.source("def foo(self):\n    return self.ball_diameter\n")
        link = self.root / "alias.py"
        try:
            link.symlink_to(source)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(PropertyUsageError):
            trace_property_references([link], {"ball_diameter"})

    def test_no_code_execution_even_with_destructive_toplevel(self):
        marker = self.root / "NEVER_WRITE.txt"
        src = ("from pathlib import Path\n"
               f"Path({str(marker)!r}).write_text('BAD')\n"
               "raise RuntimeError('do not run')\n"
               "def f(self):\n    return self.ball_diameter\n")
        out = self.trace(src)
        self.assertEqual(out["ball_diameter"]["possible_reference_count"], 1)
        self.assertFalse(marker.exists())

    def test_empty_candidate_set_safe(self):
        out = self.trace("def f(self):\n    return self.ball_diameter\n", set())
        self.assertEqual(out, {})

    def test_integration_with_static_property_declarations(self):
        src = self.source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty(default=3.0)\n"
            "    def draw(self, context):\n"
            "        return self.ball_diameter\n"
            "    def execute(self):\n"
            "        self.ball_diameter = 4\n")
        report = map_repair_plan_properties(plan(), [src])
        self.assertEqual(report["static_property_declarations_found"], 1)
        self.assertEqual(report["static_possible_attribute_references_found"], 2)
        matches = report["recommendations"][0]["exact_name_matches"]
        self.assertEqual(len(matches), 1)
        refs = matches[0]["possible_code_references"]
        self.assertEqual(refs["access_counts"]["read"], 1)
        self.assertEqual(refs["access_counts"]["write"], 1)
        self.assertFalse(report["recommendations"][0]["validated_geometry_effect"])
        self.assertFalse(refs["runtime_effect_verified"])

    def test_integration_no_matching_property_does_not_promote_usage(self):
        src = self.source(
            "def f(other):\n    return other.ball_diameter\n")
        report = map_repair_plan_properties(plan(), [src])
        self.assertEqual(report["static_property_declarations_found"], 0)
        self.assertEqual(report["static_possible_attribute_references_found"], 0)
        self.assertFalse(report["recommendations"][0]["has_declared_name_match"])

    def test_property_usage_report_has_no_source_literals(self):
        secret = "SENSITIVE_SOURCE_VALUE_NOT_PUBLIC"
        src = self.source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            f"    ball_diameter: FloatProperty(default=2.0, description={secret!r})\n"
            "    def f(self):\n"
            f"        print({secret!r}, self.ball_diameter)\n")
        output = json.dumps(map_repair_plan_properties(plan(), [src]))
        self.assertNotIn(secret, output)
        self.assertNotIn(str(self.root), output)


if __name__ == "__main__":
    unittest.main()
