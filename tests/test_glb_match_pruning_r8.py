"""Team B R8: proof-oriented bounded pruning of R2 nonexact contour scan.

Self-authored triangle meshes only. Results contain anonymous candidate IDs,
classification and aggregate synthetic timing/memory, never real GLB data.
"""
from __future__ import annotations

from itertools import product
from statistics import median
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

from cbdk.glb_boundary_audit import boundary_audit
from cbdk.glb_part_match import (
    BOUNDARY_LAYOUT_RELATIVE_TOLERANCE,
    _outside_expanded_boundary_segment_box,
    suggest_spatial_part_matches,
)
from cbdk.glb_surface_distance import SurfaceDistanceError
from test_glb_match_budget_r4 import many_rings, open_edge_fixture, scaled
from test_glb_match_determinism_r5 import float32_faces, reorder_faces
from test_glb_match_adversarial_r7 import split_edge_fan, slightly_perturbed_budget
from test_glb_part_match import nearly_touching_triangles, square_frame


def original_unpruned(reference, candidate, ref_counts, cand_counts):
    """Force the pre-R8 complete R2 closest-distance loop for parity tests.

    A simple predicate with the same call signature but always False skips
    *only* the new broad-phase reject. The strict exact R6 shortcut still
    operates as before on identical inputs.
    """
    with patch("cbdk.glb_part_match._outside_expanded_boundary_segment_box",
               new=lambda *_args: False):
        return suggest_spatial_part_matches(
            reference, candidate, ref_counts, cand_counts)


