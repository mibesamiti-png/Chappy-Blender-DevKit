"""Team B R6: collision-free, bounded exact-contour shortcut evidence.

The R2 nearest-segment comparison is forced by an isolated test patch to
check *identical results* against the new exact equality path; this patch
does not change production behavior or expose source geometry to reports.
"""
from __future__ import annotations

from statistics import median
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

import cbdk.glb_part_match as matcher
from cbdk.glb_part_match import (
    _exact_undirected_contour_signature, suggest_spatial_part_matches,
)
from cbdk.glb_surface_distance import SurfaceDistanceError
from test_glb_match_budget_r4 import open_edge_fixture, many_rings, scaled
from test_glb_match_determinism_r5 import (
    float32_faces, reorder_faces, shifted_faces,
)
from test_glb_part_match import square_frame, nearly_touching_triangles


def baseline_scan(reference, candidate, left, right):
    """Force original R2 distance scan without altering the matcher."""
    with patch(
        "cbdk.glb_part_match._exact_undirected_contour_signature",
        side_effect=lambda _segments: object(),
    ):
        return suggest_spatial_part_matches(reference, candidate, left, right)


class ExactContourFastPathTests(unittest.TestCase):

    def test_canonical_signature_is_undirected_order_free_and_collision_free(self):
        p, q, r = (0., 0., 0.), (1., 0., 0.), (0., 1., 0.)
        original = [(p, q), (q, r), (r, p)]
        reverse = [(q, p), (p, r), (r, q)]
        self.assertEqual(_exact_undirected_contour_signature(original),
                         _exact_undirected_contour_signature(reverse))
        self.assertNotEqual(_exact_undirected_contour_signature(original),
                            _exact_undirected_contour_signature(original + [(p, q)]))
        moved = [(p, q), (q, (0., 1.000001, 0.)), (r, p)]
        self.assertNotEqual(_exact_undirected_contour_signature(original),
                            _exact_undirected_contour_signature(moved))

    def test_255_256_face_permutation_fast_path_matches_original_r2_scan(self):
        for edges in (255, 256):
            with self.subTest(open_edges=edges):
                reference = open_edge_fixture(edges)
                candidate = reorder_faces(reference)
                counts = [len(reference)]
                with patch(
                    "cbdk.glb_part_match._exact_undirected_contour_signature",
                    wraps=_exact_undirected_contour_signature,
                ) as signature:
                    accelerated = suggest_spatial_part_matches(
                        reference, candidate, counts, counts)
                self.assertEqual(signature.call_count, 2,
                                 "Exact scan must check both contours")
                self.assertEqual(accelerated, baseline_scan(
                    reference, candidate, counts, counts))
                self.assertEqual(accelerated["reference_parts"][0]["status"],
                                 "suggested")
                self.assertEqual(accelerated["reference_parts"][0]
                                 ["topology_review_reasons"], [])
                self.assertFalse(accelerated["auto_apply"])
                self.assertFalse(accelerated["cross_file_part_identity_proven"])

    def test_over_256_budget_skips_signature_and_remains_ambiguous(self):
        faces = open_edge_fixture(257)
        with patch(
            "cbdk.glb_part_match._exact_undirected_contour_signature",
            side_effect=AssertionError("budget should reject before signature"),
        ):
            result = suggest_spatial_part_matches(
                faces, reorder_faces(faces), [87], [87])
        self.assertEqual(result["reference_parts"][0]["status"], "ambiguous")
        self.assertEqual(result["reference_parts"][0]
                         ["topology_review_reasons"],
                         ["boundary_layout_budget_exceeded"])
        self.assertEqual(result["unpaired_candidate_part_ids"], ["part_001"])

    def test_r3_component_guard_still_runs_for_exact_equal_boundaries(self):
        faces = nearly_touching_triangles(touch=True)
        real = matcher._observed_boundary_component_count
        with patch("cbdk.glb_part_match._observed_boundary_component_count",
                   wraps=real) as counter:
            matched = suggest_spatial_part_matches(
                faces, reorder_faces(faces), [2], [2])
        self.assertEqual(counter.call_count, 2)
        self.assertEqual(matched["reference_parts"][0]["status"], "suggested")
        self.assertEqual(matched, baseline_scan(
            faces, reorder_faces(faces), [2], [2]))

    def test_negative_contours_and_jitter_match_original_conservative_results(self):
        ref = square_frame()
        scenarios = (
            ("retessellate", square_frame(flip_diagonal=True)),
            ("changed_hole", square_frame(opening_x=.24)),
            ("resized_hole", square_frame(opening_half_width=.5)),
            ("micro_jitter", square_frame(opening_x=.00004)),
            ("float32", float32_faces(ref)),
            ("float32_shift", shifted_faces(float32_faces(ref), .0001)),
        )
        for label, sample in scenarios:
            with self.subTest(case=label):
                candidate = reorder_faces(sample)
                current = suggest_spatial_part_matches(ref, candidate, [8], [8])
                old = baseline_scan(ref, candidate, [8], [8])
                self.assertEqual(current, old)
                row = current["reference_parts"][0]
                if label in ("changed_hole", "resized_hole"):
                    self.assertEqual(row["status"], "ambiguous")
                    self.assertEqual(row["topology_review_reasons"],
                                     ["boundary_spatial_layout_mismatch"])
                else:
                    self.assertEqual(row["status"], "suggested")
                    self.assertEqual(row["topology_review_reasons"], [])
                self.assertFalse(current["auto_apply"])
                self.assertFalse(current["cross_file_part_identity_proven"])

    def test_r3_gap_contact_both_directions_preserves_ambiguity(self):
        apart = nearly_touching_triangles()
        touch = nearly_touching_triangles(touch=True)
        for reference, candidate in ((apart, touch), (touch, apart)):
            for changed in (candidate, reorder_faces(candidate)):
                with self.subTest(reference_touch=reference is touch,
                                  reordered=changed is not candidate):
                    current = suggest_spatial_part_matches(
                        reference, changed, [2], [2])
                    self.assertEqual(current, baseline_scan(
                        reference, changed, [2], [2]))
                    self.assertEqual(current["reference_parts"][0]["status"],
                                     "ambiguous")
                    self.assertEqual(current["reference_parts"][0]
                                     ["topology_review_reasons"],
                                     ["boundary_component_count_mismatch"])

    def test_uniform_scale_and_64_part_permutation_preserves_review_only(self):
        for factor in (.01, 1., 100.):
            with self.subTest(scale=factor):
                reference = scaled(square_frame(), factor)
                candidate = reorder_faces(scaled(
                    square_frame(flip_diagonal=True), factor))
                actual = suggest_spatial_part_matches(
                    reference, candidate, [8], [8])
                self.assertEqual(actual, baseline_scan(
                    reference, candidate, [8], [8]))
                self.assertEqual(actual["reference_parts"][0]["status"],
                                 "suggested")
        groups = many_rings()
        reference = [face for part in groups for face in part]
        candidate = [face for part in reversed(groups)
                     for face in reorder_faces(part)]
        result = suggest_spatial_part_matches(
            reference, candidate, [8] * 64, [8] * 64)
        self.assertEqual(result["reference_parts"][0]["candidate_part_ids"],
                         ["part_064"])
        self.assertEqual(result["reference_parts"][-1]["candidate_part_ids"],
                         ["part_001"])
        self.assertTrue(all(row["status"] == "suggested" for row
                            in result["reference_parts"]))
        self.assertFalse(result["auto_apply"])
        self.assertFalse(result["cross_file_part_identity_proven"])

    def test_invalid_513_faces_or_65_parts_still_fail_closed(self):
        original = open_edge_fixture(255)
        excess = original * 7  # >512 validated triangles
        with self.assertRaises(SurfaceDistanceError):
            suggest_spatial_part_matches(excess, excess,
                                         [len(excess)], [len(excess)])
        groups = many_rings()
        reference = [part[0] for part in groups] + [groups[0][1]]
        with self.assertRaises(ValueError):
            suggest_spatial_part_matches(
                reference, reference, [1] * 65, [1] * 65)

    def test_measured_256_edge_speedup_and_peak_are_bounded(self):
        reference = open_edge_fixture(256)
        candidate = reorder_faces(reference)
        counts = [86]
        # Warm both paths before aggregate measurements. No CI wall-time
        # requirement: comparisons use matched snapshots, not timing.
        baseline_scan(reference, candidate, counts, counts)
        suggest_spatial_part_matches(reference, candidate, counts, counts)
        old_times, fast_times = [], []
        for _ in range(3):
            t0 = perf_counter()
            old = baseline_scan(reference, candidate, counts, counts)
            old_times.append((perf_counter() - t0) * 1000)
            t0 = perf_counter()
            fast = suggest_spatial_part_matches(
                reference, candidate, counts, counts)
            fast_times.append((perf_counter() - t0) * 1000)
            self.assertEqual(fast, old)
        tracemalloc.start()
        try:
            suggest_spatial_part_matches(reference, candidate, counts, counts)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 32 * 1024 * 1024)
        prev, curr = median(old_times), median(fast_times)
        self.assertGreater(prev, 0.)
        self.assertGreater(curr, 0.)
        print(f"CBDK_R6_EXACT_BOUNDARY_256 baseline_median_ms={prev:.3f} "
              f"fast_median_ms={curr:.3f} speedup_x={prev/curr:.2f} "
              f"peak_kib={peak//1024} samples=3")


if __name__ == "__main__":
    unittest.main()
