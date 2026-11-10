"""Team B R7: adversarial review-only GLB contour fast-path checks.

Fixtures are CBDK-owned triangle soups. No private geometry, file paths,
per-segment coordinates, or source-identifying contents enter reports/logs.
"""
from __future__ import annotations

from statistics import median
from time import perf_counter
import tracemalloc
import unittest
from unittest.mock import patch

import cbdk.glb_part_match as matcher
from cbdk.glb_boundary_audit import boundary_audit, local_boundary_segments
from cbdk.glb_part_match import (
    _boundary_layout_issue, _exact_undirected_contour_signature,
    suggest_spatial_part_matches,
)
from cbdk.glb_surface_distance import SurfaceDistanceError
from test_glb_part_match import nearly_touching_triangles
from test_glb_match_budget_r4 import many_rings, open_edge_fixture
from test_glb_match_determinism_r5 import float32_faces, reorder_faces
from test_glb_match_fastpath_r6 import baseline_scan


def split_edge_fan(split_at=.30, indentation=0.):
    """Five triangles with five contour edges and fixed 1x1 outer bounds.

    Changing the vertex division along the flat bottom side does not
    change the perimeter. Moving that vertex inward creates a real
    inward notch while preserving part center, extent and face count.
    """
    loop = [(0., 0., 0.), (split_at, indentation, 0.),
            (1., 0., 0.), (1., 1., 0.), (0., 1., 0.)]
    center = (.5, .5, 0.)
    return [[center, loop[i], loop[(i + 1) % len(loop)]]
            for i in range(len(loop))]


def slightly_perturbed_budget(faces):
    """Adjust one vertex only, without changing face/boundary counts."""
    shifted = [[tuple(p) for p in face] for face in faces]
    x, y, z = shifted[0][1]
    shifted[0][1] = (x + .03, y, z)
    return shifted