class R8BoundedPruningTests(unittest.TestCase):

    def assert_review_only(self, result):
        self.assertEqual(result["status"], "review_only")
        self.assertIs(result["auto_apply"], False)
        self.assertIs(result["cross_file_part_identity_proven"], False)

    def test_analytic_bbox_never_excludes_point_within_true_distance_tolerance(self):
        """Euclidean <=tol implies each axis is <=tol from segment bounds."""
        tol = BOUNDARY_LAYOUT_RELATIVE_TOLERANCE
        self.assertGreater(tol, 0.)
        margin = tol * 2.
        examples = (
            ((0., 0., 0.), (1., 0., 0.)),
            ((-1., 2., -.25), (-1., -1., -.25)),
            ((0., 0., 0.), (1., 1., 1.)),
            ((.02, .03, 0.), (.02, .03, 0.)),
        )
        for start, end in examples:
            for t in (0., .125, .5, .875, 1.):
                closest = tuple(start[i] + t*(end[i]-start[i])
                                for i in range(3))
                # Worst 3-axis offset norm < tol even at diagonal corners.
                for shift in product((-.49*tol, 0., .49*tol), repeat=3):
                    point = tuple(closest[i] + shift[i] for i in range(3))
                    self.assertFalse(
                        _outside_expanded_boundary_segment_box(
                            point, start, end, margin),
                        "a true within-tolerance point cannot be excluded",
                    )

    def test_far_boxes_rejected_and_near_boxes_left_to_exact_r2(self):
        margin = BOUNDARY_LAYOUT_RELATIVE_TOLERANCE*2
        a, b = (-1., 0., 0.), (1., 0., 0.)
        self.assertTrue(_outside_expanded_boundary_segment_box(
            (0., margin * 5, 0.), a, b, margin))
        self.assertFalse(_outside_expanded_boundary_segment_box(
            (0., margin / 4, 0.), a, b, margin))
        self.assertFalse(_outside_expanded_boundary_segment_box(
            (0., margin * .99, 0.), b, a, margin))
        # The prefilter is deliberately NOT itself a match validator.
        self.assertFalse(_outside_expanded_boundary_segment_box(
            (0., margin * .75, 0.), a, b, margin))

    def test_notches_collinear_split_and_retriangulation_equal_original_r2(self):
        cases = (
            ("split_equal_outline", split_edge_fan(.30),
             reorder_faces(split_edge_fan(.70)), "suggested", []),
            ("notch_mismatch", split_edge_fan(.30),
             reorder_faces(split_edge_fan(.70, indentation=.03)),
             "ambiguous", ["boundary_spatial_layout_mismatch"]),
            ("float32_small_notch", float32_faces(split_edge_fan(.25)),
             float32_faces(reorder_faces(split_edge_fan(
                 .75, indentation=.0001))), "suggested", []),
            ("different_aperture", square_frame(),
             square_frame(opening_x=.24), "ambiguous",
             ["boundary_spatial_layout_mismatch"]),
            ("same_contour_retessellate", square_frame(),
             reorder_faces(square_frame(flip_diagonal=True)), "suggested", []),
        )
        for name, ref, cand, status, reasons in cases:
            with self.subTest(case=name):
                counts = [len(ref)]
                self.assertEqual(len(ref), len(cand))
                current = suggest_spatial_part_matches(
                    ref, cand, counts, counts)
                original = original_unpruned(ref, cand, counts, counts)
                self.assertEqual(current, original)
                self.assertEqual(current["reference_parts"][0]["status"], status)
                self.assertEqual(current["reference_parts"][0]
                                 ["topology_review_reasons"], reasons)
                self.assert_review_only(current)

    def test_r3_point_contact_guard_not_hidden_by_box_pruning(self):
        apart = float32_faces(nearly_touching_triangles())
        touching = float32_faces(nearly_touching_triangles(touch=True))
        for a, b in ((apart, touching), (touching, apart)):
            for cand in (b, reorder_faces(b)):
                with self.subTest(contact=a is touching, reverse=cand is not b):
                    current = suggest_spatial_part_matches(a, cand, [2], [2])
                    self.assertEqual(current, original_unpruned(a, cand, [2], [2]))
                    self.assertEqual(current["reference_parts"][0]
                                     ["topology_review_reasons"],
                                     ["boundary_component_count_mismatch"])
                    self.assertEqual(current["reference_parts"][0]["status"],
                                     "ambiguous")
                    self.assert_review_only(current)

    def test_255_256_257_budget_and_changed_nonexact_full_scan_parity(self):
        for edges in (255, 256, 257):
            with self.subTest(edges=edges):
                reference = open_edge_fixture(edges)
                changed = (slightly_perturbed_budget(reference)
                           if edges == 256 else reorder_faces(reference))
                counts = [len(reference)]
                with patch(
                    "cbdk.glb_part_match._outside_expanded_boundary_segment_box",
                    wraps=_outside_expanded_boundary_segment_box,
                ) as spy:
                    result = suggest_spatial_part_matches(
                        reference, changed, counts, counts)
                self.assertEqual(result, original_unpruned(
                    reference, changed, counts, counts))
                self.assertEqual(result["reference_parts"][0]["status"],
                                 "ambiguous" if edges == 257 else "suggested")
                if edges == 257:
                    self.assertEqual(spy.call_count, 0)
                    self.assertEqual(result["reference_parts"][0]
                                     ["topology_review_reasons"],
                                     ["boundary_layout_budget_exceeded"])
                elif edges == 256:
                    self.assertGreater(spy.call_count, 100)
                self.assert_review_only(result)

    def test_64_parts_512_faces_reorder_and_duplicate_motifs(self):
        groups = many_rings()
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                copy = [list(part) for part in groups]
                if duplicate:
                    copy[1] = [list(face) for face in copy[0]]
                ref = [face for part in copy for face in part]
                cand = [face for part in reversed(copy)
                        for face in reorder_faces(part)]
                counts = [8]*64
                self.assertEqual(len(ref), 512)
                current = suggest_spatial_part_matches(ref, cand, counts, counts)
                original = original_unpruned(ref, cand, counts, counts)
                self.assertEqual(current, original)
                self.assertEqual(current["reference_parts"][0]["status"],
                                 "ambiguous" if duplicate else "suggested")
                self.assert_review_only(current)

    def test_uniform_scales_and_limits_preserve_acceptance(self):
        for factor in (.01, 1., 100.):
            with self.subTest(scale=factor):
                ref = scaled(square_frame(), factor)
                changed = scaled(square_frame(opening_x=.24), factor)
                result = suggest_spatial_part_matches(ref, changed, [8], [8])
                self.assertEqual(result, original_unpruned(
                    ref, changed, [8], [8]))
                self.assertEqual(result["reference_parts"][0]["status"], "ambiguous")
        invalid = open_edge_fixture(255)*7
        with self.assertRaises(SurfaceDistanceError):
            suggest_spatial_part_matches(invalid, invalid,
                                         [len(invalid)], [len(invalid)])
        groups = many_rings()
        sixty_five = [group[0] for group in groups]+[groups[0][1]]
        with self.assertRaises(ValueError):
            suggest_spatial_part_matches(sixty_five, sixty_five,
                                         [1]*65, [1]*65)

    def test_nonexact_256_edge_warmed_speed_and_memory(self):
        reference = open_edge_fixture(256)
        candidate = slightly_perturbed_budget(reference)
        self.assertEqual(
            boundary_audit(candidate, [86])["parts"][0]["boundary_edges"], 256)
        original_unpruned(reference, candidate, [86], [86])
        suggest_spatial_part_matches(reference, candidate, [86], [86])
        before, after = [], []
        for _ in range(3):
            t0 = perf_counter()
            baseline = original_unpruned(reference, candidate, [86], [86])
            before.append((perf_counter()-t0)*1000.)
            t0 = perf_counter()
            improved = suggest_spatial_part_matches(
                reference, candidate, [86], [86])
            after.append((perf_counter()-t0)*1000.)
            self.assertEqual(improved, baseline)
        tracemalloc.start()
        try:
            suggest_spatial_part_matches(reference, candidate, [86], [86])
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 32*1024*1024)
        before_ms, after_ms = median(before), median(after)
        self.assertGreater(before_ms, 0.)
        self.assertGreater(after_ms, 0.)
        print("CBDK_R8_NONEXACT_256 "
              f"unpruned_median_ms={before_ms:.3f} "
              f"pruned_median_ms={after_ms:.3f} "
              f"speedup_x={before_ms/after_ms:.2f} "
              f"peak_kib={peak//1024} samples=3")


if __name__ == "__main__":
    unittest.main()
