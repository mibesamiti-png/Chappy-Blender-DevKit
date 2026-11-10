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


    def test_r8_pruned_r2_review_never_promotes_file_identity(self):
        """Conservative R8 broad-phase may speed review, never approve a GLB.

        GLB-specific mocked facade test; actual Blender export/import is
        covered separately by the CI's existing headless Blender smoke.
        """
        from cbdk.glb_part_match import suggest_spatial_part_matches
        from test_glb_match_pruning_r8 import original_unpruned
        from test_glb_match_adversarial_r7 import split_edge_fan

        ref = split_edge_fan(.30)
        for name, other, status in (
            ("resegmented_collinear", split_edge_fan(.70), "suggested"),
            ("moved_notch", split_edge_fan(.70, indentation=.03), "ambiguous"),
        ):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                match = suggest_spatial_part_matches(ref, other, [5], [5])
                self.assertEqual(match, original_unpruned(ref, other, [5], [5]))
                self.assertEqual(match["reference_parts"][0]["status"], status)
                self.assertFalse(match["auto_apply"])
                self.assertFalse(match["cross_file_part_identity_proven"])
                review = {
                    "kind": "cbdk_glb_surface_review",
                    "status": "review_only",
                    "surface_observation": "no_difference_observed_at_samples",
                    "part_match_candidates": match,
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
                           return_value=review):
                    output = run_glb_regression(
                        root / "blender", root / "a.glb", root / "b.glb",
                        root / "out", surface_review=True,
                    )
                self.assertIs(output["surface_does_not_auto_approve"], True)
                self.assertIs(output["passed_is_metadata_only"], True)
                self.assertEqual(output["surface_status"], "review_only")


    def test_r9_dense_fallback_review_is_never_file_approval(self):
        """R9 near-notch candidates stay reviewer hints through the facade.

        This GLB-owned mocked-IO test triggers existing Blender workflow.
        R9 dense-AABB stress inputs themselves are Python-only fixtures.
        """
        from cbdk.glb_part_match import suggest_spatial_part_matches
        from test_glb_match_pruning_r8 import original_unpruned
        from test_glb_match_adversarial_r7 import split_edge_fan

        reference = split_edge_fan(.30)
        for label, candidate, expected in (
            ("same_contour_resplit", split_edge_fan(.70), "suggested"),
            ("near_notch", split_edge_fan(.70, indentation=.0001), "suggested"),
            ("real_notch", split_edge_fan(.70, indentation=.03), "ambiguous"),
        ):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                pairing = suggest_spatial_part_matches(
                    reference, candidate, [5], [5])
                self.assertEqual(pairing, original_unpruned(
                    reference, candidate, [5], [5]))
                self.assertEqual(pairing["reference_parts"][0]["status"], expected)
                self.assertFalse(pairing["cross_file_part_identity_proven"])
                self.assertFalse(pairing["auto_apply"])

                surface = {
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
                           return_value=surface):
                    result = run_glb_regression(
                        root / "blender", root / "a.glb", root / "b.glb",
                        root / "out", surface_review=True)
                self.assertIs(result["surface_does_not_auto_approve"], True)
                self.assertIs(result["passed_is_metadata_only"], True)
                self.assertEqual(result["surface_status"], "review_only")


    def test_r10_adaptive_candidates_never_approve_a_glb_file(self):
        """An adaptive R2 optimization is never a semantic file approval.

        This is a GLB-owned mocked facade test. The existing headless
        Blender CI separately checks authored GLB export/import smoke;
        dense R10 geometry stress itself remains Python-only.
        """
        from cbdk.glb_part_match import suggest_spatial_part_matches
        from test_glb_match_adaptive_r10 import always_box_report
        from test_glb_match_adversarial_r7 import split_edge_fan

        ref = split_edge_fan(.30)
        for name, cand, expected in (
            ("collinear", split_edge_fan(.70), "suggested"),
            ("small_notch", split_edge_fan(.70, indentation=.0001),
             "suggested"),
            ("real_notch", split_edge_fan(.70, indentation=.03),
             "ambiguous"),
        ):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                pairing = suggest_spatial_part_matches(ref, cand, [5], [5])
                self.assertEqual(pairing, always_box_report(
                    ref, cand, [5], [5]))
                self.assertEqual(pairing["reference_parts"][0]["status"],
                                 expected)
                self.assertFalse(pairing["auto_apply"])
                self.assertFalse(pairing["cross_file_part_identity_proven"])
                surface = {
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
                           return_value=surface):
                    result = run_glb_regression(
                        root / "blender", root / "a.glb", root / "b.glb",
                        root / "out", surface_review=True)
                self.assertIs(result["surface_does_not_auto_approve"], True)
                self.assertIs(result["passed_is_metadata_only"], True)
                self.assertEqual(result["surface_status"], "review_only")


    def test_r14_anonymous_evidence_triage_never_approves_regression(self):
        """A review-only triage cannot override a metadata-only GLB result.

        Mocked local I/O here; real self-authored GLB exports are independently
        exercised by the existing Blender multi-version CI workflow.
        """
        from cbdk.glb_evidence_triage import build_glb_evidence_triage
        from cbdk.glb_compare import compare_scene_metadata
        from test_glb_compare import obj, scene

        reference = scene([obj("UNPUBLISHED_TEST_ASSET", [0, 0, 0],
                               [2, 2, 1])])
        candidate = scene([obj("UNPUBLISHED_TEST_ASSET", [.4, 0, 0],
                               [2, 2, 1])])
        comparison = compare_scene_metadata(reference, candidate)
        triage = build_glb_evidence_triage(comparison=comparison)
        self.assertEqual(triage["status"], "review_only")
        self.assertFalse(any(triage["safety"].values()))
        self.assertIn("metadata_differences", triage["review_topics"])
        self.assertIn("sampled_surface_distance", triage["unobserved_channels"])
        self.assertNotIn("UNPUBLISHED_TEST_ASSET", str(triage))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("cbdk.glb_regression.write_glb_inspection"), \
                 patch("cbdk.glb_regression.render_glb_preview"), \
                 patch("cbdk.glb_regression.write_scene_comparison",
                       return_value=comparison):
                result = run_glb_regression(
                    root / "blender", root / "reference.glb",
                    root / "candidate.glb", root / "out")
        self.assertFalse(result["passed"])
        self.assertIs(result["passed_is_metadata_only"], True)
        self.assertIs(result["surface_does_not_auto_approve"], True)
        self.assertEqual(result["surface_status"], "not_requested")


    def test_r15_declared_basis_cannot_approve_glb_regression(self):
        """A matching self-declared basis is not a geometry or file verdict.

        Mock the GLB launcher I/O; the existing Blender workflow separately
        runs CBDK's synthetic GLB exports on all three native versions.
        """
        from cbdk.glb_evidence_basis_r15 import build_bound_glb_evidence_triage
        from test_glb_evidence_basis_r15 import BASIS, claimed_sources, reports

        inputs = reports("missing")
        bound = build_bound_glb_evidence_triage(
            **inputs, source_basis=claimed_sources(inputs),
            expected_basis=BASIS)
        self.assertEqual(bound["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assertFalse(bound["basis_review"]["sources_verified_same_run"])
        self.assertFalse(any(bound["safety"].values()))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("cbdk.glb_regression.write_glb_inspection"), \
                 patch("cbdk.glb_regression.render_glb_preview"), \
                 patch("cbdk.glb_regression.write_scene_comparison",
                       return_value=inputs["comparison"]):
                actual = run_glb_regression(
                    root / "blender", root / "reference.glb",
                    root / "candidate.glb", root / "out")
            self.assertIs(actual["passed"], False)
            self.assertIs(actual["passed_is_metadata_only"], True)
            self.assertIs(actual["surface_does_not_auto_approve"], True)
            self.assertEqual(actual["surface_status"], "not_requested")


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
