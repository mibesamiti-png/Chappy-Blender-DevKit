"""Deterministic BVH tests vs exact brute-force triangle surface queries."""
from __future__ import annotations

import unittest

from cbdk.glb_surface_distance import (
    MAX_TRIANGLES, SAMPLES_PER_TRIANGLE, SurfaceDistanceError,
    _box_distance_squared, _directed, _validated_triangles,
    compare_triangle_surfaces,
)


def tiled_faces(cols, rows, *, z=0.0, spacing=2.75):
    """Synthetic, separated triangle patches (not a user model)."""
    result = []
    for y in range(rows):
        for x in range(cols):
            ox, oy = x * spacing, y * spacing
            result.append([
                (ox, oy, z),
                (ox + 1.0, oy, z),
                (ox, oy + 1.0, z),
            ])
    return result


class SurfaceBVHTests(unittest.TestCase):
    def test_nearest_triangle_matches_bruteforce_for_translated_grid(self):
        left = _validated_triangles(tiled_faces(4, 4), "reference")
        right = _validated_triangles(tiled_faces(4, 4, z=.36), "candidate")
        fast = _directed(left, right)
        brute = _directed(left, right, accelerated=False)
        self.assertEqual(fast["mean"], brute["mean"])
        self.assertEqual(fast["sampled_max"], brute["sampled_max"])
        self.assertEqual(fast["sample_count"], brute["sample_count"])
        self.assertLess(fast["triangle_distance_evaluations"],
                        fast["brute_force_evaluations"])
        self.assertEqual(brute["triangle_distance_evaluations"],
                         brute["brute_force_evaluations"])

    def test_same_surface_triangulation_matches_bruteforce(self):
        reference = [
            [(-1, -1, 0), (1, -1, 0), (1, 1, 0)],
            [(-1, -1, 0), (1, 1, 0), (-1, 1, 0)],
        ]
        candidate = [
            [(-1, -1, 0), (1, -1, 0), (-1, 1, 0)],
            [(1, -1, 0), (1, 1, 0), (-1, 1, 0)],
        ]
        left = _validated_triangles(reference, "reference")
        right = _validated_triangles(candidate, "candidate")
        self.assertEqual(_directed(left, right)["mean"],
                         _directed(left, right, accelerated=False)["mean"])

    def test_large_400_face_fixture_reduces_exact_triangle_evaluations(self):
        face_list = tiled_faces(20, 20)
        report = compare_triangle_surfaces(face_list, face_list)
        self.assertEqual(report["reference_triangles"], 400)
        self.assertEqual(report["symmetric_mean"], 0)
        self.assertEqual(report["symmetric_sampled_max"], 0)
        self.assertLess(
            report["reference_to_candidate"]["triangle_distance_evaluations"],
            report["reference_to_candidate"]["brute_force_evaluations"] // 4,
        )
        self.assertEqual(report["search_acceleration"],
                         "deterministic_median_split_triangle_aabb_bvh")
        self.assertFalse(report["exact_surface_equivalence_verified"])

    def test_maximum_512_face_input_is_accepted(self):
        mesh = tiled_faces(32, 16)
        report = compare_triangle_surfaces(mesh, mesh)
        self.assertEqual(report["reference_triangles"], MAX_TRIANGLES)
        self.assertEqual(report["candidate_triangles"], MAX_TRIANGLES)
        self.assertEqual(report["reference_to_candidate"]["sample_count"],
                         MAX_TRIANGLES * SAMPLES_PER_TRIANGLE)

    def test_above_limit_refused(self):
        with self.assertRaises(SurfaceDistanceError):
            compare_triangle_surfaces(tiled_faces(33, 16), tiled_faces(1, 1))

    def test_pruning_preserves_offset_distance(self):
        report = compare_triangle_surfaces(tiled_faces(5, 4),
                                           tiled_faces(5, 4, z=.25))
        self.assertAlmostEqual(report["symmetric_mean"], .25, places=6)
        self.assertAlmostEqual(report["symmetric_sampled_max"], .25, places=6)

    def test_face_order_and_winding_do_not_change_geometry_score(self):
        a = tiled_faces(4, 4)
        b = [list(reversed(face)) for face in reversed(a)]
        report = compare_triangle_surfaces(a, b)
        self.assertEqual(report["symmetric_mean"], 0)
        self.assertEqual(report["symmetric_sampled_max"], 0)

    def test_aabb_lower_bound_for_inside_and_outside(self):
        bounds = ((0, 0, 0), (1, 1, 1))
        self.assertEqual(_box_distance_squared((.5, .5, .5), bounds), 0)
        self.assertEqual(_box_distance_squared((2, .5, .5), bounds), 1)
        self.assertEqual(_box_distance_squared((2, 3, .5), bounds), 5)

    def test_bvh_pruning_measurement_is_stable(self):
        faces = tiled_faces(8, 8)
        a = compare_triangle_surfaces(faces, faces)
        b = compare_triangle_surfaces(faces, faces)
        self.assertEqual(a, b)
        self.assertLessEqual(
            a["reference_to_candidate"]["triangle_distance_evaluations"],
            a["reference_to_candidate"]["brute_force_evaluations"],
        )

    def test_bvh_does_not_change_review_only_or_cavity_claims(self):
        report = compare_triangle_surfaces(tiled_faces(4, 4),
                                           tiled_faces(4, 4))
        self.assertEqual(report["status"], "review_only")
        self.assertFalse(report["enclosed_cavities_verified"])
        self.assertFalse(report["watertight_solid_equivalence_verified"])
        self.assertFalse(report["safety"]["auto_approves"])
        self.assertEqual(report["max_triangles_per_mesh"], 512)


if __name__ == "__main__":
    unittest.main()
