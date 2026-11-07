"""Bound AST review and runtime evidence without executing original Python."""
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
from cbdk.glb_synthetic_conditions import aggregate_review_digest, build_conditions
from cbdk.glb_synthetic_run_review import build_run_review, render_run_review
from cbdk.glb_visual_experiment_review import (
    build_visual_experiment_review, main, render_visual_experiment_review, write_linked_review,
)
from test_glb_synthetic_adaptive import review


class VisualExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "PRIVATE_addon.py"
        self.marker = self.root / "must-not-execute"
        self.source.write_text(
            "from pathlib import Path\n" + f"Path({str(self.marker)!r}).touch()\n"
            "import bpy\nfrom bpy.props import FloatProperty\n"
            "class PrivateProps:\n"
            "    socket_opening_diameter: FloatProperty(default=987654321.123)\n"
            "    clearance: FloatProperty(default=0.2)\n"
            "    def build(self):\n"
            "        bpy.ops.mesh.primitive_cylinder_add(radius=self.socket_opening_diameter)\n")
        self.visual = review(distance=.46, socket_faces=24)
        self.candidate = review(distance=.23, socket_faces=24)

    def experiment(self, *, budget=1, trials=1, failed=False, bound=True):
        checkpoint = build_adaptive_checkpoint(self.visual,
            {"adaptive_124": self.candidate} if trials else {}, budget=budget)
        kwargs = dict(source_sha256="a" * 64, reference_sha256="b" * 64,
            baseline_sha256="c" * 64, blender_version="4.5.15", scale=6.0,
            initial_max=.46, initial_faces=24)
        if bound:
            kwargs["baseline_review_sha256"] = aggregate_review_digest(self.visual)
        return build_run_review(checkpoint, budget=budget,
            stage="candidate_comparison" if failed else "completed",
            status="failed" if failed else "completed",
            active_trial=("adaptive_147" if trials else "adaptive_124") if failed else None,
            failure_code="comparison_timeout" if failed else None, integrity="verified",
            conditions=build_conditions(**kwargs))

    def build(self, *, roles=None, experiment=None):
        return build_visual_experiment_review(self.visual, [self.source],
            experiment or self.experiment(), roles={"part_003": "socket"} if roles is None else roles)

    def test_bound_review_separates_static_name_from_synthetic_observations(self):
        before = self.source.read_bytes()
        result = self.build()
        self.assertEqual(result["linked_candidate_count"], 1)
        self.assertFalse(any(result["safety"].values()))
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.source.read_bytes(), before)
        link = next(row for row in result["candidate_links"] if row["candidate_family"] == "socket_opening_diameter")
        self.assertEqual(link["synthetic_control_id"], "socket_diameter")
        self.assertFalse(link["property_effect_verified"])
        self.assertIsNone(link["recommended_parameter_value"])
        text = render_visual_experiment_review(result)
        self.assertIn("実プロパティの因果は未証明", text)
        self.assertIn("socket_opening_diameter", text)
        self.assertIn("PrivateProps", text)
        self.assertNotIn("987654321", text)
        self.assertNotIn("PRIVATE_addon.py", text)
        self.assertNotIn(str(self.marker), text)

    def test_role_or_name_absence_does_not_infer_a_control(self):
        for roles in ({}, {"part_003": "hinge"}, {"part_001": "socket"}):
            with self.subTest(roles=roles):
                self.assertEqual(self.build(roles=roles)["linked_candidate_count"], 0)
        self.source.write_text("from bpy.props import FloatProperty\nclass Other:\n    unrelated: FloatProperty()\n")
        self.assertEqual(self.build()["linked_candidate_count"], 0)

    def test_failed_and_zero_trial_prefix_never_claims_run_completion(self):
        for trials in (0, 1):
            result = self.build(experiment=self.experiment(budget=2, trials=trials, failed=True))
            self.assertFalse(result["experiment_review"]["run_completed"])
            self.assertEqual(result["experiment_review"]["validated_attempts"], trials)
            self.assertIn("失敗・停止", render_visual_experiment_review(result))
            self.assertFalse(any(result["safety"].values()))

    def test_mismatched_visual_is_rejected_before_source_read(self):
        experiment = self.experiment()
        other = copy.deepcopy(self.visual)
        other["candidate_sampled_max"] = .47
        with patch("cbdk.glb_visual_experiment_review.build_visual_property_review") as parse:
            with self.assertRaises(ValueError):
                build_visual_experiment_review(other, [self.source], experiment)
            parse.assert_not_called()

    def test_legacy_binding_missing_is_readable_but_unlinkable(self):
        experiment = self.experiment(bound=False)
        render_run_review(experiment)
        with self.assertRaises(ValueError):
            self.build(experiment=experiment)

    def test_canonical_hash_ignores_json_formatting_and_order(self):
        reordered = json.loads(json.dumps(dict(reversed(list(self.visual.items()))), indent=4))
        self.assertEqual(aggregate_review_digest(self.visual), aggregate_review_digest(reordered))
        for value in (None, {"x": float("nan")}, {"x": "x" * (128 * 1024)}):
            with self.assertRaises(ValueError):
                aggregate_review_digest(value)

    def test_changed_inputs_and_forged_runtime_are_rejected(self):
        for mutate in (
            lambda r: r["safety"].update(user_addon_executed=True),
            lambda r: r["conditions"].update(baseline_review_sha256="d" * 64),
            lambda r: r["checkpoint"]["steps"][0].update(sampled_max=.01),
            lambda r: r.update(input_integrity="not_checked"),
        ):
            bad = self.experiment()
            mutate(bad)
            with self.assertRaises(ValueError):
                self.build(experiment=bad)

    def test_display_rejects_forged_causality_and_private_injections(self):
        good = self.build()
        for mutate in (
            lambda r: r["safety"].update(property_controls_generator_verified=True),
            lambda r: r["safety"].update(source_executed=0),
            lambda r: r["candidate_links"][0].update(property_effect_verified=True),
            lambda r: r["static_candidates"][0].update(private_path="secret.py"),
            lambda r: r["static_candidates"][0]["candidates"][0].update(family="private`code"),
            lambda r: r["baseline_metric"].update(socket_sampled_affected_faces=True),
            lambda r: r["static_candidates"][0].update(boundary_edges=1),
            lambda r: r.update(linked_candidate_count=99),
        ):
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(ValueError):
                render_visual_experiment_review(bad)

    def test_private_new_outputs_and_collision_preflight(self):
        result = self.build()
        paths = write_linked_review(result, "reports/latest/bound.json", root=self.root)
        before = [p.read_bytes() for p in paths]
        with self.assertRaises((ValueError, FileExistsError)):
            write_linked_review(result, "reports/latest/bound.json", root=self.root)
        self.assertEqual([p.read_bytes() for p in paths], before)
        md = self.root / "reports/latest/collision.md"
        md.write_text("keep")
        with self.assertRaises(FileExistsError):
            write_linked_review(result, "reports/latest/collision.json", root=self.root)
        self.assertFalse(md.with_suffix(".json").exists())
        self.assertEqual(md.read_text(), "keep")
        for output in ("docs/private.json", "reports/latest/../escape.json", str(self.root / "absolute.json")):
            with self.assertRaises(ValueError):
                write_linked_review(result, output, root=self.root)

    def test_cli_is_read_only_and_stdout_never_contains_private_candidates(self):
        visual, run = self.root / "visual.json", self.root / "run.json"
        visual.write_text(json.dumps(self.visual))
        run.write_text(json.dumps(self.experiment()))
        originals = (visual.read_bytes(), run.read_bytes(), self.source.read_bytes())
        with patch("cbdk.glb_visual_experiment_review.ROOT", self.root), \
             patch("subprocess.run") as launch, contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = main(["--visual-review", str(visual), "--run-review", str(run),
                         "--source", str(self.source), "--role", "part_003=socket",
                         "--output", "reports/latest/cli.json"])
            launch.assert_not_called()
        self.assertEqual(code, 0)
        for secret in ("socket_opening_diameter", "PrivateProps", str(self.root), "987654321"):
            self.assertNotIn(secret, stdout.getvalue())
        self.assertEqual((visual.read_bytes(), run.read_bytes(), self.source.read_bytes()), originals)
        self.assertFalse(self.marker.exists())
        run.write_text('{"status":1,"status":2}')
        with patch("cbdk.glb_visual_experiment_review.ROOT", self.root), \
             contextlib.redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit):
            main(["--visual-review", str(visual), "--run-review", str(run),
                  "--source", str(self.source), "--output", "reports/latest/bad.json"])
        self.assertNotIn(str(self.root), stderr.getvalue())
        self.assertFalse((self.root / "reports/latest/bad.json").exists())


if __name__ == "__main__":
    unittest.main()
