"""Team B R10 — safe adaptive R2 AABB bypass for densely overlapping boxes.

All cases use self-authored bounded geometry. Exact reports are compared
against forced R8 and fully unpruned R2; logs contain only aggregate timing.
"""
from __future__ import annotations

from statistics import median
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

from cbdk.glb_part_match import (
    _boundary_layout_issue, _outside_expanded_boundary_segment_box,
    _keep_r2_bbox_after_probe, suggest_spatial_part_matches,
)
from cbdk.glb_surface_distance import SurfaceDistanceError
from test_glb_match_stress_r9 import overlapping_boxes, unpruned_layout
from test_glb_match_budget_r4 import open_edge_fixture, many_rings, scaled
from test_glb_match_adversarial_r7 import split_edge_fan, slightly_perturbed_budget
from test_glb_match_determinism_r5 import float32_faces, reorder_faces
from test_glb_match_pruning_r8 import original_unpruned
from test_glb_part_match import nearly_touching_triangles, square_frame


def always_box_layout(reference, candidate, part):
    """R8's pre-R10 static AABB: no adaptive disabling (test-only)."""
    with patch("cbdk.glb_part_match._keep_r2_bbox_after_probe",
               new=lambda _rejected: True):
        return _boundary_layout_issue(reference, candidate, part, part)


def always_box_report(a, b, ref_counts, cand_counts):
    with patch("cbdk.glb_part_match._keep_r2_bbox_after_probe",
               new=lambda _rejected: True):
        return suggest_spatial_part_matches(a, b, ref_counts, cand_counts)


