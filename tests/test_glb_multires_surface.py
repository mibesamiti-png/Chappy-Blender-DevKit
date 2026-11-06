"""Coarse-to-fine surface probing regression tests on repository-authored meshes."""
from __future__ import annotations

import unittest

from cbdk.glb_multires_surface import (
    COARSE_SAMPLES, FINE_SAMPLES, MAX_SUSPECT_FACES, EXPLORATION_FACES,
    compare_multires_triangle_surfaces,
)
from cbdk.glb_surface_distance import (
    SurfaceDistanceError, compare_triangle_surfaces,
)


def filled_square(z=0.0, flip_diagonal=False):
    points = [(-1, -1, z), (1, -1, z), (1, 1, z), (-1, 1, z)]
    indices = [(0, 1, 3), (1, 2, 3)] if flip_diagonal else [
        (0, 1, 2), (0, 2, 3)]
    return [[points[i] for i in face] for face in indices]


def square_with_hole(half_width=0.22):
    outer = [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)]
    h = half_width
    inner = [(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)]
    mesh = []
    for i in range(4):
        j = (i + 1) % 4
        mesh.extend([[outer[i], outer[j], inner[j]],
                     [outer[i], inner[j], inner[i]]])
    return mesh


def tiled_triangles(n, z=0.0):
    return [[(i * 3, 0, z), (i * 3 + 1, 0, z), (i * 3, 1, z)]
            for i in range(n)]


class MultiResolutionSurfaceTests(unittest.TestCase):
    def test_narrow_open_hole_missed_at_24_found_by_48(self):
        filled, cutout = filled_square(), square_with_hole(.22)
        # Concrete counterexample: fixed 24-point/surface scoring misses it.
        old = compare_triangle_surfaces(filled, cutout)
        self.assertEqual(old["symmetric_mean"], 0)
        self.assertEqual(old["symmetric_sampled_max"], 0)
        report = compare_multires_triangle_surfaces(filled, cutout)
        self.assertEqual(report["coarse_symmetric_sampled_max"], 0)
        self.assertGreater(report["refined_symmetric_sampled_max"], .005)
        self.assertGreater(report["refined_symmetric_mean"], 0)
        self.assertTrue(report["new_nonzero_sample_after_refinement"])
        self.assertTrue(report["reference_to_candidate"]["new_nonzero_sample_after_refinement"])

    def test_no_false_claim_of_full_coverage(self):
        report = compare_multires_triangle_surfaces(filled_square(), filled_square())
        self.assertEqual(report["refined_symmetric_mean"], 0)
        self.assertFalse(report["complete_surface_coverage"])
        self.assertFalse(report["exact_hausdorff_verified"])
        self.assertFalse(report["enclosed_cavities_verified"])
        self.assertFalse(report["auto_approve"])

    def test_alternative_triangulation_same_surface_zero(self):
        report = compare_multires_triangle_surfaces(
            filled_square(), filled_square(flip_diagonal=True))
        self.assertEqual(report["coarse_symmetric_mean"], 0)
        self.assertEqual(report["refined_symmetric_mean"], 0)

    def test_z_translation_refined_distance(self):
        result = compare_multires_triangle_surfaces(
            filled_square(), filled_square(z=.25))
        self.assertAlmostEqual(result["coarse_symmetric_mean"], .25, places=6)
        self.assertAlmostEqual(result["refined_symmetric_mean"], .25, places=6)
        self.assertAlmostEqual(result["refined_symmetric_sampled_max"], .25, places=6)

    def test_refinement_counts_and_exploration_budget(self):
        report = compare_multires_triangle_surfaces(filled_square(), filled_square())
        forward = report["reference_to_candidate"]
        self.assertEqual(forward["coarse_sample_count"], 2 * COARSE_SAMPLES)
        self.assertEqual(forward["additional_sample_count"],
                         2 * (FINE_SAMPLES - COARSE_SAMPLES))
        self.assertEqual(forward["total_sample_count"], 2 * FINE_SAMPLES)
        self.assertEqual(forward["suspect_face_count"], 0)
        self.assertEqual(forward["exploration_face_count"], 2)

    def test_many_identical_faces_only_refine_exploration_quota(self):
        report = compare_multires_triangle_surfaces(
            tiled_triangles(48), tiled_triangles(48))
        forward = report["reference_to_candidate"]
        self.assertEqual(forward["coarse_sample_count"], 48 * COARSE_SAMPLES)
        self.assertEqual(forward["additional_sample_count"],
                         EXPLORATION_FACES * (FINE_SAMPLES - COARSE_SAMPLES))
        self.assertEqual(forward["unrefined_face_count"], 46)
        self.assertEqual(report["refined_symmetric_mean"], 0)

    def test_suspects_selected_before_exploration(self):
        result = compare_multires_triangle_surfaces(
            tiled_triangles(12), tiled_triangles(12, z=.4))
        fwd = result["reference_to_candidate"]
        self.assertEqual(fwd["suspect_face_count"], MAX_SUSPECT_FACES)
        self.assertEqual(fwd["exploration_face_count"], EXPLORATION_FACES)
        self.assertEqual(fwd["refined_face_count"], 10)
        self.assertEqual(fwd["additional_sample_count"], 10 * (FINE_SAMPLES - COARSE_SAMPLES))

    def test_more_sampling_not_claimed_monotonic(self):
        report = compare_multires_triangle_surfaces(
            filled_square(), square_with_hole(.22))
        self.assertIn("not guaranteed monotonic", " ".join(report["limitations"]))
        self.assertFalse(report["complete_surface_coverage"])

    def test_face_order_and_winding_independent(self):
        faces = square_with_hole(.22)
        backwards = [list(reversed(face)) for face in reversed(faces)]
        left = compare_multires_triangle_surfaces(filled_square(), faces)
        right = compare_multires_triangle_surfaces(filled_square(), backwards)
        self.assertEqual(left, right)

    def test_rejected_invalid_input(self):
        for bad in ([], "not triangles",
                    [[(0, 0, 0), (1, 1, 1), (2, 2, 2)]],
                    [[(0, 0, 0), (1, 0, 0), (0, 1, float("nan"))]]):
            with self.subTest(value=str(bad)[:30]), self.assertRaises(SurfaceDistanceError):
                compare_multires_triangle_surfaces(bad, filled_square())

    def test_source_geometry_not_exposed(self):
        source = filled_square(z=12345.678)
        report = compare_multires_triangle_surfaces(source, source)
        self.assertNotIn("12345", str(report))
        self.assertTrue(all(flag is False for flag in report["safety"].values()))
        self.assertEqual(report["status"], "review_only")

    def test_bounded_maximum_512_triangles(self):
        mesh = tiled_triangles(512)
        report = compare_multires_triangle_surfaces(mesh, mesh)
        self.assertEqual(report["reference_triangles"], 512)
        self.assertEqual(report["refined_symmetric_mean"], 0)
        self.assertLess(report["reference_to_candidate"]["total_sample_count"],
                        512 * FINE_SAMPLES)

    def test_above_limit_refused(self):
        with self.assertRaises(SurfaceDistanceError):
            compare_multires_triangle_surfaces(
                tiled_triangles(513), filled_square())


if __name__ == "__main__":
    unittest.main()
