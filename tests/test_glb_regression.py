from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_regression import run_glb_regression


class GLBRegressionTests(unittest.TestCase):
    def test_orchestrates_two_previews_then_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref = root / "ref.glb"; cand = root / "cand.glb"
            ref.write_bytes(b"x"); cand.write_bytes(b"y")
            comparison = {
                "kind": "cbdk_glb_scene_comparison",
                "passed": True,
                "summary": {"errors": 0},
                "differences": [],
            }
            with patch("cbdk.glb_regression.write_glb_inspection") as inspect, \
                 patch("cbdk.glb_regression.render_glb_preview") as render, \
                 patch("cbdk.glb_regression.write_scene_comparison", return_value=comparison) as compare:
                result = run_glb_regression(
                    root / "blender", ref, cand, root / "out",
                    resolution=320, timeout=90, profile="shape",
                )
            self.assertEqual(inspect.call_count, 2)
            self.assertEqual(render.call_count, 2)
            self.assertEqual(compare.call_count, 1)
            self.assertTrue(result["passed"])
            self.assertEqual(result["profile"], "shape")
            self.assertEqual(result["parameter_review_candidates"], 0)
            self.assertTrue((root / "out" / "repair_plan.json").is_file())


    def test_optional_surface_review_is_called_and_remains_review_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref, cand = root / "ref.glb", root / "cand.glb"
            ref.write_bytes(b"x")
            cand.write_bytes(b"y")
            comparison = {
                "kind": "cbdk_glb_scene_comparison",
                "passed": True,
                "summary": {"errors": 0},
                "differences": [],
            }
            surface = {
                "kind": "cbdk_glb_surface_review",
                "status": "review_only",
                "surface_observation": "sampled_difference_detected",
            }
            with patch("cbdk.glb_regression.write_glb_inspection"), \
                 patch("cbdk.glb_regression.render_glb_preview"), \
                 patch("cbdk.glb_regression.write_scene_comparison",
                       return_value=comparison), \
                 patch("cbdk.glb_regression.run_glb_surface_review",
                       return_value=surface) as review:
                result = run_glb_regression(
                    root / "blender", ref, cand, root / "out",
                    surface_review=True, timeout=150,
                )
            review.assert_called_once_with(
                root / "blender", ref, cand,
                root / "out" / "surface_review.json", timeout=150)
            self.assertTrue(result["passed"])
            self.assertTrue(result["passed_is_metadata_only"])
            self.assertTrue(result["surface_does_not_auto_approve"])
            self.assertEqual(result["surface_status"], "review_only")
            self.assertEqual(result["surface_observation"],
                             "sampled_difference_detected")

    def test_r5_boundary_candidate_does_not_become_authoritative_regression(self):
        """Candidate ordering and changed openings never approve a GLB regression.

        Exercise the actual public regression orchestration return contract
        using CBDK-authored surfaces and mocked subprocess/GLB preflight.
        No third-party data or Blender code execution occurs in this unit test.
        """
        from cbdk.glb_part_match import suggest_spatial_part_matches
        from test_glb_match_determinism_r5 import reorder_faces
        from test_glb_part_match import square_frame

        original = square_frame()
        cases = (
            ("equivalent_reordered", reorder_faces(original), "suggested"),
            ("changed_opening", reorder_faces(square_frame(opening_x=.24)),
             "ambiguous"),
        )
        comparison = {
            "kind": "cbdk_glb_scene_comparison",
            "passed": True,
            "summary": {"errors": 0},
            "differences": [],
        }
        for label, other, expected in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                reference, candidate = root / "ref.glb", root / "cand.glb"
                reference.write_bytes(b"x")
                candidate.write_bytes(b"y")
                pairing = suggest_spatial_part_matches(
                    original, other, [8], [8],
                )
                self.assertEqual(pairing["reference_parts"][0]["status"], expected)
                self.assertFalse(pairing["auto_apply"])
                self.assertFalse(pairing["cross_file_part_identity_proven"])
                surface = {
                    "kind": "cbdk_glb_surface_review",
                    "status": "review_only",
                    "surface_observation": "no_difference_observed_at_samples",
                    "part_match_candidates": pairing,
                }
                with patch("cbdk.glb_regression.write_glb_inspection"), \
                     patch("cbdk.glb_regression.render_glb_preview"), \
                     patch("cbdk.glb_regression.write_scene_comparison",
                           return_value=comparison), \
                     patch("cbdk.glb_regression.run_glb_surface_review",
                           return_value=surface):
                    result = run_glb_regression(
                        root / "blender", reference, candidate, root / "out",
                        surface_review=True,
                    )
                self.assertEqual(result["surface_status"], "review_only")
                self.assertTrue(result["surface_does_not_auto_approve"])
                self.assertTrue(result["passed_is_metadata_only"])


    def test_r6_exact_contour_shortcut_never_authorizes_file_regression(self):
        """New R6 fast path cannot change the facade's review-only contract.

        This GLB-owned regression test triggers the existing headless Blender
        workflow but uses mocked IO here; no private GLB is executed.
        """
        from cbdk.glb_part_match import suggest_spatial_part_matches
        from test_glb_match_fastpath_r6 import baseline_scan
        from test_glb_part_match import square_frame

        original = square_frame()
        for label, candidate, expected in (
            ("same_contour", square_frame(flip_diagonal=True), "suggested"),
            ("moved_opening", square_frame(opening_x=.24), "ambiguous"),
        ):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                pairing = suggest_spatial_part_matches(
                    original, candidate, [8], [8])
                self.assertEqual(pairing, baseline_scan(
                    original, candidate, [8], [8]))
                self.assertEqual(pairing["reference_parts"][0]["status"],
                                 expected)
                self.assertFalse(pairing["cross_file_part_identity_proven"])
                self.assertFalse(pairing["auto_apply"])
                report = {
                    "kind": "cbdk_glb_surface_review",
                    "status": "review_only",
                    "surface_observation": "no_difference_observed_at_samples",
                    "part_match_candidates": pairing,
                }
                comparison = {
                    "kind": "cbdk_glb_scene_comparison",
                    "passed": True,
                    "summary": {"errors": 0},
                    "differences": [],
                }
                with patch("cbdk.glb_regression.write_glb_inspection"), \
                     patch("cbdk.glb_regression.render_glb_preview"), \
                     patch("cbdk.glb_regression.write_scene_comparison",
                           return_value=comparison), \
                     patch("cbdk.glb_regression.run_glb_surface_review",
                           return_value=report):
                    result = run_glb_regression(
                        root / "blender", root / "ref.glb",
                        root / "cand.glb", root / "out", surface_review=True)
                self.assertTrue(result["surface_does_not_auto_approve"])
                self.assertTrue(result["passed_is_metadata_only"])
                self.assertEqual(result["surface_status"], "review_only")


    def test_r7_adversarial_contour_never_approves_glb_regression(self):
        """Same count but moved notch remains a review signal, not authority.

        GLB-owned mocked facade control; native Blender export/import is
        separately exercised by the existing triggered version matrix.
        """
        from cbdk.glb_part_match import suggest_spatial_part_matches
        from test_glb_match_adversarial_r7 import split_edge_fan
        from test_glb_match_fastpath_r6 import baseline_scan

        ref = split_edge_fan(.30)
        for name, cand, expected in (
            ("collinear_split", split_edge_fan(.70), "suggested"),
            ("inward_notch", split_edge_fan(.70, indentation=.03),
             "ambiguous"),
        ):
            with self.subTest(geometry=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                observed = suggest_spatial_part_matches(ref, cand, [5], [5])
                self.assertEqual(observed, baseline_scan(ref, cand, [5], [5]))
                self.assertEqual(observed["reference_parts"][0]["status"], expected)
                self.assertFalse(observed["auto_apply"])
                self.assertFalse(observed["cross_file_part_identity_proven"])

                surface = {
                    "kind": "cbdk_glb_surface_review",
                    "status": "review_only",
                    "surface_observation": "no_difference_observed_at_samples",
                    "part_match_candidates": observed,
                }
                metadata = {
                    "kind": "cbdk_glb_scene_comparison",
                    "passed": True,
                    "summary": {"errors": 0},
                    "differences": [],
                }
                with patch("cbdk.glb_regression.write_glb_inspection"), \
                     patch("cbdk.glb_regression.render_glb_preview"), \
                     patch("cbdk.glb_regression.write_scene_comparison",
                           return_value=metadata), \
                     patch("cbdk.glb_regression.run_glb_surface_review",
                           return_value=surface):
                    result = run_glb_regression(
                        root / "blender", root / "reference.glb",
                        root / "candidate.glb", root / "out",
                        surface_review=True,
                    )
                self.assertIs(result["surface_does_not_auto_approve"], True)
                self.assertIs(result["passed_is_metadata_only"], True)
                self.assertEqual(result["surface_status"], "review_only")


    def test_optional_surface_stage_can_report_skipped_without_false_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            comparison = {
                "kind": "cbdk_glb_scene_comparison",
                "passed": True,
                "summary": {"errors": 0},
                "differences": [],
            }
            with patch("cbdk.glb_regression.write_glb_inspection"), \
                 patch("cbdk.glb_regression.render_glb_preview"), \
                 patch("cbdk.glb_regression.write_scene_comparison",
                       return_value=comparison), \
                 patch("cbdk.glb_regression.run_glb_surface_review",
                       return_value={
                           "kind": "cbdk_glb_surface_review",
                           "status": "skipped",
                           "surface_observation": "not_measured",
                       }):
                result = run_glb_regression(
                    root / "blender", root / "a.glb", root / "b.glb",
                    root / "out", surface_review=True)
            self.assertTrue(result["passed"])
            self.assertTrue(result["passed_is_metadata_only"])
            self.assertTrue(result["surface_does_not_auto_approve"])
            self.assertEqual(result["surface_status"], "skipped")
            self.assertEqual(result["surface_observation"], "not_measured")

    def test_invalid_surface_review_switch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_glb_regression(
                    Path(tmp) / "blender", Path(tmp) / "a.glb",
                    Path(tmp) / "b.glb", Path(tmp) / "out",
                    surface_review="yes")


if __name__ == "__main__":
    unittest.main()