class AdversarialR7BoundaryTests(unittest.TestCase):

    def assert_review_only(self, result):
        self.assertEqual(result["status"], "review_only")
        self.assertIs(result["auto_apply"], False)
        self.assertIs(result["cross_file_part_identity_proven"], False)

    def test_same_count_different_collinear_split_forces_r2_fallback(self):
        a, b = split_edge_fan(.30), split_edge_fan(.70)
        self.assertEqual(boundary_audit(a, [5])["parts"][0]["boundary_edges"], 5)
        self.assertEqual(boundary_audit(b, [5])["parts"][0]["boundary_edges"], 5)
        # Equal-edge-count contours are *not* necessarily bytewise identical.
        a_lines, b_lines = (local_boundary_segments(f, [5]) for f in (a, b))
        self.assertNotEqual(_exact_undirected_contour_signature(
            [(tuple(s[1:4]), tuple(s[4:7])) for s in a_lines]),
            _exact_undirected_contour_signature(
            [(tuple(s[1:4]), tuple(s[4:7])) for s in b_lines]))
        real = matcher._observed_boundary_component_count
        with patch("cbdk.glb_part_match._observed_boundary_component_count",
                   wraps=real) as counter:
            current = suggest_spatial_part_matches(a, reorder_faces(b), [5], [5])
        self.assertEqual(counter.call_count, 2, "R3 guard must still run")
        self.assertEqual(current, baseline_scan(a, reorder_faces(b), [5], [5]))
        row = current["reference_parts"][0]
        self.assertEqual(row["status"], "suggested")
        self.assertEqual(row["topology_review_reasons"], [])
        self.assert_review_only(current)

    def test_equal_edge_count_shallow_notch_is_not_a_false_fast_match(self):
        original = split_edge_fan(.30)
        bad = split_edge_fan(.70, indentation=.03)
        self.assertEqual(boundary_audit(bad, [5])["parts"][0]["boundary_edges"], 5)
        for source, target in ((original, bad), (bad, original)):
            current = suggest_spatial_part_matches(source, target, [5], [5])
            self.assertEqual(current, baseline_scan(source, target, [5], [5]))
            row = current["reference_parts"][0]
            self.assertEqual(row["status"], "ambiguous")
            self.assertEqual(row["topology_review_reasons"],
                             ["boundary_spatial_layout_mismatch"])
            self.assert_review_only(current)

    def test_float32_collinear_split_and_small_notch_are_deterministic(self):
        original = float32_faces(split_edge_fan(.25))
        for candidate in (
            float32_faces(reorder_faces(split_edge_fan(.75))),
            float32_faces(reorder_faces(split_edge_fan(.75, indentation=.0001))),
        ):
            one = suggest_spatial_part_matches(original, candidate, [5], [5])
            self.assertEqual(one, baseline_scan(original, candidate, [5], [5]))
            self.assertEqual(one, suggest_spatial_part_matches(
                original, candidate, [5], [5]))
            self.assertEqual(one["reference_parts"][0]["status"], "suggested")
            self.assert_review_only(one)

    def test_direct_zero_length_boundary_guard_equals_original_r2(self):
        """R6 exact-signature early return must not accept invalid zero edges.

        Public GLB extraction already excludes collapsed triangles; test the
        private layout function independently against its original R2 scan.
        """
        part = {"center": (0., 0., 0.), "size": (1., 1., 0.)}
        zero = [[1, 0., 0., 0., 0., 0., 0.]]
        with patch("cbdk.glb_part_match._exact_undirected_contour_signature",
                   side_effect=lambda _lines: object()):
            original = _boundary_layout_issue(zero, zero, part, part)
        self.assertEqual(original, "boundary_spatial_layout_mismatch")
        self.assertEqual(_boundary_layout_issue(zero, zero, part, part),
                         original, "exact signature must not skip R2 zero-edge guard")

    def test_near_weld_triangle_is_marked_ambiguous_not_authoritative(self):
        barely_nonzero = [[(0., 0., 0.), (2e-8, 0., 0.), (0., 1., 0.)]]
        audit = boundary_audit(barely_nonzero, [1])
        self.assertEqual(audit["parts"][0]["weld_collapsed_triangles"], 1)
        result = suggest_spatial_part_matches(
            barely_nonzero, barely_nonzero, [1], [1])
        self.assertEqual(result["reference_parts"][0]["status"], "ambiguous")
        self.assertEqual(result["reference_parts"][0]["topology_review_reasons"],
                         ["weld_collapsed_triangles_observed"])
        self.assert_review_only(result)
        with self.assertRaises(SurfaceDistanceError):
            tiny = [[(0., 0., 0.), (0., 0., 0.), (0., 1., 0.)]]
            suggest_spatial_part_matches(tiny, tiny, [1], [1])

    def test_r3_gap_vs_contact_after_float32_and_winding(self):
        separated = float32_faces(nearly_touching_triangles())
        contact = float32_faces(nearly_touching_triangles(touch=True))
        for a, b in ((separated, contact), (contact, separated)):
            for candidate in (b, reorder_faces(b)):
                report = suggest_spatial_part_matches(a, candidate, [2], [2])
                self.assertEqual(report, baseline_scan(a, candidate, [2], [2]))
                self.assertEqual(report["reference_parts"][0]["status"],
                                 "ambiguous")
                self.assertEqual(report["reference_parts"][0]
                                 ["topology_review_reasons"],
                                 ["boundary_component_count_mismatch"])
                self.assert_review_only(report)

    def test_64_part_512_face_duplicate_motif_is_not_autopaired(self):
        groups = many_rings()
        groups[1] = [list(face) for face in groups[0]]
        reference = [face for group in groups for face in group]
        candidate = [face for group in reversed(groups)
                     for face in reorder_faces(group)]
        counts = [8] * 64
        self.assertEqual(len(reference), 512)
        result = suggest_spatial_part_matches(
            reference, candidate, counts, counts)
        self.assertEqual([row["status"] for row
                          in result["reference_parts"][:2]],
                         ["ambiguous", "ambiguous"])
        self.assertTrue(all(row["status"] == "suggested" for row
                            in result["reference_parts"][2:]))
        self.assertEqual(result["unpaired_candidate_part_ids"],
                         ["part_063", "part_064"])
        self.assertTrue(all(len(row["candidate_part_ids"]) <= 2 for row
                            in result["reference_parts"]))
        self.assertEqual(result, suggest_spatial_part_matches(
            reference, candidate, counts, counts))
        self.assert_review_only(result)

    def test_255_256_257_branch_and_nonexact_fallback_resource_budget(self):
        for edges, expected in ((255, "suggested"), (256, "suggested"),
                                (257, "ambiguous")):
            with self.subTest(observed_edges=edges):
                original = open_edge_fixture(edges)
                reordered = reorder_faces(original)
                with patch("cbdk.glb_part_match._exact_undirected_contour_signature",
                           wraps=_exact_undirected_contour_signature) as spy:
                    result = suggest_spatial_part_matches(
                        original, reordered, [len(original)], [len(original)])
                self.assertEqual(result["reference_parts"][0]["status"], expected)
                self.assertEqual(spy.call_count, 0 if edges == 257 else 2)
                self.assert_review_only(result)
                if edges == 257:
                    self.assertEqual(result["reference_parts"][0]
                                     ["topology_review_reasons"],
                                     ["boundary_layout_budget_exceeded"])
        original = open_edge_fixture(256)
        candidate = slightly_perturbed_budget(original)
        self.assertEqual(boundary_audit(candidate, [86])["parts"][0]
                         ["boundary_edges"], 256)
        before, after = [], []
        for _ in range(3):
            t0 = perf_counter()
            old = baseline_scan(original, candidate, [86], [86])
            before.append((perf_counter() - t0) * 1000.)
            t0 = perf_counter()
            report = suggest_spatial_part_matches(
                original, candidate, [86], [86])
            after.append((perf_counter() - t0) * 1000.)
            self.assertEqual(report, old)
            self.assertEqual(report["reference_parts"][0]["status"],
                             "suggested")
            self.assert_review_only(report)
        tracemalloc.start()
        try:
            suggest_spatial_part_matches(original, candidate, [86], [86])
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 32 * 1024 * 1024)
        print("CBDK_R7_NONEXACT_256 "
              f"forced_r2_median_ms={median(before):.3f} "
              f"r6_fallback_median_ms={median(after):.3f} "
              f"peak_kib={peak//1024} samples=3")


if __name__ == "__main__":
    unittest.main()
