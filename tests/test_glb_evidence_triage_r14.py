"""R14 GLB anonymous evidence triage: four authored shapes and fail closed.

No user GLBs, file paths, object names or AST source references are emitted.
"""
from __future__ import annotations

import copy
import json
import math
import unittest

from cbdk.glb_boundary_audit import boundary_audit
from cbdk.glb_compare import compare_scene_metadata
from cbdk.glb_evidence_triage import build_glb_evidence_triage, KIND
from cbdk.glb_surface_distance import compare_triangle_surfaces
from test_glb_compare import obj, scene, silhouette
from test_glb_part_match import square_frame, triangle
import test_glb_visual_experiment_review as linked_fixture
from cbdk.glb_experiment_triage import build_experiment_triage


def authored_case(case):
    """Return comparable CBDK-created fixtures, never real private models."""
    reference = square_frame()
    candidate = square_frame()
    reference_counts = [8]
    candidate_counts = [8]
    old_objects = [obj("TestBody", [0, 0, 0], [2, 2, .1])]
    new_objects = [obj("TestBody", [0, 0, 0], [2, 2, .1])]
    old_pixels = silhouette([0, 1, 8, 9])
    new_pixels = old_pixels
    if case == "displacement":
        candidate = square_frame(offset_x=.25)
        new_objects = [obj("TestBody", [.25, 0, 0], [2, 2, .1])]
    elif case == "opening":
        candidate = square_frame(opening_x=.35)
        new_pixels = silhouette([0, 1, 2, 8, 9, 10])
    elif case == "missing":
        reference += [triangle(x=5)]
        reference_counts = [8, 1]
        old_objects.append(obj("Missing", [5, 0, 0], [1, 1, .1]))
    elif case != "identical":
        raise ValueError("Unknown test fixture")
    original_metadata = scene(old_objects)
    candidate_metadata = scene(new_objects)
    original_metadata["silhouettes"] = {"front.png": old_pixels}
    candidate_metadata["silhouettes"] = {"front.png": new_pixels}
    comparison = compare_scene_metadata(
        original_metadata, candidate_metadata,
        profile="strict" if case == "missing" else "shape",
        silhouette_iou_min=.8)
    surface = compare_triangle_surfaces(reference, candidate)
    left = boundary_audit(reference, reference_counts)
    right = boundary_audit(candidate, candidate_counts)
    return comparison, left, right, surface


