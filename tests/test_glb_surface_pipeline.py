"""Safe local GLB surface-review preflight, Blender launcher, and report checks."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_surface_pipeline import (
    GLBSurfacePipelineError, MAX_INPUT_BYTES, run_glb_surface_review,
)


def inspection(*, external=False, meshes=1, vertices=12):
    return {
        "external_uris": [{"uri": "http://invalid.example/geometry.bin"}]
        if external else [],
        "counts": {
            "meshes": meshes, "approximate_vertex_references": vertices,
        },
    }


def report(*, status="review_only", unsafe=False):
    result = {
        "schema_version": 1,
        "kind": "cbdk_glb_surface_review",
        "source": "local_blender_import_aggregate_only",
        "status": status,
        "reference_triangles": 2,
        "candidate_triangles": 8,
        "complete_surface_equivalence_proven": False,
        "auto_apply": False,
        "safety": {
            "executes_addon_code": False,
            "uploads_private_glb": unsafe,
            "saves_raw_mesh_vertices": False,
            "changes_source_glbs": False,
        },
    }
    if status == "review_only":
        result.update({
            "fixed_surface": {"symmetric_sampled_max": 0.2},
            "adaptive_surface": {"refined_symmetric_sampled_max": 0.3},
            "surface_observation": "sampled_difference_detected",
        })
    else:
        result.update({"reason": "triangle_limit",
                       "surface_observation": "not_measured"})
    return result


class GLBSurfacePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ref = self.root / "private-reference.glb"
        self.cand = self.root / "private-candidate.glb"
        self.blender = self.root / "blender.exe"
        self.out = self.root / "reports" / "surface.json"
        for file in (self.ref, self.cand, self.blender):
            file.write_bytes(b"dummy")

    def run_fake(self, *, status="review_only", unsafe=False, report_override=None):
        commands = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            Path(cmd[-1]).write_text(json.dumps(report_override if report_override is not None else report(status=status, unsafe=unsafe)))
            line = "CBDK_GLB_SURFACE_REVIEW_PASS " + json.dumps({
                "kind": "cbdk_glb_surface_review", "status": status,
            }) + "\n"
            return subprocess.CompletedProcess(cmd, 0, stdout=line, stderr="")

        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()) as inspector, \
             patch("cbdk.glb_surface_pipeline.subprocess.run",
                   side_effect=fake_run) as process:
            result = run_glb_surface_review(
                self.blender, self.ref, self.cand, self.out)
        self.assertEqual(inspector.call_count, 2)
        self.assertEqual(process.call_count, 1)
        return result, commands[0]

    def test_successful_local_review_and_aggregate_output(self):
        result, command = self.run_fake()
        self.assertEqual(result["status"], "review_only")
        self.assertIn("--disable-autoexec", command)
        self.assertIn("--factory-startup", command)
        self.assertEqual(command[-3], str(self.ref.resolve()))
        self.assertEqual(command[-2], str(self.cand.resolve()))
        self.assertEqual(command[-1], str(self.out.resolve()))
        self.assertEqual(
            Path(command[command.index("--python") + 1]).name,
            "blender_glb_surface_review.py",
        )
        self.assertNotIn("private-reference.glb", self.out.read_text())
        self.assertFalse(result["auto_apply"])

    def test_triangle_limit_generates_skipped_not_approved(self):
        result, _ = self.run_fake(status="skipped")
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "triangle_limit")
        self.assertNotIn("fixed_surface", result)
        self.assertFalse(result["complete_surface_equivalence_proven"])

    def test_rejects_external_uri_before_blender_launch(self):
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection(external=True)), \
             patch("cbdk.glb_surface_pipeline.subprocess.run") as run:
            with self.assertRaisesRegex(GLBSurfacePipelineError, "External"):
                run_glb_surface_review(self.blender, self.ref, self.cand, self.out)
            run.assert_not_called()

    def test_rejects_no_mesh_or_excessive_accessor_references(self):
        for info in (inspection(meshes=0), inspection(vertices=100001)):
            with self.subTest(info=info), \
                 patch("cbdk.glb_surface_pipeline.inspect_glb", return_value=info), \
                 patch("cbdk.glb_surface_pipeline.subprocess.run") as run:
                with self.assertRaises(GLBSurfacePipelineError):
                    run_glb_surface_review(self.blender, self.ref, self.cand, self.out)
                run.assert_not_called()

    def test_rejects_wrong_extensions_and_missing_blender(self):
        self.cand.rename(self.root / "candidate.txt")
        with self.assertRaises(GLBSurfacePipelineError):
            run_glb_surface_review(self.blender, self.ref, self.cand, self.out)
        with self.assertRaises(GLBSurfacePipelineError):
            run_glb_surface_review(self.root / "not-found.exe", self.ref,
                                   self.ref, self.out)

    def test_rejects_oversized_file_without_import(self):
        with self.ref.open("r+b") as file:
            file.truncate(MAX_INPUT_BYTES + 1)
        with patch("cbdk.glb_surface_pipeline.subprocess.run") as run:
            with self.assertRaisesRegex(GLBSurfacePipelineError, "24 MiB"):
                run_glb_surface_review(self.blender, self.ref, self.cand, self.out)
            run.assert_not_called()

    def test_validates_timeout(self):
        for bad in (0, 9, 901, 10.5, "100", True):
            with self.subTest(bad=bad), self.assertRaises(GLBSurfacePipelineError):
                run_glb_surface_review(self.blender, self.ref, self.cand,
                                       self.out, timeout=bad)

    def test_rejects_non_json_output(self):
        with self.assertRaises(GLBSurfacePipelineError):
            run_glb_surface_review(
                self.blender, self.ref, self.cand, self.ref)

    def test_rejects_unsafe_report_flags(self):
        with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
            self.run_fake(unsafe=True)

    def test_prevents_stale_report_if_blender_fails(self):
        self.out.parent.mkdir(parents=True)
        self.out.write_text('{"status":"old"}')
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()), \
             patch("cbdk.glb_surface_pipeline.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 7,
                       stdout="bad", stderr="failed")):
            with self.assertRaisesRegex(GLBSurfacePipelineError, "failed"):
                run_glb_surface_review(self.blender, self.ref, self.cand, self.out)
        self.assertFalse(self.out.exists())

    def test_runner_timeout_rejected(self):
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()), \
             patch("cbdk.glb_surface_pipeline.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="blender", timeout=30)):
            with self.assertRaisesRegex(GLBSurfacePipelineError, "timed out"):
                run_glb_surface_review(self.blender, self.ref, self.cand, self.out)


    def test_rejects_nonfinite_negative_or_boolean_surface_metric(self):
        for bad in (float("nan"), float("inf"), -0.01, True, "0.2"):
            with self.subTest(value=repr(bad)):
                invalid = report()
                invalid["fixed_surface"]["symmetric_sampled_max"] = bad
                with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                    self.run_fake(report_override=invalid)

    def test_rejects_invalid_triangle_counts_and_skip_measurements(self):
        for invalid_count in (-1, 1.5, True, "8"):
            with self.subTest(count=repr(invalid_count)):
                invalid = report()
                invalid["reference_triangles"] = invalid_count
                with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                    self.run_fake(report_override=invalid)
        invalid = report(status="skipped")
        invalid["fixed_surface"] = {"symmetric_sampled_max": 0.0}
        with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
            self.run_fake(status="skipped", report_override=invalid)

    def test_rejects_observation_contradicting_measured_distance(self):
        for observed, fixed, adaptive in (
            ("no_difference_observed_at_samples", 0.2, 0.3),
            ("sampled_difference_detected", 0.0, 0.0),
        ):
            with self.subTest(observed=observed):
                invalid = report()
                invalid["surface_observation"] = observed
                invalid["fixed_surface"]["symmetric_sampled_max"] = fixed
                invalid["adaptive_surface"]["refined_symmetric_sampled_max"] = adaptive
                with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                    self.run_fake(report_override=invalid)

    def test_rejects_measured_triangle_count_over_cap(self):
        invalid = report()
        invalid["candidate_triangles"] = 513
        with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
            self.run_fake(report_override=invalid)

    def test_rejects_duplicate_keys_and_nonfinite_json_in_report(self):
        def fake_bad_report(raw):
            def run(cmd, **kwargs):
                Path(cmd[-1]).write_text(raw, encoding="utf-8")
                acknowledgment = json.dumps({
                    "kind": "cbdk_glb_surface_review",
                    "status": "review_only",
                })
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="CBDK_GLB_SURFACE_REVIEW_PASS " + acknowledgment,
                    stderr="",
                )
            with patch("cbdk.glb_surface_pipeline.inspect_glb",
                       return_value=inspection()), \
                 patch("cbdk.glb_surface_pipeline.subprocess.run",
                       side_effect=run):
                with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                    run_glb_surface_review(self.blender, self.ref, self.cand, self.out)

        valid = json.dumps(report())
        fake_bad_report(valid.replace('"schema_version": 1,',
                                      '"schema_version": 1, "schema_version": 1,', 1))
        fake_bad_report(valid.replace('"symmetric_sampled_max": 0.2',
                                      '"symmetric_sampled_max": NaN', 1))

    def test_rejects_duplicate_acknowledgment_keys(self):
        def run(cmd, **kwargs):
            Path(cmd[-1]).write_text(json.dumps(report()), encoding="utf-8")
            raw = ('{"kind":"cbdk_glb_surface_review",'
                   '"status":"review_only","status":"review_only"}')
            return subprocess.CompletedProcess(
                cmd, 0, stdout="CBDK_GLB_SURFACE_REVIEW_PASS " + raw,
                stderr="",
            )
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()), \
             patch("cbdk.glb_surface_pipeline.subprocess.run",
                   side_effect=run):
            with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                run_glb_surface_review(self.blender, self.ref, self.cand, self.out)

    def test_valid_anonymous_part_inventory(self):
        valid = report()
        valid["part_inventory"] = {
            "reference_object_count": 2,
            "candidate_object_count": 2,
            "reference_triangle_counts": [1, 1],
            "candidate_triangle_counts": [6, 2],
            "max_listed_per_side": 32,
            "correspondence_verified": False,
            "identifies_changed_part": False,
            "notes": "Anonymous size-ranked inventory, not matched objects",
        }
        result, _ = self.run_fake(report_override=valid)
        self.assertEqual(result["part_inventory"]["reference_object_count"], 2)

    def test_rejects_unverified_part_correspondence_and_mismatched_counts(self):
        valid = report()
        valid["part_inventory"] = {
            "reference_object_count": 2,
            "candidate_object_count": 2,
            "reference_triangle_counts": [1, 1],
            "candidate_triangle_counts": [6, 2],
            "max_listed_per_side": 32,
            "correspondence_verified": False,
            "identifies_changed_part": False,
            "notes": "Anonymous size-ranked inventory, not matched objects",
        }
        for mutation in (
            lambda p: p.update(correspondence_verified=True),
            lambda p: p.update(identifies_changed_part=True),
            lambda p: p.update(reference_triangle_counts=[2, 2]),
            lambda p: p.update(candidate_triangle_counts=[2, 6]),
            lambda p: p.update(candidate_object_count=3),
            lambda p: p.update(reference_triangle_counts=[True, 1]),
            lambda p: p.update(private_object_name="secret"),
        ):
            bad = json.loads(json.dumps(valid))
            mutation(bad["part_inventory"])
            with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                self.run_fake(report_override=bad)

    def test_part_count_hints_accepted_when_recomputed(self):
        from cbdk.glb_part_hints import count_based_part_hints
        valid = report()
        inventory = {
            "reference_object_count": 2, "candidate_object_count": 2,
            "reference_triangle_counts": [1, 1],
            "candidate_triangle_counts": [6, 2],
            "max_listed_per_side": 32,
            "correspondence_verified": False,
            "identifies_changed_part": False,
            "notes": "Anonymous size-ranked inventory, not matched objects",
        }
        valid["part_inventory"] = inventory
        valid["part_count_hints"] = count_based_part_hints(
            inventory["reference_triangle_counts"],
            inventory["candidate_triangle_counts"],
            reference_total=2, candidate_total=2,
        )
        result, _ = self.run_fake(report_override=valid)
        self.assertEqual(result["part_count_hints"]["candidate_count"], 0)
        invalid = json.loads(json.dumps(valid))
        invalid["part_count_hints"]["correspondence_verified"] = True
        with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
            self.run_fake(report_override=invalid)
        invalid = json.loads(json.dumps(valid))
        invalid["part_count_hints"]["weak_candidate_triangle_counts"] = [1]
        with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
            self.run_fake(report_override=invalid)

    def test_output_report_is_bounded(self):
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()), \
             patch("cbdk.glb_surface_pipeline.subprocess.run") as proc:
            def large_report(cmd, **kwargs):
                Path(cmd[-1]).write_text("X" * (1024 * 1024 + 1))
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="CBDK_GLB_SURFACE_REVIEW_PASS " +
                    json.dumps({"kind": "cbdk_glb_surface_review",
                                "status": "review_only"}), stderr="")
            proc.side_effect = large_report
            with self.assertRaisesRegex(GLBSurfacePipelineError, "report"):
                run_glb_surface_review(self.blender, self.ref, self.cand, self.out)


if __name__ == "__main__":
    unittest.main()
