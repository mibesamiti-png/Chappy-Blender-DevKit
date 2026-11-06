"""Surface-to-triangle comparisons: topology/index independence and cutout detection."""
from __future__ import annotations

import math
import unittest

from cbdk.glb_surface_distance import (
    SurfaceDistanceError, MAX_TRIANGLES, compare_triangle_surfaces,
)


def filled_square(diagonal="main", z=0.0):
    a, b, c, d = ((-1.0, -1.0, z), (1.0, -1.0, z),
                  (1.0, 1.0, z), (-1.0, 1.0, z))
    if diagonal == "main":
        return [[a, b, c], [a, c, d]]
    return [[a, b, d], [b, c, d]]


def square_with_open_hole():
    outside = [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)]
    inside = [(-0.45, -0.45, 0), (0.45, -0.45, 0),
              (0.45, 0.45, 0), (-0.45, 0.45, 0)]
    triangles = []
    for i in range(4):
        j = (i + 1) % 4
        triangles.extend([
            [outside[i], outside[j], inside[j]],
            [outside[i], inside[j], inside[i]],
        ])
    return triangles


class SampledSurfaceDistanceTests(unittest.TestCase):
    def test_identical_surface_zero(self):
        square = filled_square()
        report = compare_triangle_surfaces(square, square)
        self.assertEqual(report["symmetric_mean"], 0)
        self.assertEqual(report["symmetric_sampled_max"], 0)
        self.assertEqual(report["reference_to_candidate"]["sample_count"], 24)

    def test_different_triangulation_same_surface_zero(self):
        report = compare_triangle_surfaces(filled_square(), filled_square("other"))
        self.assertEqual(report["symmetric_mean"], 0)
        self.assertEqual(report["symmetric_sampled_max"], 0)
        self.assertFalse(report["triangulation_correspondence_required"])

    def test_reverse_winding_face_and_vertex_order(self):
        a = filled_square()
        b = [[*reversed(face)] for face in reversed(a)]
        report = compare_triangle_surfaces(a, b)
        self.assertEqual(report["symmetric_mean"], 0)
        self.assertFalse(report["vertex_correspondence_required"])

    def test_translation_z_has_known_approximate_distance(self):
        report = compare_triangle_surfaces(filled_square(), filled_square(z=0.25))
        self.assertAlmostEqual(report["symmetric_mean"], 0.25, places=6)
        self.assertAlmostEqual(report["symmetric_sampled_max"], 0.25, places=6)
        self.assertEqual(report["units"], "input_coordinate_units")

    def test_open_center_hole_detected_despite_identical_outer_bounds(self):
        report = compare_triangle_surfaces(square_with_open_hole(), filled_square())
        self.assertEqual(report["reference_to_candidate"]["mean"], 0)
        self.assertGreater(report["candidate_to_reference"]["mean"], 0.01)
        self.assertGreater(report["candidate_to_reference"]["sampled_max"], 0.10)
        self.assertGreater(report["symmetric_sampled_max"], 0.10)
        self.assertFalse(report["enclosed_cavities_verified"])

    def test_open_hole_directionality_reverses_on_swap(self):
        left = compare_triangle_surfaces(square_with_open_hole(), filled_square())
        right = compare_triangle_surfaces(filled_square(), square_with_open_hole())
        self.assertEqual(left["candidate_to_reference"]["mean"],
                         right["reference_to_candidate"]["mean"])
        self.assertEqual(left["symmetric_mean"], right["symmetric_mean"])

    def test_identical_radial_distances_do_not_imply_same_surface(self):
        left = [[(1, 0, 0), (-1, 0, 0), (0, 1, 0)]]
        right = [[(0, 1, 0), (0, -1, 0), (0, 0, 1)]]
        report = compare_triangle_surfaces(left, right)
        self.assertGreater(report["symmetric_mean"], 0.05)

    def test_deterministic_and_no_input_mutation(self):
        left = filled_square()
        right = square_with_open_hole()
        original_left = repr(left)
        original_right = repr(right)
        a = compare_triangle_surfaces(left, right)
        self.assertEqual(a, compare_triangle_surfaces(left, right))
        self.assertEqual(repr(left), original_left)
        self.assertEqual(repr(right), original_right)

    def test_rejects_degenerate_zero_area_faces(self):
        with self.assertRaises(SurfaceDistanceError):
            compare_triangle_surfaces([[(0, 0, 0), (1, 0, 0), (2, 0, 0)]],
                                      filled_square())

    def test_rejects_invalid_triangle_counts(self):
        for invalid in ([], filled_square() * (MAX_TRIANGLES + 1), "bad", None):
            with self.subTest(value=str(type(invalid))), self.assertRaises(SurfaceDistanceError):
                compare_triangle_surfaces(invalid, filled_square())

    def test_rejects_invalid_vertices(self):
        invalid = [
            [[0, 0, 0], [0, 0, 1]],
            [[0, 0, 0], [1, 0, 0], [0, 1]],
            [[0, 0, 0], [1, 0, 0], [0, 1, True]],
            [[0, 0, 0], [1, 0, 0], [0, 1, "0"]],
        ]
        for face in invalid:
            with self.subTest(face=repr(face)), self.assertRaises(SurfaceDistanceError):
                compare_triangle_surfaces([face], filled_square())

    def test_rejects_nonfinite_huge_and_overflowing_values(self):
        for bad in (float("nan"), float("inf"), float("-inf"), 1e7, 10**1000):
            with self.subTest(bad=str(bad)), self.assertRaises(SurfaceDistanceError):
                compare_triangle_surfaces([[(bad, 0, 0), (1, 0, 0), (0, 1, 0)]],
                                          filled_square())

    def test_report_cannot_be_mistaken_for_exact_hausdorff_or_volumetric_proof(self):
        report = compare_triangle_surfaces(filled_square(), filled_square())
        self.assertEqual(report["status"], "review_only")
        self.assertEqual(report["metric"],
                         "area_weighted_bidirectional_sampled_point_to_triangle_distance")
        self.assertFalse(report["exact_surface_equivalence_verified"])
        self.assertFalse(report["watertight_solid_equivalence_verified"])
        self.assertFalse(report["safety"]["auto_approves"])
        self.assertFalse(report["safety"]["executes_addon"])
        self.assertFalse(report["safety"]["uploads_private_geometry"])


if __name__ == "__main__":
    unittest.main()
