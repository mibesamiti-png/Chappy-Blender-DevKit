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

    def test_different_baseline_and_conflicting_summaries_rejected(self):
        linked = self.fixture.build()
        other = copy.deepcopy(self.fixture.visual); other["candidate_sampled_max"] = .47
        with self.assertRaises(ValueError):
            build_experiment_triage(other, linked)
        good = self.build()
        good["focus_review"]["observations"]["candidate"][2]["medium"] = 23
        with self.assertRaises(ValueError):
            render_experiment_triage(good)

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
