"""GLB-020: 3D difference color correctness, privacy and launcher tests."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_diff_colors import classify_faces, COLOR_RGBA
from cbdk.glb_diff_visualize import run_glb_diff_visualize
from cbdk.glb_surface_pipeline import GLBSurfacePipelineError


TRI = [[(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)]]


def shift(faces, z):
    return [[(x, y, zz + z) for x, y, zz in face] for face in faces]


def inspection():
    return {"external_uris": [], "counts": {
        "meshes": 1, "approximate_vertex_references": 3,
    }}


def report():
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_diff_visualization",
        "status": "review_only",
        "source": "local_blender_import_color_overlay",
        "outputs": ["reference_diff.glb", "candidate_diff.glb"],
        "triangle_limit_per_scene": 512,
        "reference": {"low": 1, "medium": 0, "high": 0},
        "candidate": {"low": 1, "medium": 0, "high": 0},
        "sampled_only": True,
        "complete_surface_equivalence_proven": False,
        "auto_apply": False,
        "thresholds": {
            "combined_aabb_diagonal": 1.414,
            "medium_from": 0.014,
            "high_from": 0.07,
        },
        "safety": {
            "executes_addon_code": False,
            "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False,
            "changes_source_glbs": False,
        },
    }


class ColorClassificationTests(unittest.TestCase):
    def test_identical_triangle_is_grey_both_directions(self):
        values = classify_faces(TRI, TRI)
        self.assertEqual(values["reference_labels"], ["low"])
        self.assertEqual(values["candidate_labels"], ["low"])
        self.assertEqual(values["reference_sampled_max"], 0.0)
        self.assertFalse(values["complete_surface_equivalence_proven"])
        self.assertTrue(values["sampled_only"])

    def test_medium_and_large_offset_have_distinct_colors(self):
        medium = classify_faces(TRI, shift(TRI, .03))
        high = classify_faces(TRI, shift(TRI, .3))
        self.assertEqual(medium["reference_labels"], ["medium"])
        self.assertEqual(medium["candidate_labels"], ["medium"])
        self.assertEqual(high["reference_labels"], ["high"])
        self.assertEqual(high["candidate_labels"], ["high"])
        self.assertEqual(len(COLOR_RGBA), 3)

    def test_winding_does_not_change_classification(self):
        inverted = [[TRI[0][2], TRI[0][0], TRI[0][1]]]
        values = classify_faces(inverted, TRI)
        self.assertEqual(values["reference_labels"], ["low"])
        self.assertEqual(values["candidate_labels"], ["low"])

    def test_source_face_order_is_preserved(self):
        faces = TRI + shift(TRI, .5)
        values = classify_faces(faces, TRI)
        self.assertEqual(values["reference_labels"], ["low", "high"])

    def test_degenerate_nan_and_oversized_inputs_are_rejected(self):
        bad = [[(0., 0., 0.)] * 3]
        for source in (bad, shift(TRI, float("nan")), TRI * 513):
            with self.subTest(source_len=len(source)):
                with self.assertRaises(ValueError):
                    classify_faces(source, TRI)

    def test_thresholds_and_count_totals_are_explicit(self):
        values = classify_faces(TRI, shift(TRI, .03))
        self.assertGreater(values["thresholds"]["high_from"],
                           values["thresholds"]["medium_from"])
        self.assertEqual(sum(values["reference_counts"].values()), 1)
        self.assertEqual(values["thresholds"]["samples_per_triangle"], 24)


class ColoredGLBLauncherTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ref = self.root / "private_ref.glb"
        self.cand = self.root / "private_candidate.glb"
        self.exe = self.root / "blender.exe"
        for p in (self.ref, self.cand, self.exe):
            p.write_bytes(b"stub")
        self.dest = self.root / "colors"

    def fake_runner(self, cmd, **kwargs):
        target = Path(cmd[-1])
        (target / "review.json").write_text(json.dumps(report()))
        for name in ("reference_diff.glb", "candidate_diff.glb"):
            (target / name).write_bytes(b"x" * 150)
        return subprocess.CompletedProcess(
            cmd, 0, stdout="CBDK_GLB_DIFF_VISUALIZE_PASS " +
            json.dumps({"kind": "cbdk_glb_diff_visualization",
                        "status": "review_only"}), stderr="",
        )

    def run_ok(self, runner=None):
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()), \
             patch("cbdk.glb_diff_visualize.subprocess.run",
                   side_effect=runner or self.fake_runner) as proc:
            result = run_glb_diff_visualize(
                self.exe, self.ref, self.cand, self.dest)
        return result, proc.call_args.args[0]

    def test_outputs_two_local_3d_glbs_and_aggregates(self):
        result, command = self.run_ok()
        self.assertEqual(result["status"], "review_only")
        self.assertIn("--disable-autoexec", command)
        self.assertIn("--factory-startup", command)
        self.assertEqual(command[-3:-1],
                         [str(self.ref.resolve()), str(self.cand.resolve())])
        self.assertEqual(Path(command[command.index("--python") + 1]).name,
                         "blender_glb_diff_visualize.py")
        report_json = (self.dest / "review.json").read_text()
        self.assertNotIn("private_ref", report_json)
        self.assertFalse(result["auto_apply"])

    def test_refuses_existing_folder_instead_of_overwriting(self):
        self.dest.mkdir()
        (self.dest / "user.txt").write_text("keep")
        with patch("cbdk.glb_surface_pipeline.inspect_glb",
                   return_value=inspection()), \
             patch("cbdk.glb_diff_visualize.subprocess.run") as runner:
            with self.assertRaisesRegex(GLBSurfacePipelineError, "must not exist"):
                run_glb_diff_visualize(
                    self.exe, self.ref, self.cand, self.dest)
            runner.assert_not_called()
        self.assertEqual((self.dest / "user.txt").read_text(), "keep")

    def test_rejects_nonzero_blender_exit(self):
        def failure(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 7, stdout="", stderr="failed")
        with self.assertRaisesRegex(GLBSurfacePipelineError, "failed"):
            self.run_ok(failure)

    def test_rejects_fake_files_or_unsafe_reports(self):
        def no_files(cmd, **kwargs):
            target = Path(cmd[-1])
            (target / "review.json").write_text(json.dumps(report()))
            return subprocess.CompletedProcess(
                cmd, 0, stdout="CBDK_GLB_DIFF_VISUALIZE_PASS " +
                json.dumps({"kind": "cbdk_glb_diff_visualization",
                            "status": "review_only"}), stderr="")
        with self.assertRaisesRegex(GLBSurfacePipelineError, "outputs"):
            self.run_ok(no_files)

    def test_rejects_external_uri_before_start(self):
        info = inspection()
        info["external_uris"] = [{"uri": "https://example.invalid/x"}]
        with patch("cbdk.glb_surface_pipeline.inspect_glb", return_value=info), \
             patch("cbdk.glb_diff_visualize.subprocess.run") as proc:
            with self.assertRaises(GLBSurfacePipelineError):
                run_glb_diff_visualize(self.exe, self.ref, self.cand, self.dest)
            proc.assert_not_called()

    def test_invalid_timeout(self):
        for timeout in (0, True, "30", 901):
            with self.subTest(timeout=timeout):
                with self.assertRaises(GLBSurfacePipelineError):
                    run_glb_diff_visualize(
                        self.exe, self.ref, self.cand, self.dest, timeout=timeout)


if __name__ == "__main__":
    unittest.main()