class R14GLBEvidenceTriageTests(unittest.TestCase):

    def assembled(self, case):
        comparison, left, right, surface = authored_case(case)
        report = build_glb_evidence_triage(
            comparison=comparison,
            boundary_reference=left,
            boundary_candidate=right,
            sampled_surface=surface)
        return report, (comparison, left, right, surface)

    def assert_safety(self, report):
        self.assertEqual(report["kind"], KIND)
        self.assertEqual(report["status"], "review_only")
        self.assertFalse(any(report["safety"].values()))
        self.assertFalse(report["evidence_sources_verified_same_run"])
        self.assertNotIn("source_name", json.dumps(report, sort_keys=True))
        self.assertNotIn("TestBody", json.dumps(report, sort_keys=True))
        self.assertNotIn("Missing", json.dumps(report, sort_keys=True))

    def test_four_authored_geometry_conditions_preserve_existing_evidence(self):
        for name in ("identical", "displacement", "opening", "missing"):
            with self.subTest(case=name):
                report, originals = self.assembled(name)
                comparison, ref, cand, surface = originals
                channels = report["channels"]
                self.assert_safety(report)
                self.assertEqual(channels["metadata_differences"]["errors"],
                                 comparison["summary"]["errors"])
                self.assertEqual(channels["silhouette_iou"]["view_count"], 1)
                self.assertEqual(channels["silhouette_iou"]["worst_observed_iou"],
                                 min(comparison["summary"]["scene_silhouette_iou"].values()))
                self.assertEqual(channels["boundary_counts"]["reference_boundary_edges"],
                                 ref["summary"]["boundary_edges"])
                self.assertEqual(channels["boundary_counts"]["candidate_boundary_edges"],
                                 cand["summary"]["boundary_edges"])
                self.assertEqual(channels["sampled_surface_distance"]["sampled_max"],
                                 surface["symmetric_sampled_max"])
                self.assertEqual(channels["static_property_candidates"]["status"],
                                 "not_measured")
                if name == "identical":
                    self.assertTrue(comparison["passed"])
                    self.assertEqual(channels["metadata_differences"]["status"],
                                     "no_difference_reported")
                    self.assertEqual(channels["sampled_surface_distance"]["status"],
                                     "no_difference_observed_at_samples")
                    self.assertEqual(report["review_topics"], [])
                    self.assertFalse(channels["metadata_differences"]
                                     ["metadata_pass_is_geometry_proof"])
                elif name == "displacement":
                    self.assertIn("object_center", channels["metadata_differences"]
                                  ["recognized_difference_codes"])
                    self.assertEqual(channels["silhouette_iou"]["worst_observed_iou"], 1.)
                    self.assertEqual(channels["boundary_counts"]["status"],
                                     "no_count_difference_observed")
                    self.assertIn("sampled_surface_distance", report["review_topics"])
                elif name == "opening":
                    self.assertIn("scene_silhouette", channels["metadata_differences"]
                                  ["recognized_difference_codes"])
                    self.assertLess(channels["silhouette_iou"]["worst_observed_iou"], .8)
                    self.assertEqual(channels["boundary_counts"]["status"],
                                     "no_count_difference_observed")
                    self.assertIn("sampled_surface_distance", report["review_topics"])
                else:
                    self.assertIn("missing_reference_object",
                                  channels["metadata_differences"]["recognized_difference_codes"])
                    self.assertEqual(channels["boundary_counts"]["status"],
                                     "observed_count_difference")
                    self.assertIn("boundary_counts", report["review_topics"])

    def test_unobserved_is_explicit_and_never_exact_equivalence(self):
        result = build_glb_evidence_triage()
        self.assert_safety(result)
        self.assertEqual(set(result["unobserved_channels"]), set(result["channels"]))
        self.assertTrue(all(row["status"] == "not_measured"
                            for row in result["channels"].values()))
        one, _ = self.assembled("identical")
        self.assertFalse(one["channels"]["boundary_counts"]
                         ["same_counts_prove_same_holes"])
        self.assertFalse(one["channels"]["sampled_surface_distance"]
                         ["true_hausdorff_or_hole_location_proven"])

    def test_existing_private_ast_triage_is_only_anonymous_counts(self):
        fixture = linked_fixture.VisualExperimentTests(
            methodName="test_bound_review_separates_static_name_from_synthetic_observations")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = build_experiment_triage(fixture.visual, fixture.build())
        report = build_glb_evidence_triage(static_property_triage=source)
        self.assert_safety(report)
        props = report["channels"]["static_property_candidates"]
        self.assertEqual(props["status"], "unverified_syntax_candidates")
        self.assertGreater(props["candidate_family_count"], 0)
        self.assertFalse(props["property_effect_verified"])
        self.assertIsNone(props["selected_property"])
        private_source = json.dumps(source, sort_keys=True)
        self.assertNotEqual(private_source, json.dumps(report, sort_keys=True))
        self.assertNotIn("source_001.py", json.dumps(report))

    def test_inconsistent_comparison_counts_or_pass_fail_closed(self):
        comparison, left, right, surface = authored_case("displacement")
        for mutate in (
            lambda c: c["summary"].update(errors=0),
            lambda c: c.update(passed=True),
            lambda c: c["summary"].update(scene_silhouette_iou={"front.png": math.nan}),
            lambda c: c["evidence"].update(scene_silhouettes_compared=False),
            lambda c: c["summary"].update(scene_silhouette_iou={"front.png": True}),
        ):
            with self.subTest(mutation=str(mutate)):
                bad = copy.deepcopy(comparison)
                mutate(bad)
                with self.assertRaises(ValueError):
                    build_glb_evidence_triage(comparison=bad)
        # Never forward name- or path-bearing fields from a valid report.
        comparison["reference_source"] = "PERSONAL_FOLDER_SECRET.glb"
        comparison["candidate_source"] = "PRIVATE_MODEL.glb"
        report = build_glb_evidence_triage(comparison=comparison)
        self.assertNotIn("PERSONAL_FOLDER_SECRET", json.dumps(report))
        self.assertNotIn("PRIVATE_MODEL", json.dumps(report))

    def test_boundary_tamper_and_missing_pair_fail_closed(self):
        comparison, left, right, surface = authored_case("missing")
        for edit in (
            lambda x: x["summary"].update(boundary_edges=100),
            lambda x: x["parts"][0].update(observed_boundary=False),
            lambda x: x["parts"][0].update(part_id="../../../private"),
            lambda x: x.update(hole_locations_verified=True),
            lambda x: x["parts"][0].update(triangle_count=513),
        ):
            with self.subTest(mutation=str(edit)):
                bad = copy.deepcopy(left)
                edit(bad)
                with self.assertRaises(ValueError):
                    build_glb_evidence_triage(boundary_reference=bad,
                                              boundary_candidate=right)
        with self.assertRaises(ValueError):
            build_glb_evidence_triage(boundary_reference=left)
        self.assertEqual(build_glb_evidence_triage()["channels"]
                         ["boundary_counts"]["status"], "not_measured")

    def test_surface_skip_unknown_and_nonfinite_never_approve(self):
        _, _, _, sampled = authored_case("identical")
        for bad_mutation in (
            lambda s: s.update(status="approved"),
            lambda s: s.update(exact_surface_equivalence_verified=True),
            lambda s: s.update(symmetric_sampled_max=float("nan")),
            lambda s: s.update(symmetric_sampled_max=42.),
            lambda s: s["safety"].update(auto_approves=True),
        ):
            with self.subTest(mutation=str(bad_mutation)):
                bad = copy.deepcopy(sampled)
                bad_mutation(bad)
                with self.assertRaises(ValueError):
                    build_glb_evidence_triage(sampled_surface=bad)
        skipped = {
            "kind": "cbdk_glb_surface_review", "schema_version": 1,
            "source": "local_blender_import_aggregate_only",
            "status": "skipped", "reason": "triangle_limit",
            "surface_observation": "not_measured",
            "auto_apply": False, "complete_surface_equivalence_proven": False,
            "safety": {
                "executes_addon_code": False, "uploads_private_glb": False,
                "saves_raw_mesh_vertices": False, "changes_source_glbs": False,
            },
        }
        result = build_glb_evidence_triage(sampled_surface=skipped)
        self.assertEqual(result["channels"]["sampled_surface_distance"]["status"],
                         "not_measured")
        self.assertEqual(result["channels"]["sampled_surface_distance"]["reason"],
                         "triangle_limit")
        self.assertIn("sampled_surface_distance", result["unobserved_channels"])
        bad = dict(skipped, surface_observation="no_difference_observed_at_samples")
        with self.assertRaises(ValueError):
            build_glb_evidence_triage(sampled_surface=bad)

    def test_unknown_difference_cannot_become_user_identifying_code(self):
        comparison, *_ = authored_case("identical")
        diff = {"code": "CUSTOM_PRIVATE_SOURCE_DUMP", "severity": "info",
                "message": "secret", "metrics": {}}
        comparison["differences"].append(diff)
        comparison["summary"]["infos"] = 1
        report = build_glb_evidence_triage(comparison=comparison)
        self.assertEqual(report["channels"]["metadata_differences"]
                         ["unrecognized_difference_count"], 1)
        self.assertNotIn("CUSTOM_PRIVATE", json.dumps(report))
        self.assertNotIn("secret", json.dumps(report))

    def test_deterministic_result_independent_of_original_object_order(self):
        comparison, left, right, surface = authored_case("opening")
        first = build_glb_evidence_triage(
            comparison=comparison, boundary_reference=left,
            boundary_candidate=right, sampled_surface=surface)
        comparison = copy.deepcopy(comparison)
        comparison["differences"].reverse()
        comparison["summary"]["scene_silhouette_iou"] = dict(
            reversed(list(comparison["summary"]["scene_silhouette_iou"].items())))
        second = build_glb_evidence_triage(
            comparison=comparison, boundary_reference=left,
            boundary_candidate=right, sampled_surface=surface)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
