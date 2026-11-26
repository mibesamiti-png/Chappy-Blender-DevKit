"""Focus/AST/run reconciliation with explicit ambiguity and private outputs."""
import copy
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from cbdk.glb_experiment_triage import build_experiment_triage, render_experiment_triage, write_experiment_triage, main
import test_glb_visual_experiment_review as linked_fixture


class ExperimentTriageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = linked_fixture.VisualExperimentTests(methodName="test_bound_review_separates_static_name_from_synthetic_observations")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def build(self, **kwargs):
        return build_experiment_triage(self.fixture.visual, self.fixture.build(**kwargs))

    def test_single_candidate_keeps_runtime_uncertainty(self):
        report = self.build()
        self.assertFalse(any(report["safety"].values()))
        self.assertTrue(all(r["selected_declaration"] is None for r in report["candidate_reviews"]))
        trial = report["trial_observations"][0]
        self.assertEqual(trial["global_sampled_max_change_from_previous"], -.23)
        self.assertEqual(trial["candidate_socket_face_change_from_previous"], 0)
        self.assertIn("実プロパティ因果は未証明", render_experiment_triage(report))

    def test_same_name_in_two_classes_is_ambiguous_even_with_geometry_path(self):
        with self.fixture.source.open("a", encoding="utf-8") as stream:
            stream.write('\nclass OtherProps:\n    socket_opening_diameter: FloatProperty()\n')
        report = self.build()
        row = next(r for r in report["candidate_reviews"] if r["family"] == "socket_opening_diameter")
        self.assertEqual(row["declaration_count"], 2)
        self.assertEqual(row["status"], "multiple_static_declarations")
        self.assertTrue(row["syntax_counts_are_family_aggregates"])
        self.assertIsNone(row["selected_declaration"])
        self.assertFalse(self.fixture.marker.exists())

    def test_no_matching_declarations_is_not_a_cause_exclusion(self):
        self.fixture.source.write_text("class Empty: pass\n", encoding="utf-8")
        report = self.build()
        self.assertEqual(report["candidate_reviews"], [])
        self.assertIn("原因不存在", render_experiment_triage(report))

    def test_existing_property_review_exposes_reference_only_focus(self):
        from cbdk.glb_visual_property_review import build_visual_property_review
        from cbdk.glb_visual_review_markdown import render_review_markdown
        visual = copy.deepcopy(self.fixture.visual)
        visual["parts"]["reference"][2].update(low=72, medium=24)
        visual["reference"].update(low=128, medium=24)
        visual["parts"]["candidate"][2].update(low=96, medium=0)
        visual["candidate"].update(low=152, medium=0)
        mapped = build_visual_property_review(visual, [self.fixture.source])
        self.assertEqual(mapped["recommendations"], [])
        text = render_review_markdown(mapped)
        self.assertIn("reference / part_003", text)
        self.assertIn("参照側だけの差分", text)
        self.assertNotIn("レビュー対象の差分が観測されません", text)

    def test_failed_and_zero_prefix_remain_incomplete(self):
        for trials in (0, 1):
            report = self.build(experiment=self.fixture.experiment(budget=2, trials=trials, failed=True))
            self.assertEqual(report["experiment_status"], "failed")
            self.assertEqual(report["next_action"], "review_failed_or_incomplete_prefix")
            self.assertEqual(len(report["trial_observations"]), trials)

    def test_r17_private_review_connects_focus_declarations_and_trial_decisions(self):
        from cbdk.glb_synthetic_adaptive import build_adaptive_checkpoint
        from cbdk.glb_synthetic_run_review import build_run_review
        from test_glb_synthetic_adaptive import review
        self.fixture.source.write_text(
            "from bpy.props import FloatProperty\n"
            "class First:\n    socket_opening_diameter: FloatProperty()\n"
            "class Second:\n    socket_opening_diameter: FloatProperty()\n",
            encoding="utf-8")
        original = self.fixture.experiment()
        checkpoint = build_adaptive_checkpoint(
            self.fixture.visual, {
                "adaptive_124": self.fixture.candidate,
                "adaptive_147": review(distance=.30, socket_faces=24),
                "adaptive_158": review(distance=.10, socket_faces=12),
            }, budget=3)
        run = build_run_review(checkpoint, budget=3, stage="completed",
                               status="completed", integrity="verified",
                               conditions=original["conditions"])
        report = self.build(experiment=run)
        before = copy.deepcopy(report)
        text = render_experiment_triage(report)
        for fragment in (
            "candidate / part_003", "socket_opening_diameter",
            "First", "Second", "同名宣言の実体を区別",
            "adaptive_124", "adaptive_147", "adaptive_158",
            "観測進捗あり", "観測進捗として棄却",
            "no_meaningful_sampled_max_improvement",
            "attempt_budget_exhausted", "合成目標内: adaptive_158",
            "検証済み試行: 3/3", "実設定値の推薦はしない",
        ):
            self.assertIn(fragment, text)
        self.assertNotIn(str(self.fixture.root), text)
        self.assertFalse(self.fixture.marker.exists())
        self.assertEqual(report, before)
        self.assertFalse(any(report["safety"].values()))

    def test_r17_interrupted_prefix_distinguishes_unmeasured_and_failure(self):
        from cbdk.glb_synthetic_run_review import build_run_review
        for trials in (0, 1):
            failed = self.fixture.experiment(budget=2, trials=trials, failed=True)
            for status in ("failed", "incomplete"):
                run = build_run_review(
                    failed["checkpoint"], budget=2, stage=failed["stage"],
                    status=status, active_trial=failed["active_trial_id"],
                    failure_code=failed["failure_code"] if status == "failed" else None,
                    integrity="verified", conditions=failed["conditions"])
                text = render_experiment_triage(self.build(experiment=run))
                with self.subTest(trials=trials, status=status):
                    self.assertIn(f"実行状態: {status}", text)
                    self.assertIn(f"検証済み試行: {trials}/2", text)
                    self.assertIn(f"未検証枠: {2-trials}", text)
                    self.assertIn("incomplete_trace", text)
                    self.assertIn("処理対象: " + run["active_trial_id"], text)
                    self.assertIn("比較処理の負荷" if status == "failed" else
                                  "終了証拠を確認する", text)
                    self.assertIn("自動実行・自動再開・設定値適用なし", text)
                    if not trials:
                        self.assertIn("初期観測以外は未測定", text)
                    self.assertNotIn("試行予算は完了", text)

    def test_r17_single_candidate_is_not_a_runtime_binding(self):
        text = render_experiment_triage(self.build())
        self.assertIn("宣言位置:", text)
        self.assertIn("実行時に登録・参照される設定か別途確認", text)
        self.assertIn("人の役割ラベルと名称による照合候補のみ", text)
        self.assertIn("実ユーザーGLB・元アドオンの使用や実行は別の明示許可", text)
        self.assertNotIn(str(self.fixture.root), text)
        self.assertNotIn("987654321", text)

    def test_different_baseline_and_conflicting_summaries_rejected(self):
        linked = self.fixture.build()
        other = copy.deepcopy(self.fixture.visual); other["candidate_sampled_max"] = .47
        with self.assertRaises(ValueError):
            build_experiment_triage(other, linked)
        good = self.build()
        good["focus_review"]["observations"]["candidate"][2]["medium"] = 23
        with self.assertRaises(ValueError):
            render_experiment_triage(good)

    def test_r26_weak_candidate_is_not_same_fixture_runtime_evidence(self):
        from test_parameter_fixture_evidence import observations, reduce
        report = self.build()
        self.assertFalse(any(report["safety"].values()))
        self.assertTrue(all(row["selected_declaration"] is None for row in report["candidate_reviews"]))
        static, native = observations()
        # A static candidate and independent native run cannot be joined,
        # even if property names and fixed source digest happen to match.
        self.assertEqual(reduce(static, None)["status"], "incomplete")
        native["run_id"] = "2" * 32
        self.assertEqual(reduce(static, native)["reason_codes"], ["identity_mismatch"])
        native["run_id"] = static["run_id"]
        native["source_sha256"] = "b" * 64
        self.assertEqual(reduce(static, native)["reason_codes"], ["identity_mismatch"])
        static, native = observations()
        native["properties"][0]["causality_proven"] = True
        rejected = reduce(static, native)
        self.assertFalse(rejected["same_fixture_observations_verified"])
        self.assertFalse(any(rejected["safety"].values()))

    def test_forged_candidate_selection_and_delta_rejected(self):
        for change in (
            lambda r: r["candidate_reviews"][0].update(selected_declaration="first"),
            lambda r: r["trial_observations"][0].update(global_sampled_max_change_from_previous=-1),
            lambda r: r["safety"].update(causality_proven=True),
            lambda r: r.update(private_path="secret"),
        ):
            report = self.build(); change(report)
            with self.assertRaises(ValueError):
                render_experiment_triage(report)

    def test_private_output_exclusive_and_escape_refused(self):
        report = self.build(); root = self.fixture.root
        paths = write_experiment_triage(report, "reports/latest/triage.json", root=root)
        before = [p.read_bytes() for p in paths]
        with self.assertRaises((ValueError, FileExistsError)):
            write_experiment_triage(report, "reports/latest/triage.json", root=root)
        self.assertEqual(before, [p.read_bytes() for p in paths])
        for path in ("docs/leak.json", "reports/latest/../leak.json", str(root / "absolute.json")):
            with self.assertRaises(ValueError):
                write_experiment_triage(report, path, root=root)

    def test_cli_never_launches_source_or_prints_candidates(self):
        root = self.fixture.root
        visual, linked = root / "visual.json", root / "linked.json"
        visual.write_text(json.dumps(self.fixture.visual), encoding="utf-8")
        linked.write_text(json.dumps(self.fixture.build()), encoding="utf-8")
        from cbdk.glb_experiment_triage import write_experiment_triage as writer
        with patch("cbdk.glb_experiment_triage.write_experiment_triage", side_effect=lambda r, p: writer(r, p, root=root)), \
             patch("subprocess.run") as run, contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main(["--visual-review", str(visual), "--linked-review", str(linked),
                                   "--output", "reports/latest/cli-triage.json"]), 0)
        run.assert_not_called()
        self.assertNotIn("PrivateProps", stdout.getvalue())
        self.assertNotIn("socket_opening_diameter", stdout.getvalue())
