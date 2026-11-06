"""Ensure the trusted synthetic fixture has a credible AST-to-runtime path.

These unit tests only PARSE source. Blender executes this repository-owned
fixture exclusively in the separate Blender CI matrix.
"""
from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from cbdk.glb_property_map import map_repair_plan_properties

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "cbdk_parameter_experiment.py"
SMOKE = ROOT / "scripts" / "blender_parameter_experiment_smoke.py"


def _plan():
    return {
        "schema_version": 1, "kind": "cbdk_glb_repair_plan",
        "status": "review_only",
        "recommendation_count": 1,
        "recommendations": [{
            "target": "CBDK_Param_Sphere",
            "suspected_category": "part_size_parameter",
            "requires_human_parameter_mapping": True,
            "possible_parameter_families": ["sphere_radius", "bevel_width"],
        }],
        "unmapped_difference_codes": [],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
    }


class TrustedParameterExperimentASTTests(unittest.TestCase):
    def setUp(self):
        self.report = map_repair_plan_properties(_plan(), [FIXTURE])
        matches = self.report["recommendations"][0]["exact_name_matches"]
        self.mapped = {hit["candidate_family"]: hit for hit in matches}

    def test_fixture_has_two_actual_bpy_float_properties(self):
        self.assertEqual(set(self.mapped), {"sphere_radius", "bevel_width"})
        self.assertEqual(self.report["static_property_declarations_found"], 2)
        for hit in self.mapped.values():
            self.assertEqual(hit["declarations"][0]["property_constructor"], "FloatProperty")

    def test_sphere_radius_flows_to_mesh_primitive(self):
        evidence = self.mapped["sphere_radius"]["possible_geometry_dataflow"]
        self.assertGreater(evidence["possible_path_count"], 0)
        self.assertTrue(any(row["recognized_api"] == "bpy.ops.mesh.primitive_uv_sphere_add"
                            for row in evidence["examples"]))
        self.assertFalse(evidence["geometry_effect_verified"])

    def test_bevel_width_flows_to_modifier_like_assignment(self):
        evidence = self.mapped["bevel_width"]["possible_geometry_dataflow"]
        self.assertGreater(evidence["possible_path_count"], 0)
        self.assertTrue(any(row["recognized_api"] == "modifier.width"
                            for row in evidence["examples"]))
        self.assertFalse(evidence["receiver_binding_verified"])

    def test_both_settings_have_same_class_self_evidence(self):
        for hit in self.mapped.values():
            hint = hit["same_class_reference_review"]
            self.assertEqual(hint["classification"],
                             "syntactic_same_source_class_self_reference_found")
            self.assertGreater(hint["possible_same_source_class_self_count"], 0)
            self.assertFalse(hint["actual_receiver_binding_verified"])

    def test_no_code_or_paths_are_copied_into_static_report(self):
        encoded = json.dumps(self.report)
        self.assertNotIn(str(ROOT), encoded)
        self.assertNotIn("cbdk_parameter_experiment.py", encoded)
        self.assertNotIn("default=0.75", encoded)
        self.assertFalse(self.report["safety"]["source_executed"])
        self.assertFalse(self.report["safety"]["auto_approves"])

    def test_runtime_fixture_variants_are_explicit_and_separated(self):
        tree = ast.parse(SMOKE.read_text(encoding="utf-8"))
        variants = next(
            node.value for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "VARIANTS"
                    for target in node.targets)
        )
        values = ast.literal_eval(variants)
        self.assertEqual([row[0] for row in values],
                         ["baseline", "sphere_radius_changed", "bevel_width_changed"])
        self.assertEqual(values[0][2], values[1][2])
        self.assertEqual(values[0][1], values[2][1])
        self.assertNotEqual(values[0][1], values[1][1])
        self.assertNotEqual(values[0][2], values[2][2])


if __name__ == "__main__":
    unittest.main()
