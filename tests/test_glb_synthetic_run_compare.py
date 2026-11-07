"""Same-condition comparison, source digests, privacy and legacy compatibility."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_synthetic_adaptive import build_adaptive_checkpoint
from cbdk.glb_synthetic_conditions import build_conditions, condition_source_digest, validate_conditions
from cbdk.glb_synthetic_run_compare import (
    compare_run_reviews, main, render_run_comparison, write_run_comparison,
)
from cbdk.glb_synthetic_run_review import build_run_review, render_run_review
from test_glb_synthetic_adaptive import review


def conditions(**updates):
    args = dict(source_sha256="a" * 64, reference_sha256="b" * 64,
                baseline_sha256="c" * 64, blender_version="4.5.15", scale=6.0,
                initial_max=.46, initial_faces=24)
    args.update(updates)
    return build_conditions(**args)


def completed(distance=.23, faces=12, *, budget=1, context=True):
    baseline = review(distance=.46, socket_faces=24)
    trials = {"adaptive_124": review(distance=distance, socket_faces=faces)}
    checkpoint = build_adaptive_checkpoint(baseline, trials, budget=budget)
    return build_run_review(checkpoint, budget=budget, stage="completed",
                            status="completed", integrity="verified",
                            conditions=conditions() if context else None)


class RunComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_same_conditions_determinism_and_input_nonmutation(self):
        first, second = completed(), completed()
        before = copy.deepcopy([first, second])
        result = compare_run_reviews([first, second])
        self.assertEqual(result["eligible_runs"], 2)
        self.assertTrue(result["comparison_available"])
        self.assertEqual(result["rows"][1]["comparison_status"], "no_meaningful_difference")
        self.assertEqual([first, second], before)
        self.assertIn("有意な観測差なし", render_run_comparison(result))
        self.assertFalse(any(result["safety"].values()))

    def test_improvement_regression_and_mixed_counts_are_distinct(self):
        result = compare_run_reviews([
            completed(), completed(.2, 10), completed(.3, 20), completed(.2, 20),
        ])
        self.assertEqual([r["comparison_status"] for r in result["rows"]], [
            "anchor", "observed_improvement", "observed_regression", "mixed_observations",
        ])
        self.assertEqual(result["rows"][1]["sampled_max_delta_from_anchor"], -.03)
        self.assertEqual(result["rows"][3]["socket_faces_delta_from_anchor"], 8)

    def test_tiny_distance_change_does_not_claim_improvement(self):
        result = compare_run_reviews([completed(), completed(.2299999, 12)])
        self.assertEqual(result["rows"][1]["comparison_status"], "no_meaningful_difference")

    def test_each_condition_difference_excludes_comparison(self):
        for key, value in (
            ("source_sha256", "d" * 64), ("reference_sha256", "d" * 64),
            ("baseline_sha256", "d" * 64), ("blender_version", "5.2.1"),
            ("combined_aabb_diagonal", 7.0),
        ):
            other = completed()
            other["conditions"][key] = value
            with self.subTest(key=key):
                result = compare_run_reviews([completed(), other])
                self.assertFalse(result["comparison_available"])
                self.assertEqual(result["rows"][1]["exclusion_reason"], "conditions_mismatch")
                self.assertIsNone(result["rows"][1]["sampled_max_delta_from_anchor"])

    def test_initial_observation_mismatch_is_invalid_not_ranked(self):
        other = completed()
        other["conditions"]["initial_sampled_max"] = .5
        result = compare_run_reviews([completed(), other])
        self.assertEqual(result["rows"][1]["exclusion_reason"], "invalid_report")
        self.assertIsNone(result["input_reviews"][1])

    def test_budget_mismatch_excluded_even_with_identical_conditions(self):
        baseline = review(distance=.46, socket_faces=24)
        cp = build_adaptive_checkpoint(baseline, {
            "adaptive_124": review(distance=.23, socket_faces=12),
            "adaptive_147": review(distance=.1, socket_faces=10),
        }, budget=2)
        other = build_run_review(cp, budget=2, stage="completed", status="completed",
                                 integrity="verified", conditions=conditions())
        result = compare_run_reviews([completed(), other])
        self.assertEqual(result["rows"][1]["exclusion_reason"], "budget_mismatch")

    def test_failed_prefix_goal_is_not_success_and_incomplete_is_excluded(self):
        baseline = review(distance=.46, socket_faces=24)
        cp = build_adaptive_checkpoint(baseline, {
            "adaptive_124": review(distance=.1, socket_faces=10),
        }, budget=2)
        failed = build_run_review(cp, budget=2, stage="candidate_comparison", status="failed",
                                 active_trial="adaptive_101", failure_code="comparison_timeout",
                                 integrity="verified", conditions=conditions())
        incomplete = build_run_review(cp, budget=2, stage="measurement_validated",
                                      integrity="verified", conditions=conditions())
        result = compare_run_reviews([failed, completed(), incomplete])
        self.assertEqual(result["anchor_run_id"], "run_002")
        self.assertEqual(result["rows"][0]["exclusion_reason"], "run_failed")
        self.assertTrue(result["rows"][0]["observed_goal_in_prefix"])
        self.assertIsNone(result["rows"][0]["sampled_max_delta_from_anchor"])
        self.assertEqual(result["rows"][2]["exclusion_reason"], "run_incomplete")

    def test_changed_inputs_hide_untrusted_metrics(self):
        cp = build_adaptive_checkpoint(review(distance=.46, socket_faces=24), {}, budget=1)
        failed = build_run_review(cp, budget=1, stage="candidate_comparison", status="failed",
            active_trial="adaptive_124", failure_code="input_integrity_changed", integrity="failed",
            conditions=conditions())
        row = compare_run_reviews([completed(), failed])["rows"][1]
        self.assertEqual(row["exclusion_reason"], "input_integrity_unverified")
        self.assertIsNone(row["best_sampled_max"])

    def test_legacy_readable_but_never_assumed_same_conditions(self):
        legacy = completed(context=False)
        self.assertEqual(legacy["schema_version"], 1)
        self.assertIn("試行予算を完了", render_run_review(legacy))
        result = compare_run_reviews([legacy, completed()])
        self.assertEqual(result["rows"][0]["exclusion_reason"], "missing_conditions")
        self.assertEqual(result["anchor_run_id"], "run_002")

    def test_bad_safety_unknown_labels_and_forged_decisions_do_not_leak(self):
        invalid = completed()
        invalid["safety"]["auto_applies_user_property"] = True
        invalid["private_path"] = "very-private-addon.py"
        result = compare_run_reviews([completed(), invalid])
        self.assertIsNone(result["input_reviews"][1])
        self.assertNotIn("very-private-addon.py", json.dumps(result))
        self.assertNotIn("very-private-addon.py", render_run_comparison(result))
        forged = copy.deepcopy(result)
        forged["rows"][1]["comparison_status"] = "observed_improvement"
        with self.assertRaises(ValueError):
            render_run_comparison(forged)
        forged = copy.deepcopy(result)
        forged["safety"]["executes_code"] = 0
        with self.assertRaises(ValueError):
            render_run_comparison(forged)

    def test_no_eligible_anchor_and_input_caps(self):
        result = compare_run_reviews([None, completed(context=False)])
        self.assertFalse(result["comparison_available"])
        self.assertIsNone(result["anchor_run_id"])
        for bad in ([], [completed()], [completed()] * 17, "secret"):
            with self.assertRaises(ValueError):
                compare_run_reviews(bad)
        self.assertEqual(compare_run_reviews([completed()] * 16)["eligible_runs"], 16)

    def test_condition_schema_rejects_flags_nan_paths_and_bad_hashes(self):
        good = conditions()
        for key, value in (
            ("max_trials", True), ("samples_per_triangle", 24.0),
            ("source_sha256", "secret.py"), ("blender_version", "secret"),
            ("combined_aabb_diagonal", True), ("initial_sampled_max", float("nan")),
            ("unexpected", "private.glb"),
        ):
            bad = copy.deepcopy(good)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_conditions(bad)

    def test_digest_reads_fixed_sources_without_execution_and_detects_change(self):
        source = self.root / "trusted.py"
        marker = self.root / "must-not-execute"
        source.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
        with patch("cbdk.glb_synthetic_conditions.SOURCES", ("trusted.py",)):
            first = condition_source_digest(self.root)
            self.assertFalse(marker.exists())
            source.write_text("raise RuntimeError('not executed')\n")
            self.assertNotEqual(condition_source_digest(self.root), first)
            source.unlink()
            with self.assertRaises(ValueError):
                condition_source_digest(self.root)

    def test_fresh_output_and_reader_cli_never_launch_processes(self):
        from cbdk.glb_synthetic_run_review import write_run_review
        for i in (1, 2):
            folder = self.root / str(i)
            folder.mkdir()
            write_run_review(completed(), folder)
        report = compare_run_reviews([completed(), completed()])
        output = self.root / "result"
        output.mkdir()
        paths = write_run_comparison(report, output)
        before = [p.read_bytes() for p in paths]
        with self.assertRaises(FileExistsError):
            write_run_comparison(report, output)
        self.assertEqual([p.read_bytes() for p in paths], before)
        import cbdk.glb_synthetic_run_compare as module
        with patch.object(module, "__file__", str(self.root / "cbdk/module.py")), \
             patch("subprocess.run") as proc, contextlib.redirect_stdout(io.StringIO()):
            code = main(["--run", str(self.root / "1/synthetic_run_review.json"),
                         "--run", str(self.root / "2/synthetic_run_review.json"),
                         "--output", str(self.root / "reports/latest/cli")])
            self.assertEqual(code, 0)
            proc.assert_not_called()
            code = main(["--run", str(self.root / "1/synthetic_run_review.json"),
                         "--run", str(self.root / "missing-secret.json"),
                         "--output", str(self.root / "reports/latest/cli_inconclusive")])
            self.assertEqual(code, 2)
        body = (self.root / "reports/latest/cli_inconclusive/synthetic_run_comparison.json").read_text()
        self.assertNotIn("missing-secret", body)


if __name__ == "__main__":
    unittest.main()
