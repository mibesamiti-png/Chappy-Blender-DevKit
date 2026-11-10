"""Review-only repair-plan regression tests: no inferred exact source identifiers."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.glb_diagnose import diagnose_comparison
from cbdk.glb_repair_plan import (
    RepairPlanError, build_repair_plan, plan_from_comparison, write_repair_plan,
)


def make_comparison(differences=None):
    rows = differences or []
    errors = sum(row.get("severity") == "error" for row in rows)
    return {
        "schema_version": 1, "kind": "cbdk_glb_scene_comparison",
        "passed": errors == 0,
        "summary": {
            "errors": errors,
            "warnings": sum(row.get("severity") == "warning" for row in rows),
            "infos": sum(row.get("severity") == "info" for row in rows),
        },
        "differences": rows,
    }


def difference(code, target="Socket_L", **extra):
    metrics = {"reference_object": target, **extra}
    return {"code": code, "severity": "error", "metrics": metrics}


def plan_from_rows(rows):
    return build_repair_plan(diagnose_comparison(make_comparison(rows)))


class GLBRepairPlanTests(unittest.TestCase):
    def test_socket_profile_maps_to_possible_parameters_not_actual_properties(self):
        plan = plan_from_rows([
            difference("object_silhouette", "Socket_L", view="front",
                       iou=0.42, minimum=0.90)])
        item = plan["recommendations"][0]
        self.assertEqual(item["role_guess_from_object_name"], "socket")
        self.assertEqual(item["suspected_category"], "part_profile_boolean_or_cutout")
        self.assertIn("socket_opening_diameter", item["possible_parameter_families"])
        self.assertIn("clearance", item["possible_parameter_families"])
        self.assertIn("boolean_cutter", item["possible_parameter_families"])
        self.assertEqual(item["affected_views"], ["front"])
        self.assertEqual(item["worst_iou"], 0.42)
        self.assertTrue(item["requires_human_parameter_mapping"])
        self.assertTrue(item["role_guess_is_unverified"])

    def test_ball_dimensions_and_axis_direction(self):
        plan = plan_from_rows([
            difference("object_dimensions", "Ball",
                       reference=[2, 2, 2], candidate=[2.6, 2, 2],
                       relative_error=0.23, tolerance=0.05)])
        item = plan["recommendations"][0]
        self.assertIn("ball_diameter", item["possible_parameter_families"])
        self.assertIn("shaft_diameter", item["possible_parameter_families"])
        axis = item["observed_axis_difference"]
        self.assertEqual(axis["axis"], "X")
        self.assertEqual(axis["candidate_direction"], "larger_or_positive")
        self.assertEqual(axis["reference_observed"], 2)
        self.assertEqual(axis["candidate_observed"], 2.6)
        self.assertIsNone(axis["parameter_value_recommendation"])
        self.assertEqual(axis["unit"], "unknown_from_comparison")

    def test_center_offset_preserves_signed_observation(self):
        plan = plan_from_rows([
            difference("object_center", "Socket_R",
                       reference=[0, 5, 0], candidate=[0, 3, 0],
                       relative_error=0.2)])
        item = plan["recommendations"][0]
        self.assertEqual(item["observed_axis_difference"]["axis"], "Y")
        self.assertEqual(item["observed_axis_difference"]["candidate_direction"],
                         "smaller_or_negative")
        self.assertIn("joint_anchor", item["possible_parameter_families"])

    def test_hinge_name_influences_possible_families(self):
        plan = plan_from_rows([difference("object_dimensions", "Hinge_Axis")])
        item = plan["recommendations"][0]
        self.assertIn("hinge_axis_diameter", item["possible_parameter_families"])

    def test_generic_part_uses_safe_generic_families(self):
        plan = plan_from_rows([difference("object_dimensions", "RandomPart")])
        item = plan["recommendations"][0]
        self.assertIsNone(item["role_guess_from_object_name"])
        self.assertFalse(item["role_guess_is_unverified"])
        self.assertIn("outer_dimensions", item["possible_parameter_families"])
        self.assertNotIn("ball_diameter", item["possible_parameter_families"])

    def test_missing_part_prioritized_and_not_fabricated(self):
        plan = plan_from_rows([
            {"code": "missing_reference_object", "severity": "error",
             "metrics": {"object": "Socket_R", "volume_fraction": 0.2}},
            difference("object_center", "Ball"),
        ])
        item = plan["recommendations"][0]
        self.assertEqual(item["target"], "Socket_R")
        self.assertIn("generation_mode", item["possible_parameter_families"])
        self.assertEqual(item["observed_axis_difference"], None)

    def test_multiple_scene_views_grouped(self):
        plan = plan_from_rows([
            {"code": "scene_silhouette", "severity": "error",
             "metrics": {"view": view, "iou": score, "minimum": 0.9}}
            for view, score in (("front", 0.6), ("right", 0.3), ("top", 0.55))
        ])
        self.assertEqual(plan["recommendation_count"], 1)
        self.assertEqual(plan["recommendations"][0]["target"], "scene")
        self.assertEqual(plan["recommendations"][0]["worst_iou"], 0.3)
        self.assertEqual(plan["recommendations"][0]["affected_views"],
                         ["front", "right", "top"])

    def test_report_without_differences_has_no_parameter_edits(self):
        plan = build_repair_plan(diagnose_comparison(make_comparison()))
        self.assertEqual(plan["recommendation_count"], 0)
        self.assertFalse(plan["requires_review"])
        self.assertEqual(plan["next_actions"], [])
        self.assertFalse(plan["safety"]["applies_parameters"])
        self.assertFalse(plan["safety"]["edits_code"])
        self.assertFalse(plan["safety"]["auto_approves"])

    def test_unknown_codes_remain_review_work(self):
        plan = plan_from_rows([{"code": "new_metric", "severity": "warning", "metrics": {}}])
        self.assertTrue(plan["requires_review"])
        self.assertEqual(plan["unmapped_difference_codes"], ["new_metric"])
        self.assertEqual(plan["recommendation_count"], 0)
        self.assertGreater(len(plan["next_actions"]), 0)

    def test_ranked_recommendations_are_deterministic(self):
        rows = [difference("object_center", "Ball"),
                difference("object_silhouette", "Socket_L", view="front", iou=0.5),
                difference("missing_reference_object", "Socket_R")]
        first = plan_from_rows(rows)
        self.assertEqual(first, plan_from_rows(rows))
        self.assertEqual(first["recommendations"][0]["target"], "Socket_R")

    def test_unverified_roles_do_not_match_partial_words(self):
        plan = plan_from_rows([difference("object_silhouette", "FootballPart")])
        item = plan["recommendations"][0]
        self.assertIsNone(item["role_guess_from_object_name"])

    def test_bad_shape_diagnosis_is_rejected(self):
        with self.assertRaises(RepairPlanError):
            build_repair_plan({"kind": "wrong", "hypotheses": []})
        with self.assertRaises(RepairPlanError):
            build_repair_plan({"kind": "cbdk_glb_diagnosis", "hypotheses": []})

    def test_hypothesis_count_and_evidence_count_are_strict(self):
        diagnosis = diagnose_comparison(make_comparison([difference("object_center", "Ball")]))
        for field, value in (("hypothesis_count", True), ("hypothesis_count", 2)):
            other = copy.deepcopy(diagnosis)
            other[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RepairPlanError):
                build_repair_plan(other)
        other = copy.deepcopy(diagnosis)
        other["hypotheses"][0]["evidence_summary"]["evidence_count"] = True
        with self.assertRaises(RepairPlanError):
            build_repair_plan(other)

    def test_bad_priority_or_confidence_rejected(self):
        for field, bad in (("priority", -1), ("priority", True),
                           ("confidence", 2), ("confidence", "0.5")):
            diagnosis = diagnose_comparison(make_comparison([difference("object_center")]))
            diagnosis["hypotheses"][0][field] = bad
            with self.subTest(field=field), self.assertRaises(RepairPlanError):
                build_repair_plan(diagnosis)

    def test_unknown_category_is_manual_review_only(self):
        diagnosis = diagnose_comparison(make_comparison([difference("object_silhouette")]))
        diagnosis["hypotheses"][0]["category"] = "unknown_future_category"
        plan = build_repair_plan(diagnosis)
        self.assertEqual(plan["recommendations"][0]["possible_parameter_families"], [])
        self.assertIn("manually", plan["recommendations"][0]["inspect_checks"][0])

    def test_unsafe_object_names_are_rejected(self):
        diagnosis = diagnose_comparison(make_comparison([difference("object_center")]))
        for target in ("bad\nobject", "x" * 200, ""):
            other = copy.deepcopy(diagnosis)
            other["hypotheses"][0]["target"] = target
            with self.subTest(target=repr(target)), self.assertRaises(RepairPlanError):
                build_repair_plan(other)

    def test_missing_or_malformed_axis_data_does_not_invent_values(self):
        plan = plan_from_rows([difference("object_dimensions",
                                          reference=[2, 2, 2],
                                          candidate=[2, 2])])
        self.assertIsNone(plan["recommendations"][0]["observed_axis_difference"])

    def test_write_plan_rejects_approval_claim(self):
        plan = plan_from_rows([difference("object_center", "Ball")])
        plan["safety"]["auto_approves"] = True
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out.json"
            with self.assertRaises(RepairPlanError):
                write_repair_plan(plan, out)
            self.assertFalse(out.exists())

    def test_cli_generates_local_review_report_from_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compare.json"
            out = Path(directory) / "repair_plan.json"
            path.write_text(json.dumps(make_comparison([difference(
                "object_silhouette", "Socket_L", view="front", iou=0.4)])),
                encoding="utf-8")
            import contextlib
            import io
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                status = main(["glb-repair-plan", str(path), "--output", str(out)])
            self.assertEqual(status, 0)
            report = json.loads(out.read_text("utf-8"))
            self.assertEqual(report["kind"], "cbdk_glb_repair_plan")
            self.assertEqual(report["recommendation_count"], 1)
            self.assertIn("possible_parameter_families", buffer.getvalue())

    def test_consistent_output_and_no_sources_touched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inp, output = root / "comparison.json", root / "plan.json"
            data = make_comparison([difference("object_dimensions", "Ball",
                                               reference=[2, 2, 2], candidate=[2.3, 2, 2])])
            inp.write_text(json.dumps(data), encoding="utf-8")
            original = inp.read_bytes()
            report = plan_from_comparison(inp, output)
            self.assertEqual(report, json.loads(output.read_text("utf-8")))
            self.assertEqual(inp.read_bytes(), original)
            self.assertFalse((root / "addon.py").exists())
            self.assertFalse(report["safety"]["runs_untrusted_addons"])


if __name__ == "__main__":
    unittest.main()
