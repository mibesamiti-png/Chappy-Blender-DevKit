"""GLB-020: 3D difference color correctness, privacy and launcher tests."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_diff_colors import (
    classify_faces, COLOR_RGBA, summarize_anonymous_parts,
)
from cbdk.glb_diff_visualize import run_glb_diff_visualize
from cbdk.glb_diff_viewer import render_local_diff_viewer
from cbdk.glb_part_match import suggest_spatial_part_matches
from cbdk.glb_boundary_audit import boundary_audit
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
        "viewer": "compare_viewer.html",
        "viewer_contains_derived_geometry": True,
        "viewer_local_only": True,
        "viewer_shared_camera": True,
        "viewer_browser_interaction_verified": False,
        "unobserved_regions_verified": False,
        "triangle_limit_per_scene": 512,
        "part_count_limit_per_scene": 64,
        "part_id_scheme": "anonymous_sequential_by_imported_object_name",
        "cross_file_part_identity_proven": False,
        "part_match_candidates": suggest_spatial_part_matches(TRI, TRI, [1], [1]),
        "boundary_edge_audit": {
            "method": boundary_audit(TRI, [1])["method"],
            "relative_weld_epsilon": 1e-7,
            "coordinate_welding_is_approximate": True,
            "fully_watertight_proven": False,
            "internal_voids_verified": False,
            "hole_locations_verified": False,
            "reference": boundary_audit(TRI, [1])["summary"],
            "candidate": boundary_audit(TRI, [1])["summary"],
            "parts": {
                "reference": boundary_audit(TRI, [1])["parts"],
                "candidate": boundary_audit(TRI, [1])["parts"],
            },
        },
        "sampling_sensitivity_audit": {
            "method": "extra_halton_24_probe_sensitivity_v1",
            "initial_samples_per_triangle": 24,
            "additional_samples_per_triangle": 24,
            "sensitivity_rule": "increase_gt_0.5pct_scene_diagonal_or_color_threshold_crossing",
            "unobserved_regions_verified": False,
            "complete_surface_equivalence_proven": False,
            "reference": {"sensitive_faces": 0, "face_count": 1, "max_observed_increase": 0.0},
            "candidate": {"sensitive_faces": 0, "face_count": 1, "max_observed_increase": 0.0},
            "per_part_sensitive_faces": {"reference": [0], "candidate": [0]},
        },
        "parts": {
            "reference": [
                {"part_id": "part_001", "triangle_count": 1,
                 "low": 1, "medium": 0, "high": 0},
            ],
            "candidate": [
                {"part_id": "part_001", "triangle_count": 1,
                 "low": 1, "medium": 0, "high": 0},
            ],
        },
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


class AnonymizedPartGroupingTests(unittest.TestCase):
    def test_parts_count_only_their_own_face_labels(self):
        values = summarize_anonymous_parts(
            ["low", "high", "medium", "low"], [1, 2, 1],
        )
        self.assertEqual([row["part_id"] for row in values],
                         ["part_001", "part_002", "part_003"])
        self.assertEqual(values[1]["triangle_count"], 2)
        self.assertEqual(values[1]["medium"], 1)
        self.assertEqual(values[1]["high"], 1)
        self.assertNotIn("source_name", repr(values))
        self.assertNotIn("object_name", repr(values))

    def test_bounded_part_layouts_reject_mismatch_and_empty_parts(self):
        for labels, counts in (
            (["low"], [2]),
            (["low"], [0, 1]),
            (["low"], [True]),
            (["low"], [1] * 65),
            (["unknown"], [1]),
            ([], []),
        ):
            with self.subTest(counts=counts, labels=labels):
                with self.assertRaises(ValueError):
                    summarize_anonymous_parts(labels, counts)


class OfflineLinkedViewerTests(unittest.TestCase):
    def test_bounded_offline_view_has_two_synced_canvases(self):
        html = render_local_diff_viewer(
            TRI, shift(TRI, .2), ["high"], ["high"], [1], [1],
        )
        self.assertEqual(html.count('id="cbdk-viewer-data"'), 1)
        self.assertIn("canvas-reference", html)
        self.assertIn("canvas-candidate", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("connect-src 'none'", html)
        self.assertIn("camera.yaw", html)
        self.assertIn("camera.zoom", html)
        self.assertIn("window.addEventListener", html)
        self.assertIn('"cross_file_part_identity_proven":false', html)
        self.assertIn('"unobserved_regions_verified":false', html)
        self.assertNotIn("__CBDK_VIEWER_DATA__", html)
        self.assertNotIn('PRIVATE_SOURCE_ALPHA', html)

    def test_html_payload_has_only_numeric_geometry_and_anonymous_parts(self):
        html = render_local_diff_viewer(
            TRI + shift(TRI, .3), TRI,
            ["low", "high"], ["high"], [1, 1], [1],
        )
        prefix = '<script id="cbdk-viewer-data" type="application/json">'
        content = html.split(prefix, 1)[1].split("</script>", 1)[0]
        data = json.loads(content)
        self.assertEqual(data["reference"]["faces"][0][0:2], [1, 0])
        self.assertEqual(data["reference"]["faces"][1][0:2], [2, 2])
        self.assertEqual(len(data["reference"]["faces"][1]), 11)
        self.assertEqual(data["reference"]["parts"][1]["part_id"], "part_002")
        self.assertEqual(len(data["candidate"]["parts"]), 1)
        self.assertFalse(data["auto_apply"])
        self.assertEqual(data["part_suggestions"]["reference_parts"][0]["status"], "suggested")
        self.assertFalse(data["part_suggestions"]["cross_file_part_identity_proven"])
        self.assertEqual(data["boundary_observations"]["reference"][0]["boundary_edges"], 3)
        self.assertEqual(len(data["boundary_overlay"]["reference"]), 6)
        self.assertEqual(len(data["boundary_overlay"]["candidate"]), 3)
        self.assertTrue(data["boundary_overlay_approximate"])
        self.assertFalse(data["boundary_location_proven"])
        self.assertTrue(all(len(line) == 7 and line[0] in (1, 2)
                            for line in data["boundary_overlay"]["reference"]))
        self.assertIn('id="show-boundaries"', html)
        self.assertEqual(data["sampling_sensitivity_flags"]["reference"], [0, 0])
        self.assertFalse(data["sampling_sensitivity_is_full_coverage"])
        self.assertNotIn("name", content)
        self.assertNotIn("private", content)

    def test_viewer_rejects_unaligned_or_non_boolean_sample_flags(self):
        for flags in ({"reference": [False], "candidate": []},
                      {"reference": [1], "candidate": [False]},
                      {"reference": [False]},
                      {"reference": [False], "candidate": [False], "other": []}):
            with self.subTest(flags=flags):
                with self.assertRaises(ValueError):
                    render_local_diff_viewer(
                        TRI, TRI, ["low"], ["low"], [1], [1],
                        sampling_flags=flags,
                    )

    def test_invalid_or_excessive_geometry_does_not_generate_html(self):
        for faces, categories, counts in (
            ([], [], []),
            (TRI, ["unknown"], [1]),
            (TRI, ["low"], [2]),
            (TRI * 513, ["low"] * 513, [513]),
            (shift(TRI, float("nan")), ["low"], [1]),
        ):
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    render_local_diff_viewer(
                        faces, TRI, categories, ["low"], counts, [1],
                    )


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
        (target / "compare_viewer.html").write_text(
            render_local_diff_viewer(TRI, TRI, ["low"], ["low"], [1], [1]),
            encoding="utf-8",
        )
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
        html = (self.dest / "compare_viewer.html").read_text(encoding="utf-8")
        self.assertIn("canvas-reference", html)
        self.assertIn("canvas-candidate", html)
        self.assertIn('id="show-boundaries"', html)
        self.assertNotIn("private_ref", html)
        self.assertNotIn("__CBDK_VIEWER_DATA__", html)

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

    def test_optional_topology_reason_codes_reject_tampering(self):
        # Old v1 aggregate reports may omit the new explanatory list.
        # A present list must be a canonical subset consistent with the
        # existing conservative review flag.
        cases = (
            ("legacy", None, True),
            ("unknown", ["not_a_measured_reason"], False),
            ("contradictory", ["boundary_edge_count_mismatch"], False),
            ("bool", True, False),
            ("duplicate", ["boundary_edge_count_mismatch",
                           "boundary_edge_count_mismatch"], False),
        )
        for label, reasons, accepted in cases:
            with self.subTest(case=label):
                self.dest = self.root / ("colors_" + label)

                def forged(cmd, **kwargs):
                    result = self.fake_runner(cmd, **kwargs)
                    output = Path(cmd[-1]) / "review.json"
                    data = json.loads(output.read_text(encoding="utf-8"))
                    row = data["part_match_candidates"]["reference_parts"][0]
                    if reasons is None:
                        row.pop("topology_review_reasons", None)
                    else:
                        row["topology_review_reasons"] = reasons
                    output.write_text(json.dumps(data), encoding="utf-8")
                    return result

                if accepted:
                    self.run_ok(forged)
                else:
                    with self.assertRaises(GLBSurfacePipelineError):
                        self.run_ok(forged)

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
