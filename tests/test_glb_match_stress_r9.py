"""Team B R9: adversarial R8 AABB pruning limits and parity evidence.

Only self-authored synthetic contours. Log aggregate performance/call counts,
never source paths, vertices, segment coordinates or user GLB content.
"""
from __future__ import annotations

from itertools import product
from statistics import median
from time import perf_counter
import math
import tracemalloc
import unittest
from unittest.mock import patch

from cbdk.glb_boundary_audit import boundary_audit
from cbdk.glb_part_match import (
    BOUNDARY_LAYOUT_RELATIVE_TOLERANCE,
    MAX_LAYOUT_BOUNDARY_EDGES,
    _boundary_layout_issue,
    _outside_expanded_boundary_segment_box,
    suggest_spatial_part_matches,
)
from cbdk.glb_surface_distance import SurfaceDistanceError
from test_glb_match_budget_r4 import many_rings, open_edge_fixture
from test_glb_match_determinism_r5 import float32_faces, reorder_faces
from test_glb_match_adversarial_r7 import split_edge_fan
from test_glb_match_pruning_r8 import original_unpruned
from test_glb_part_match import nearly_touching_triangles, square_frame


def unpruned_layout(ref_lines, cand_lines, part):
    """Run the original R2 scan without only the R8 box prefilter."""
    # Use a plain function rather than a Mock object: a Mock executed for
    # each of ~49k probes biases an aggregate timing comparison drastically.
    with patch("cbdk.glb_part_match._outside_expanded_boundary_segment_box",
               new=lambda *_args: False):
        return _boundary_layout_issue(ref_lines, cand_lines, part, part)


def overlapping_boxes(num=128):
    """AABB-hostile segments: long diagonal boxes envelop horizontal probes.

    The final candidate segment is horizontally compatible with all source
    probes, after many near-box but physically distant diagonal candidates.
    The reverse direction must notice the added diagonal contours.
    """
    if num < 2 or num > MAX_LAYOUT_BOUNDARY_EDGES:
        raise ValueError("Synthetic contour count out of R2 budget")
    source = []
    target = []
    for i in range(num):
        begin = .30 + .001 * i
        source.append((1, begin, .12, 0., begin + .08, .12, 0.))
        if i < num - 1:
            target.append((1, 0., 0., 0., 1., 1., 0.))
    target.append((1, .20, .12, 0., .80, .12, 0.))
    part = {"center": (0., 0., 0.), "size": (1., 1., 0.)}
    return source, target, part


