"""Durable synthetic run review, adversarial state checks and runner failures."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_surface_pipeline import GLBSurfacePipelineError
from cbdk.glb_synthetic_adaptive import (
    build_adaptive_checkpoint, render_adaptive_checkpoint, render_adaptive_history,
)
from cbdk.glb_synthetic_run_review import (
    build_run_review, read_run_review, render_run_review, write_run_review,
)
from scripts import run_glb022_synthetic_adaptive as runner
from test_glb_synthetic_adaptive import review


class RunReviewTests(unittest.TestCase):
    def setUp(self):
        self.baseline = review(distance=.46, socket_faces=24)
        self.trials = {
            "adaptive_124": review(distance=.23, socket_faces=24),
            "adaptive_147": review(distance=.115, socket_faces=12),
            "adaptive_135": review(distance=.175, socket_faces=18),
            "adaptive_141": review(distance=.145, socket_faces=15),
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        (self.root / "scripts/blender_make_glb_joint_mvp_fixtures.py").write_text(
            "# fake trusted generator, never executed in unit tests\n")
        self.exe = self.root / "blender"
        self.exe.write_bytes(b"mock")
        self.serial = 0

    def checkpoint(self, n=1, budget=4):
        return build_adaptive_checkpoint(self.baseline,
                                        dict(list(self.trials.items())[:n]), budget=budget)

    def output(self):
        self.serial += 1
        return self.root / "reports/ci" / f"case_{self.serial}"

    def generate(self, cmd, **kwargs):
        self.assertIn("--factory-startup", cmd)
        self.assertIn("--disable-autoexec", cmd)
        folder = Path(cmd[cmd.index("--") + 1])
        kind = cmd[cmd.index("--single") + 1]
        folder.mkdir(parents=True)
        (folder / (kind + ".glb")).write_bytes(b"g" * 128)
        return subprocess.CompletedProcess(cmd, 0,
            stdout="CBDK_JOINT_MVP_FIXTURES_PASS\n", stderr="")

    @contextlib.contextmanager
    def mocked(self, *, compare=None, generate=None):
        with patch.object(runner, "REPO", self.root), \
             patch.object(runner, "condition_source_digest", return_value="a" * 64), \
             patch.object(runner.subprocess, "run", side_effect=generate or self.generate), \
             patch.object(runner, "run_glb_diff_visualize", side_effect=compare or
                          [self.baseline, *self.trials.values()]), \
             contextlib.redirect_stdout(io.StringIO()) as stdout:
            yield stdout

    def test_partial_and_zero_attempt_checkpoints_stay_incomplete(self):
        for count in (0, 1, 2, 3):
            checkpoint = self.checkpoint(count)
            self.assertEqual(checkpoint["stop_reason"], "incomplete_trace")
            self.assertIn("incomplete_trace", render_adaptive_checkpoint(checkpoint))
            with self.assertRaises(ValueError):
                render_adaptive_history(checkpoint)
        initial = build_run_review(None, budget=4, stage="reference_generation")
        self.assertIn("終了証拠なし", render_run_review(initial))
        self.assertFalse(initial["run_completed"])

    def test_completed_budget_does_not_claim_goal_or_optimum(self):
        report = build_run_review(self.checkpoint(1, budget=1), budget=1,
                                  stage="completed", status="completed", integrity="verified")
        self.assertTrue(report["run_completed"])
        self.assertFalse(report["sampled_goal_observed"])
        self.assertIn("最適性は未証明", render_run_review(report))

    def test_failure_preserves_feasible_prefix_without_completion(self):
        report = build_run_review(self.checkpoint(2), budget=4,
            stage="candidate_comparison", status="failed", active_trial="adaptive_135",
            failure_code="comparison_timeout", integrity="verified")
        self.assertTrue(report["sampled_goal_observed"])
        self.assertFalse(report["run_completed"])
        self.assertEqual(report["validated_attempts"], 2)
        self.assertIn("自動再試行・自動再開は行わない", render_run_review(report))

    def test_rejects_forged_completion_active_candidate_and_state(self):
        for params in (
            dict(stage="completed", status="completed", integrity="verified"),
            dict(stage="candidate_generation", active_trial="adaptive_135"),
            dict(stage="candidate_generation"),
            dict(stage="candidate_comparison", active_trial="secret.py"),
            dict(stage="history_output", status="failed", failure_code="secret text"),
            dict(stage="history_output", integrity="failed"),
            dict(stage="history_output", status="failed", failure_code="input_integrity_changed"),
        ):
            with self.subTest(params=params), self.assertRaises(ValueError):
                build_run_review(self.checkpoint(), budget=4, **params)

    def test_rejects_numeric_safety_aliases_unknown_fields_and_forged_metrics(self):
        good = build_run_review(self.checkpoint(), budget=4, stage="measurement_validated")
        for mutate in (
            lambda r: r.update(run_completed=0),
            lambda r: r.update(schema_version=True),
            lambda r: r.update(private_path="secret.glb"),
            lambda r: r["safety"].update(user_addon_executed=0),
            lambda r: r["checkpoint"]["safety"].update(user_addon_executed=0),
            lambda r: r["checkpoint"]["steps"][0].update(sampled_max=float("nan")),
            lambda r: r["checkpoint"].update(measured_feasible_trial_id="adaptive_124"),
        ):
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(ValueError):
                render_run_review(bad)

    def test_exclusive_files_strict_json_and_bounded_reader(self):
        report = build_run_review(None, budget=4, stage="reference_generation")
        j, m = write_run_review(report, self.root, sequence=0)
        before = (j.read_bytes(), m.read_bytes())
        self.assertEqual(read_run_review(j), report)
        with self.assertRaises(FileExistsError):
            write_run_review(report, self.root, sequence=0)
        self.assertEqual((j.read_bytes(), m.read_bytes()), before)
        with self.assertRaises(ValueError):
            write_run_review(report, self.root)
        for sequence in (-1, 16, True):
            with self.assertRaises(ValueError):
                write_run_review(report, self.root, sequence=sequence)
        bad = self.root / "bad.json"
        for body in ('{"status":0,"status":1}', '{"x":NaN}', "x" * (128 * 1024 + 1)):
            bad.write_text(body)
            with self.assertRaises(ValueError):
                read_run_review(bad)

    def test_markdown_failure_does_not_publish_json_receipt(self):
        report = build_run_review(self.checkpoint(1, budget=1), budget=1,
                                  stage="completed", status="completed", integrity="verified")
        original_open = Path.open
        def fail_markdown(path, *args, **kwargs):
            if path.suffix == ".md":
                raise OSError("private disk message")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", fail_markdown), self.assertRaises(OSError):
            write_run_review(report, self.root)
        self.assertFalse((self.root / "synthetic_run_review.json").exists())

    def test_runner_success_checkpoints_and_legacy_history(self):
        output = self.output()
        with self.mocked() as stdout:
            history = runner.run(self.exe, output)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertEqual(history, terminal["checkpoint"])
        self.assertTrue(terminal["run_completed"])
        self.assertEqual(terminal["input_integrity"], "verified")
        self.assertIn("CBDK_GLB022_ADAPTIVE_SYNTHETIC_PASS", stdout.getvalue())
        self.assertTrue((output / "synthetic_adaptive_history.json").is_file())
        files = sorted(output.glob("checkpoint_*.json"))
        self.assertEqual(len(files), 14)
        self.assertEqual([p.name for p in files], [f"checkpoint_{i:03d}.json" for i in range(14)])
        for file in files:
            self.assertFalse(read_run_review(file)["run_completed"])

    def test_runner_timeout_after_one_validated_candidate_is_durable(self):
        timeout = subprocess.TimeoutExpired("private-path.glb", 180)
        wrapped = GLBSurfacePipelineError("private comparison stderr")
        wrapped.__cause__ = timeout
        output = self.output()
        with self.mocked(compare=[self.baseline, self.trials["adaptive_124"], wrapped]) as stdout:
            with self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, "comparison_timeout"):
                runner.run(self.exe, output)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertEqual(terminal["validated_attempts"], 1)
        self.assertEqual(terminal["active_trial_id"], "adaptive_147")
        self.assertEqual(terminal["checkpoint"]["best_observed_trial_id"], "adaptive_124")
        self.assertNotIn("PASS", stdout.getvalue())
        self.assertFalse((output / "synthetic_adaptive_history.json").exists())
        for path in output.glob("*.json"):
            self.assertNotIn("private-path.glb", path.read_text())
            self.assertNotIn("private comparison stderr", path.read_text())

    def test_runner_generation_failure_and_timeout_before_baseline(self):
        for failure, code in (
            (subprocess.TimeoutExpired("private command", 180), "generation_timeout"),
            (OSError("private path"), "generation_failed"),
            (subprocess.CompletedProcess([], 7, stdout="private stderr", stderr=""), "generation_failed"),
        ):
            output = self.output()
            with self.mocked(generate=[failure]), self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, code):
                runner.run(self.exe, output)
            terminal = read_run_review(output / "synthetic_run_review.json")
            self.assertIsNone(terminal["checkpoint"])
            self.assertEqual(terminal["stage"], "reference_generation")
            self.assertFalse(terminal["sampled_goal_observed"])

    def test_runner_unsafe_scale_and_cross_part_results_do_not_advance(self):
        cases = [
            (review(distance=.2, socket_faces=20, ball_faces=1), "cross_part_regression"),
            (review(distance=.2, socket_faces=20, scale=7), "coordinate_scale_changed"),
            (review(distance=float("inf"), socket_faces=20), "invalid_measurement"),
        ]
        unsafe = review(distance=.2, socket_faces=20)
        unsafe["safety"]["executes_addon_code"] = True
        cases.append((unsafe, "invalid_measurement"))
        wrong_version = review(distance=.2, socket_faces=20)
        wrong_version["blender_version"] = "5.2.1"
        cases.append((wrong_version, "invalid_measurement"))
        for candidate, code in cases:
            output = self.output()
            with self.mocked(compare=[self.baseline, candidate]), self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, code):
                runner.run(self.exe, output)
            terminal = read_run_review(output / "synthetic_run_review.json")
            self.assertEqual(terminal["validated_attempts"], 0)
            self.assertEqual(terminal["active_trial_id"], "adaptive_124")
            self.assertEqual(terminal["checkpoint"]["best_observed_trial_id"], "narrow")

    def test_runner_detects_input_mutation_and_marks_observations_untrusted(self):
        def changed(exe, ref, cand, output, **kwargs):
            ref.write_bytes(b"changed input")
            return self.baseline
        output = self.output()
        with self.mocked(compare=changed), self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, "input_integrity_changed"):
            runner.run(self.exe, output)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertEqual(terminal["input_integrity"], "failed")
        self.assertIsNone(terminal["checkpoint"])

    def test_runner_rejects_comparison_source_change_before_generation(self):
        output = self.output()
        with self.mocked(), patch.object(runner, "condition_source_digest",
                side_effect=["a" * 64, "b" * 64, "b" * 64]):
            with self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, "input_integrity_changed"):
                runner.run(self.exe, output)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertEqual(terminal["input_integrity"], "failed")
        self.assertEqual(terminal["stage"], "reference_generation")
        self.assertIsNone(terminal["checkpoint"])

    def test_runner_history_write_failure_preserves_full_trace_but_not_success(self):
        output = self.output()
        with self.mocked(), patch.object(runner, "write_adaptive_history", side_effect=OSError("private path")):
            with self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, "io_failure"):
                runner.run(self.exe, output)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertEqual(terminal["validated_attempts"], 4)
        self.assertTrue(terminal["sampled_goal_observed"])
        self.assertFalse(terminal["run_completed"])

    def test_cli_interruption_and_failure_exit_without_private_error_text(self):
        for failure, expected in ((KeyboardInterrupt(), 130), (GLBSurfacePipelineError("private"), 1)):
            output = self.output()
            with self.mocked(compare=[failure]), contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = runner.main(["--blender", str(self.exe), "--output", str(output)])
            self.assertEqual(code, expected)
            self.assertNotIn("private", stderr.getvalue())
            self.assertEqual(read_run_review(output / "synthetic_run_review.json")["status"], "failed")

    def test_one_trial_runner_finishes_budget_without_claiming_target(self):
        output = self.output()
        with self.mocked(compare=[self.baseline, self.trials["adaptive_124"]]):
            runner.run(self.exe, output, budget=1)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertTrue(terminal["run_completed"])
        self.assertFalse(terminal["sampled_goal_observed"])
        self.assertEqual(terminal["checkpoint"]["stop_reason"], "attempt_budget_exhausted")

    def test_generation_timeout_preserves_prior_validated_measurement(self):
        count = 0
        def generate(cmd, **kwargs):
            nonlocal count
            count += 1
            if count == 4:
                raise subprocess.TimeoutExpired("private launch path", 180)
            return self.generate(cmd, **kwargs)
        output = self.output()
        with self.mocked(generate=generate), self.assertRaisesRegex(runner.SyntheticAdaptiveRunError, "generation_timeout"):
            runner.run(self.exe, output)
        terminal = read_run_review(output / "synthetic_run_review.json")
        self.assertEqual(terminal["stage"], "candidate_generation")
        self.assertEqual(terminal["active_trial_id"], "adaptive_147")
        self.assertEqual(terminal["validated_attempts"], 1)
        self.assertEqual(terminal["checkpoint"]["best_observed_trial_id"], "adaptive_124")

    def test_reader_cli_never_launches_or_resumes_trials(self):
        from cbdk.glb_synthetic_run_review import main
        report = build_run_review(None, budget=4, stage="reference_generation")
        path, _ = write_run_review(report, self.root, sequence=0)
        with patch.object(runner.subprocess, "run") as proc, contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main([str(path)]), 0)
            proc.assert_not_called()
        self.assertIn("終了証拠なし", stdout.getvalue())

    def test_failure_code_cannot_claim_a_different_operation(self):
        for stage, code in (("history_output", "comparison_timeout"),
                            ("candidate_generation", "cross_part_regression"),
                            ("candidate_comparison", "generation_failed")):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                build_run_review(self.checkpoint(), budget=4, stage=stage,
                    status="failed", failure_code=code,
                    active_trial="adaptive_147" if stage.startswith("candidate_") else None)

    def test_terminal_write_failure_leaves_no_completed_checkpoint(self):
        actual_write = runner.write_run_review
        for fail_all_terminal in (False, True):
            output = self.output()
            def fail_terminal(report, directory, **kwargs):
                if "sequence" not in kwargs and (fail_all_terminal or report["status"] == "completed"):
                    raise OSError("private write error")
                return actual_write(report, directory, **kwargs)
            with self.mocked(), patch.object(runner, "write_run_review", side_effect=fail_terminal):
                with self.assertRaises(runner.SyntheticAdaptiveRunError):
                    runner.run(self.exe, output)
            for path in output.glob("checkpoint_*.json"):
                self.assertEqual(read_run_review(path)["status"], "incomplete")
            terminal = output / "synthetic_run_review.json"
            if fail_all_terminal:
                self.assertFalse(terminal.exists())
            else:
                self.assertEqual(read_run_review(terminal)["status"], "failed")

    def test_runner_refuses_existing_output_and_invalid_budget_before_execution(self):
        with self.mocked(), patch.object(runner.subprocess, "run") as process:
            for budget in (0, 5, True):
                with self.assertRaises(ValueError):
                    runner.run(self.exe, self.output(), budget=budget)
            with self.assertRaises(ValueError):
                runner.run(self.exe, self.root / "scripts")
            process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
