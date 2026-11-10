"""Untrusted comparison input and measurable GLB diagnostic review evidence."""
from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from cbdk.glb_diagnose import (
    DiagnosticError, diagnose_comparison, diagnose_comparison_file,
    write_diagnosis,
)


def comparison(differences, *, passed=False, with_counts=True):
    summary = {"errors": sum(d["severity"] == "error" for d in differences)}
    if with_counts:
        summary.update({
            "warnings": sum(d["severity"] == "warning" for d in differences),
            "infos": sum(d["severity"] == "info" for d in differences),
        })
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_scene_comparison",
        "passed": passed,
        "summary": summary,
        "differences": differences,
    }


def row(code="object_silhouette", severity="error", **metrics):
    return {"code": code, "severity": severity, "metrics": metrics}


class GLBDiagnoseEvidenceTests(unittest.TestCase):
    def test_silhouette_views_are_collapsed_and_worst_iou_retained(self):
        rows = [
            row("scene_silhouette", view="front", iou=0.81, minimum=0.90),
            row("scene_silhouette", view="right", iou=0.36, minimum=0.90),
            row("scene_silhouette", view="top", iou=0.72, minimum=0.90),
        ]
        result = diagnose_comparison(comparison(rows))
        self.assertEqual(result["hypothesis_count"], 1)
        item = result["hypotheses"][0]
        self.assertEqual(item["target"], "scene")
        self.assertEqual(item["category"], "assembly_shape_mismatch")
        self.assertEqual(item["evidence_summary"]["affected_views"],
                         ["front", "right", "top"])
        self.assertEqual(item["evidence_summary"]["worst_iou"], 0.36)
        self.assertEqual(item["evidence_summary"]["evidence_count"], 3)
        self.assertEqual(item["evidence_summary"]["error_count"], 3)

    def test_per_part_silhouette_keeps_separate_targets(self):
        rows = [
            row("object_silhouette", reference_object="Socket_L", view="front", iou=0.42),
            row("object_silhouette", reference_object="Socket_L", view="right", iou=0.65),
            row("object_silhouette", reference_object="Ball", view="front", iou=0.78),
        ]
        result = diagnose_comparison(comparison(rows))
        self.assertEqual(result["hypothesis_count"], 2)
        self.assertEqual(result["hypotheses"][0]["target"], "Socket_L")
        self.assertEqual(result["hypotheses"][0]["evidence_summary"]["worst_iou"], 0.42)
        self.assertEqual(result["hypotheses"][1]["target"], "Ball")

    def test_dimension_and_volume_differences_are_quantified(self):
        rows = [
            row("object_dimensions", reference_object="Socket_L",
                relative_error=0.31, tolerance=0.05),
            row("object_dimensions", reference_object="Socket_L",
                relative_error=0.12, tolerance=0.05, severity_note="check"),
            row("missing_reference_object", severity="warning",
                object="Socket_R", volume_fraction=0.004),
        ]
        result = diagnose_comparison(comparison(rows))
        dimensions = next(h for h in result["hypotheses"] if h["category"] == "part_size_parameter")
        missing = next(h for h in result["hypotheses"] if h["category"] == "missing_generation_branch_or_mode")
        self.assertEqual(dimensions["evidence_summary"]["max_relative_error"], 0.31)
        self.assertEqual(missing["evidence_summary"]["max_volume_fraction"], 0.004)
        self.assertEqual(result["evidence_summary"]["warnings"], 1)

    def test_missing_and_extra_part_priorities_remain_deterministic(self):
        rows = [
            row("object_center", reference_object="Ball"),
            row("missing_reference_object", object="Socket_R"),
            row("extra_candidate_object", object="ExtraCutter", severity="warning"),
        ]
        first = diagnose_comparison(comparison(rows))
        second = diagnose_comparison(comparison(rows))
        self.assertEqual(first, second)
        self.assertEqual(first["hypotheses"][0]["target"], "Socket_R")
        self.assertEqual(first["evidence_summary"]["total_differences"], 3)

    def test_pass_is_not_promoted_to_exact_geometry_proof(self):
        result = diagnose_comparison(comparison([], passed=True))
        self.assertFalse(result["needs_review"])
        self.assertTrue(result["comparison_passed"])
        self.assertEqual(result["recommended_next_step"], "no_comparison_differences_reported")
        self.assertTrue(any("32x32" in line for line in result["limitations"]))
        self.assertFalse(result["safety"]["auto_approves"])

    def test_unknown_code_warning_is_never_silently_successful(self):
        rows = [row("future_sdf_distance", severity="warning", value=0.5)]
        result = diagnose_comparison(comparison(rows, passed=True))
        self.assertTrue(result["comparison_passed"])
        self.assertTrue(result["needs_review"])
        self.assertEqual(result["unsupported_difference_codes"], ["future_sdf_distance"])
        self.assertEqual(result["hypothesis_count"], 0)
        self.assertEqual(result["recommended_next_step"], "review_unsupported_difference_codes")

    def test_info_difference_needs_review_not_automatic_geometry_fix(self):
        result = diagnose_comparison(
            comparison([row("object_topology", severity="info",
                            reference_object="Ball", changes=[])], passed=True))
        self.assertTrue(result["needs_review"])
        self.assertEqual(result["recommended_next_step"],
                         "review_warnings_and_informational_differences")

    def test_report_passed_must_be_a_boolean(self):
        for status in (None, "true", 1, 0, [], {}):
            with self.subTest(status=status), self.assertRaises(DiagnosticError):
                diagnose_comparison(dict(comparison([]), passed=status))

    def test_report_passed_must_agree_with_errors(self):
        for report in (
            comparison([row()], passed=True),
            comparison([], passed=False),
            dict(comparison([row()]), summary={"errors": 0}),
        ):
            with self.subTest(report=report), self.assertRaises(DiagnosticError):
                diagnose_comparison(report)

    def test_summary_counters_are_consistent_with_differences(self):
        for key, bad in (("errors", True), ("errors", -1), ("warnings", 2),
                         ("infos", "0")):
            sample = comparison([row("future", severity="warning")], passed=True)
            sample["summary"][key] = bad
            with self.subTest(key=key, value=bad), self.assertRaises(DiagnosticError):
                diagnose_comparison(sample)

    def test_invalid_severity_rejected_instead_of_dropped(self):
        for severity in ("ERROR", "critical", None, 5, [], {}):
            sample = comparison([])
            sample["differences"].append(row(severity=severity))
            with self.subTest(severity=severity), self.assertRaises(DiagnosticError):
                diagnose_comparison(sample)

    def test_bad_numeric_metrics_fail_closed(self):
        for metric, bad in (
            ("iou", -0.01), ("iou", 1.1), ("iou", float("nan")),
            ("minimum", "0.9"), ("volume_fraction", True),
            ("relative_error", -5), ("tolerance", float("inf")),
        ):
            with self.subTest(metric=metric, bad=bad), self.assertRaises(DiagnosticError):
                diagnose_comparison(comparison([row(**{metric: bad})]))

    def test_reject_nonjson_and_oversized_metric_objects(self):
        for metrics in ({"value": object()}, {"notes": "x" * 4200}):
            with self.subTest(metrics_type=type(next(iter(metrics.values()))).__name__):
                sample = comparison([row()])
                sample["differences"][0]["metrics"] = metrics
                with self.assertRaises(DiagnosticError):
                    diagnose_comparison(sample)

    def test_unknown_difference_code_remains_deduplicated(self):
        sample = comparison([row("future", severity="info"),
                             row("future", severity="warning")], passed=True)
        result = diagnose_comparison(sample)
        self.assertEqual(result["unsupported_difference_codes"], ["future"])
        self.assertEqual(result["evidence_summary"]["total_differences"], 2)

    def test_schema_bool_and_future_version_rejected(self):
        for version in (True, False, 2, "1"):
            with self.subTest(version=version), self.assertRaises(DiagnosticError):
                diagnose_comparison(dict(comparison([]), schema_version=version))

    def test_invalid_json_duplicate_keys_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compare.json"
            report = comparison([], passed=True)
            raw = json.dumps(report)
            path.write_text(raw[:-1] + ', "passed": true}', encoding="utf-8")
            with self.assertRaisesRegex(DiagnosticError, "Duplicate"):
                diagnose_comparison_file(path)

    def test_invalid_json_nan_and_oversize_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compare.json"
            path.write_text(json.dumps(comparison([], passed=True))[:-1] +
                            ', "unsafe": NaN}', encoding="utf-8")
            with self.assertRaises(DiagnosticError):
                diagnose_comparison_file(path)
            path.write_text("x" * (8 * 1024 * 1024 + 1), encoding="utf-8")
            with self.assertRaisesRegex(DiagnosticError, "safe size limit"):
                diagnose_comparison_file(path)

    def test_output_has_only_review_evidence_not_automatic_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            inp = Path(directory) / "comparison.json"
            out = Path(directory) / "diagnosis.json"
            inp.write_text(json.dumps(comparison([
                row("object_silhouette", reference_object="Body",
                    view="front", iou=0.45)], passed=False)), encoding="utf-8")
            result = write_diagnosis(inp, out)
            self.assertEqual(json.loads(out.read_text("utf-8")), result)
            self.assertFalse(result["safety"]["edits_code"])
            self.assertFalse(result["safety"]["auto_merges"])
            self.assertEqual(result["hypotheses"][0]["evidence_summary"]["worst_iou"], 0.45)

    def test_original_comparison_data_is_not_mutated(self):
        source = comparison([
            row("object_silhouette", reference_object="Part",
                iou=0.2, view="front")])
        original = copy.deepcopy(source)
        diagnose_comparison(source)
        self.assertEqual(source, original)


if __name__ == "__main__":
    unittest.main()