class R9HostileFallbackTests(unittest.TestCase):
    def assert_review_only(self, result):
        self.assertEqual(result["status"], "review_only")
        self.assertIs(result["auto_apply"], False)
        self.assertIs(result["cross_file_part_identity_proven"], False)

    def test_strict_bbox_padding_never_culls_an_actual_within_tolerance_point(self):
        """Check near-threshold 3D boxes incl. reversed/zero-length segments."""
        tol = BOUNDARY_LAYOUT_RELATIVE_TOLERANCE
        margin = 2 * tol
        segment_pairs = (
            ((0., 0., 0.), (1., 0., 0.)),
            ((0., 0., 0.), (1., 1., 1.)),
            ((-1., 2., -.5), (-1., -1., -.5)),
            ((.03, .04, 0.), (.03, .04, 0.)),
        )
        for start, end in segment_pairs:
            for first, last in ((start, end), (end, start)):
                for factor in (0., .125, .5, .875, 1.):
                    center = tuple(
                        first[k] + factor * (last[k] - first[k])
                        for k in range(3))
                    for offset in product((-1., 0., 1.), repeat=3):
                        # Euclidean distance <= tolerance, including just
                        # inside the tolerance sphere along one axis.
                        delta = tuple(tol * (1. - 1e-10) * c / math.sqrt(3.)
                                      for c in offset)
                        point = tuple(center[k] + delta[k] for k in range(3))
                        self.assertFalse(
                            _outside_expanded_boundary_segment_box(
                                point, first, last, margin))
        self.assertTrue(_outside_expanded_boundary_segment_box(
            (0., margin*4, 0.), (0., 0., 0.), (1., 0., 0.), margin))

    def test_box_overlap_reduces_pruning_but_preserves_old_r2_reason(self):
        source, target, part = overlapping_boxes(128)
        assert len(source) == len(target) == 128
        original = unpruned_layout(source, target, part)
        self.assertEqual(original, "boundary_spatial_layout_mismatch")
        counts = {"seen": 0, "removed": 0}
        actual = _outside_expanded_boundary_segment_box

        def observed(point, start, end, margin):
            counts["seen"] += 1
            far = actual(point, start, end, margin)
            counts["removed"] += int(far)
            return far

        # R10 changes the default by adaptively stopping low-selectivity
        # AABB calls. Keep this R9 regression about the *static R8 filter*
        # so the historical high-overlap cost remains independently tested.
        with patch("cbdk.glb_part_match._keep_r2_bbox_after_probe",
                   new=lambda _rejected: True), \
             patch("cbdk.glb_part_match._outside_expanded_boundary_segment_box",
                   side_effect=observed):
            pruned = _boundary_layout_issue(source, target, part, part)
        self.assertEqual(pruned, original)
        self.assertGreater(counts["seen"], 10000)
        # Most candidates on the long-diagonal forward scan overlap the
        # horizontal probes' AABBs; the box filter cannot prune them.
        self.assertLess(counts["removed"] / counts["seen"], .2)
        print("CBDK_R9_DENSE_AABB "
              f"probes={counts['seen']} "
              f"rejected={counts['removed']} "
              f"rejected_pct={100*counts['removed']/counts['seen']:.2f}")

    def test_255_256_257_boundary_switch_preserves_original_and_budget(self):
        for edges in (255, 256, 257):
            with self.subTest(edges=edges):
                faces = open_edge_fixture(edges)
                candidate = reorder_faces(faces)
                result = suggest_spatial_part_matches(
                    faces, candidate, [len(faces)], [len(candidate)])
                self.assertEqual(result, original_unpruned(
                    faces, candidate, [len(faces)], [len(candidate)]))
                row = result["reference_parts"][0]
                self.assertEqual(row["status"],
                                 "ambiguous" if edges == 257 else "suggested")
                if edges == 257:
                    self.assertEqual(row["topology_review_reasons"],
                                     ["boundary_layout_budget_exceeded"])
                self.assert_review_only(result)

    def test_float32_threshold_and_resegmented_notches_keep_full_report(self):
        reference = float32_faces(split_edge_fan(.30))
        for indentation in (0., .00001, .0001, .03):
            candidate = float32_faces(reorder_faces(
                split_edge_fan(.70, indentation=indentation)))
            with self.subTest(notch=indentation):
                current = suggest_spatial_part_matches(
                    reference, candidate, [5], [5])
                self.assertEqual(current, original_unpruned(
                    reference, candidate, [5], [5]))
                self.assertEqual(current, suggest_spatial_part_matches(
                    reference, candidate, [5], [5]))
                if indentation == .03:
                    self.assertEqual(current["reference_parts"][0]["status"],
                                     "ambiguous")
                self.assert_review_only(current)

    def test_r3_independent_contact_and_near_weld_stay_conservative(self):
        apart = float32_faces(nearly_touching_triangles())
        touch = float32_faces(nearly_touching_triangles(touch=True))
        for reference, candidate in ((apart, touch), (touch, apart)):
            current = suggest_spatial_part_matches(
                reference, candidate, [2], [2])
            self.assertEqual(current, original_unpruned(
                reference, candidate, [2], [2]))
            self.assertEqual(current["reference_parts"][0]["status"],
                             "ambiguous")
            self.assertEqual(current["reference_parts"][0]
                             ["topology_review_reasons"],
                             ["boundary_component_count_mismatch"])
            self.assert_review_only(current)
        small = [[(0., 0., 0.), (2e-8, 0., 0.), (0., 1., 0.)]]
        self.assertEqual(boundary_audit(small, [1])["parts"][0]
                         ["weld_collapsed_triangles"], 1)
        result = suggest_spatial_part_matches(small, small, [1], [1])
        self.assertEqual(result, original_unpruned(small, small, [1], [1]))
        self.assertEqual(result["reference_parts"][0]["status"], "ambiguous")
        self.assert_review_only(result)

    def test_64_parts_512_faces_and_input_fail_closed(self):
        groups = many_rings()
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                parts = [list(group) for group in groups]
                if duplicate:
                    parts[1] = [list(face) for face in parts[0]]
                reference = [face for group in parts for face in group]
                candidate = [face for group in reversed(parts)
                             for face in reorder_faces(group)]
                counts = [8] * 64
                self.assertEqual(len(reference), 512)
                actual = suggest_spatial_part_matches(
                    reference, candidate, counts, counts)
                self.assertEqual(actual, original_unpruned(
                    reference, candidate, counts, counts))
                self.assertEqual(actual["reference_parts"][0]["status"],
                                 "ambiguous" if duplicate else "suggested")
                self.assert_review_only(actual)
        too_many = open_edge_fixture(255) * 7
        with self.assertRaises(SurfaceDistanceError):
            suggest_spatial_part_matches(
                too_many, too_many, [len(too_many)], [len(too_many)])
        sixty_five = [group[0] for group in groups] + [groups[0][1]]
        with self.assertRaises(ValueError):
            suggest_spatial_part_matches(
                sixty_five, sixty_five, [1] * 65, [1] * 65)

    def test_dense_aabb_nonbenefit_benchmark_is_memory_bounded(self):
        """Benchmark only; do not fail CI on runner-dependent timing."""
        ref, cand, part = overlapping_boxes(128)

        def forced_static_r8():
            # Observe the original R8 design rather than the new R10
            # adaptive selector. This also preserves the R9 log's meaning.
            with patch("cbdk.glb_part_match._keep_r2_bbox_after_probe",
                       new=lambda _rejected: True):
                return _boundary_layout_issue(ref, cand, part, part)

        unpruned_layout(ref, cand, part)
        forced_static_r8()
        old_times, new_times = [], []
        for _ in range(2):
            t0 = perf_counter()
            old = unpruned_layout(ref, cand, part)
            old_times.append((perf_counter() - t0) * 1000.)
            t0 = perf_counter()
            new = forced_static_r8()
            new_times.append((perf_counter() - t0) * 1000.)
            self.assertEqual(new, old)
        tracemalloc.start()
        try:
            forced_static_r8()
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 32 * 1024 * 1024)
        before, after = median(old_times), median(new_times)
        print("CBDK_R9_DENSE_TIMING "
              f"unpruned_median_ms={before:.3f} "
              f"pruned_median_ms={after:.3f} "
              f"speedup_x={before/after:.2f} "
              f"peak_kib={peak//1024} samples=2")


if __name__ == "__main__":
    unittest.main()