class R10AdaptiveBBoxTests(unittest.TestCase):
    def assert_review_only(self, report):
        self.assertEqual(report["status"], "review_only")
        self.assertIs(report["auto_apply"], False)
        self.assertIs(report["cross_file_part_identity_proven"], False)

    def test_adaptive_decision_only_changes_work_not_r2_match(self):
        for rejected in range(65):
            with self.subTest(rejected=rejected):
                self.assertEqual(_keep_r2_bbox_after_probe(rejected),
                                 rejected >= 8)
        # The R8 padded box is a necessary condition for a point to be
        # within R2 Euclidean tolerance, not an automatic success claim.
        self.assertFalse(_outside_expanded_boundary_segment_box(
            (.5, 0., 0.), (0., 0., 0.), (1., 0., 0.), .004))
        self.assertTrue(_outside_expanded_boundary_segment_box(
            (.5, .1, 0.), (0., 0., 0.), (1., 0., 0.), .004))

    def test_dense_boxes_disable_after_exactly_64_probe_checks(self):
        a, b, part = overlapping_boxes(128)
        before = unpruned_layout(a, b, part)
        static = always_box_layout(a, b, part)
        self.assertEqual(static, before)
        with patch("cbdk.glb_part_match._outside_expanded_boundary_segment_box",
                   wraps=_outside_expanded_boundary_segment_box) as spy:
            actual = _boundary_layout_issue(a, b, part, part)
        self.assertEqual(actual, before)
        self.assertEqual(spy.call_count, 64)
        self.assertEqual(actual, "boundary_spatial_layout_mismatch")

    def test_sparse_256_edge_prefilter_stays_on(self):
        a = open_edge_fixture(256)
        b = slightly_perturbed_budget(a)
        with patch("cbdk.glb_part_match._outside_expanded_boundary_segment_box",
                   wraps=_outside_expanded_boundary_segment_box) as spy:
            current = suggest_spatial_part_matches(a, b, [86], [86])
        self.assertGreater(spy.call_count, 64,
                           "R8 pruning should stay enabled on sparse edges")
        self.assertEqual(current, original_unpruned(a, b, [86], [86]))
        self.assertEqual(current, always_box_report(a, b, [86], [86]))
        self.assertEqual(current["reference_parts"][0]["status"], "suggested")
        self.assert_review_only(current)

    def test_changes_to_real_holes_and_retriangulation_preserve_reports(self):
        cases = (
            (square_frame(), reorder_faces(square_frame(
                flip_diagonal=True)), "suggested"),
            (square_frame(), square_frame(opening_x=.24), "ambiguous"),
            (square_frame(), square_frame(opening_half_width=.5), "ambiguous"),
            (split_edge_fan(.30), reorder_faces(split_edge_fan(.70)),
             "suggested"),
            (split_edge_fan(.30), split_edge_fan(.70, indentation=.03),
             "ambiguous"),
            (float32_faces(split_edge_fan(.25)),
             float32_faces(split_edge_fan(.75, indentation=.0001)),
             "suggested"),
        )
        for ref, cand, expected in cases:
            with self.subTest(expected=expected, faces=len(ref)):
                counts = [len(ref)]
                self.assertEqual(counts, [len(cand)])
                current = suggest_spatial_part_matches(
                    ref, cand, counts, counts)
                self.assertEqual(current, always_box_report(
                    ref, cand, counts, counts))
                self.assertEqual(current, original_unpruned(
                    ref, cand, counts, counts))
                self.assertEqual(current["reference_parts"][0]["status"],
                                 expected)
                self.assert_review_only(current)

    def test_r3_gap_contact_and_zero_length_guard_not_bypassed(self):
        gap = nearly_touching_triangles()
        touching = nearly_touching_triangles(touch=True)
        for a, b in ((gap, touching), (touching, gap)):
            current = suggest_spatial_part_matches(a, b, [2], [2])
            self.assertEqual(current, original_unpruned(a, b, [2], [2]))
            self.assertEqual(current, always_box_report(a, b, [2], [2]))
            self.assertEqual(current["reference_parts"][0]["status"],
                             "ambiguous")
            self.assertEqual(current["reference_parts"][0]
                             ["topology_review_reasons"],
                             ["boundary_component_count_mismatch"])
            self.assert_review_only(current)
        part = {"center": (0., 0., 0.), "size": (1., 1., 0.)}
        zero = [(1, 0., 0., 0., 0., 0., 0.)]
        self.assertEqual(_boundary_layout_issue(zero, zero, part, part),
                         "boundary_spatial_layout_mismatch")
        self.assertEqual(always_box_layout(zero, zero, part),
                         "boundary_spatial_layout_mismatch")

    def test_limits_255_256_257_edges_64parts_512faces_and_scale(self):
        for edges in (255, 256, 257):
            with self.subTest(edges=edges):
                a = open_edge_fixture(edges)
                b = reorder_faces(a)
                counts = [len(a)]
                current = suggest_spatial_part_matches(a, b, counts, counts)
                self.assertEqual(current, always_box_report(
                    a, b, counts, counts))
                self.assertEqual(current, original_unpruned(
                    a, b, counts, counts))
                self.assertEqual(current["reference_parts"][0]["status"],
                                 "ambiguous" if edges == 257 else "suggested")
                if edges == 257:
                    self.assertEqual(current["reference_parts"][0]
                                     ["topology_review_reasons"],
                                     ["boundary_layout_budget_exceeded"])
                self.assert_review_only(current)
        groups = many_rings()
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                copy = [[list(face) for face in group] for group in groups]
                if duplicate:
                    copy[1] = [list(face) for face in copy[0]]
                a = [face for group in copy for face in group]
                b = [face for group in reversed(copy)
                     for face in reorder_faces(group)]
                counts = [8]*64
                self.assertEqual(len(a), 512)
                current = suggest_spatial_part_matches(a, b, counts, counts)
                self.assertEqual(current, always_box_report(
                    a, b, counts, counts))
                self.assertEqual(current, original_unpruned(
                    a, b, counts, counts))
                self.assertEqual(current["reference_parts"][0]["status"],
                                 "ambiguous" if duplicate else "suggested")
                self.assert_review_only(current)
        for factor in (.01, 1., 100.):
            a = scaled(square_frame(), factor)
            b = scaled(square_frame(opening_x=.24), factor)
            current = suggest_spatial_part_matches(a, b, [8], [8])
            self.assertEqual(current, always_box_report(a, b, [8], [8]))
            self.assertEqual(current, original_unpruned(a, b, [8], [8]))
            self.assertEqual(current["reference_parts"][0]["status"],
                             "ambiguous")
        too_many = open_edge_fixture(255)*7
        with self.assertRaises(SurfaceDistanceError):
            suggest_spatial_part_matches(
                too_many, too_many, [len(too_many)], [len(too_many)])
        more_parts = [group[0] for group in groups]+[groups[0][1]]
        with self.assertRaises(ValueError):
            suggest_spatial_part_matches(
                more_parts, more_parts, [1]*65, [1]*65)

    def test_dense_and_sparse_warmed_r8_vs_r10_medians(self):
        """Both paired cases: timing is evidence, not a flaky CI threshold."""
        dense_a, dense_b, dense_part = overlapping_boxes(128)
        sparse_a = open_edge_fixture(256)
        sparse_b = slightly_perturbed_budget(sparse_a)
        scenarios = (
            ("dense128",
             lambda: always_box_layout(dense_a, dense_b, dense_part),
             lambda: _boundary_layout_issue(
                 dense_a, dense_b, dense_part, dense_part)),
            ("sparse256",
             lambda: always_box_report(sparse_a, sparse_b, [86], [86]),
             lambda: suggest_spatial_part_matches(
                 sparse_a, sparse_b, [86], [86])),
        )
        for name, static, adaptive in scenarios:
            static()
            adaptive()
            static_times, adaptive_times = [], []
            for _ in range(3):
                start = perf_counter()
                old_result = static()
                static_times.append((perf_counter() - start)*1000.)
                start = perf_counter()
                new_result = adaptive()
                adaptive_times.append((perf_counter() - start)*1000.)
                self.assertEqual(old_result, new_result)
            tracemalloc.start()
            try:
                adaptive()
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            self.assertLess(peak, 32*1024*1024)
            previous, current = median(static_times), median(adaptive_times)
            print("CBDK_R10_ADAPTIVE "
                  f"case={name} r8_ms={previous:.3f} "
                  f"r10_ms={current:.3f} speedup_x={previous/current:.2f} "
                  f"peak_kib={peak//1024} samples=3")


if __name__ == "__main__":
    unittest.main()
