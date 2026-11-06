"""Benchmark safety, correctness and reporting without timing-based pass gates."""
from __future__ import annotations

import unittest

from cbdk.surface_benchmark import (
    MAX_BRUTE_TRIANGLE_PAIRS, benchmark_surface_search,
)
from cbdk.glb_surface_distance import SurfaceDistanceError


def spaced_triangles(n, z=0.0):
    return [
        [(i * 3.0, 0.0, z), (i * 3.0 + 1, 0.0, z),
         (i * 3.0, 1, z)] for i in range(n)
    ]


class SurfaceBenchmarkTests(unittest.TestCase):
    def test_same_input_comparison_reports_both_timings(self):
        mesh = spaced_triangles(8)
        report = benchmark_surface_search(mesh, mesh, repeats=2)
        self.assertEqual(report["kind"], "cbdk_trusted_surface_search_benchmark")
        self.assertEqual(set(report["benchmarks"]), {"bvh", "brute_force"})
        self.assertEqual(report["sampled_mean"], 0)
        self.assertTrue(report["scores_agree_with_brute_force"])
        self.assertFalse(report["performance_regression_gate"])
        self.assertFalse(report["relative_timings_portable"])
        self.assertEqual(report["benchmarks"]["bvh"]["repeats"], 2)

    def test_offset_matches_brute_force(self):
        result = benchmark_surface_search(
            spaced_triangles(4), spaced_triangles(4, z=0.25), repeats=1)
        self.assertAlmostEqual(result["sampled_mean"], 0.25)
        self.assertAlmostEqual(result["sampled_max"], 0.25)
        self.assertTrue(result["scores_agree_with_brute_force"])

    def test_large_mesh_bvh_only(self):
        mesh = spaced_triangles(100)
        result = benchmark_surface_search(
            mesh, mesh, repeats=1, include_brute_force=False)
        self.assertEqual(set(result["benchmarks"]), {"bvh"})
        self.assertIsNone(result["observed_brute_vs_bvh_median_ratio"])
        self.assertFalse(result["scores_agree_with_brute_force"])
        self.assertEqual(result["reference_triangles"], 100)

    def test_reject_costly_brute_force(self):
        mesh = spaced_triangles(65)
        self.assertGreater(65 * 65, MAX_BRUTE_TRIANGLE_PAIRS)
        with self.assertRaisesRegex(SurfaceDistanceError, "restricted"):
            benchmark_surface_search(mesh, mesh, repeats=1)

    def test_brute_force_at_limit_works(self):
        mesh = spaced_triangles(64)
        result = benchmark_surface_search(mesh, mesh, repeats=1)
        self.assertTrue(result["scores_agree_with_brute_force"])

    def test_invalid_repeat_values(self):
        mesh = spaced_triangles(1)
        for value in (-1, 0, 6, 1.5, "3", True):
            with self.subTest(value=value), self.assertRaises(SurfaceDistanceError):
                benchmark_surface_search(mesh, mesh, repeats=value)

    def test_invalid_brute_toggle(self):
        mesh = spaced_triangles(1)
        with self.assertRaises(SurfaceDistanceError):
            benchmark_surface_search(mesh, mesh, include_brute_force="yes")

    def test_no_private_geometry_in_report(self):
        mesh = [[(-9876.54321, 0, 0), (-9875.54321, 0, 0),
                 (-9876.54321, 1, 0)]]
        result = benchmark_surface_search(mesh, mesh, repeats=1)
        text = str(result)
        self.assertNotIn("9876", text)
        self.assertFalse(result["safety"]["publishes_private_mesh"])
        self.assertFalse(result["safety"]["executes_user_addon"])

    def test_no_elapsed_speedup_guarantee(self):
        mesh = spaced_triangles(1)
        result = benchmark_surface_search(mesh, mesh, repeats=1)
        self.assertEqual(result["scope"],
                         "end_to_end_single_direction_including_bvh_build_and_sampling")
        self.assertEqual(result["elapsed_time_unit"], "milliseconds")
        self.assertFalse(result["relative_timings_portable"])
        self.assertFalse(result["performance_regression_gate"])

    def test_input_over_512_rejected(self):
        with self.assertRaises(SurfaceDistanceError):
            benchmark_surface_search(
                spaced_triangles(513), spaced_triangles(1),
                include_brute_force=False)


if __name__ == "__main__":
    unittest.main()
