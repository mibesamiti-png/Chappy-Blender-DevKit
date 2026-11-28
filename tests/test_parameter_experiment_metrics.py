"""Pure numeric tests for trusted indexed-mesh displacement measurement."""
from __future__ import annotations

import math
import unittest

from cbdk.parameter_experiment_metrics import (
    ExperimentMetricError, vertex_displacement, radial_distribution_error,
)


class ParameterExperimentMetricTests(unittest.TestCase):
    def test_identical_meshes_are_zero(self):
        points = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        result = vertex_displacement(points, points)
        self.assertEqual(result["changed_vertex_count"], 0)
        self.assertEqual(result["mean_local_displacement"], 0)
        self.assertEqual(result["max_local_displacement"], 0)
        self.assertFalse(result["valid_for_arbitrary_glb"])

    def test_single_vertex_translation_measured(self):
        result = vertex_displacement([[0, 0, 0], [1, 0, 0]],
                                     [[3, 4, 0], [1, 0, 0]])
        self.assertEqual(result["max_local_displacement"], 5)
        self.assertEqual(result["mean_local_displacement"], 2.5)
        self.assertEqual(result["changed_vertex_count"], 1)

    def test_all_vertices_changed(self):
        result = vertex_displacement([[0, 0, 0], [0, 0, 1]],
                                     [[0, 0, 2], [0, 0, 3]])
        self.assertEqual(result["changed_vertex_count"], 2)
        self.assertEqual(result["max_local_displacement"], 2)

    def test_small_differences_are_tolerance_bounded(self):
        result = vertex_displacement([[0, 0, 0]], [[1e-7, 0, 0]])
        self.assertEqual(result["changed_vertex_count"], 0)

    def test_mismatched_vertices_fail_closed(self):
        with self.assertRaises(ExperimentMetricError):
            vertex_displacement([[0, 0, 0]], [[0, 0, 0], [1, 0, 0]])

    def test_empty_points_rejected(self):
        with self.assertRaises(ExperimentMetricError):
            vertex_displacement([], [])

    def test_invalid_shape_and_nonnumeric_values_rejected(self):
        for bad in (([[0, 1]], [[0, 1]]), ([[0, 1, True]], [[0, 1, 1]]),
                    ([[0, 0, "1"]], [[0, 0, 1]]), (None, [[0, 0, 0]]),
                    ([[0, 0, 0]], {"a": 1})):
            with self.subTest(bad=repr(bad)), self.assertRaises(ExperimentMetricError):
                vertex_displacement(*bad)

    def test_nonfinite_and_excessive_coordinates_rejected(self):
        for value in (math.nan, math.inf, -math.inf, 10 ** 1000):
            with self.subTest(value=str(value)), self.assertRaises(ExperimentMetricError):
                vertex_displacement([[value, 0, 0]], [[0, 0, 0]])

    def test_index_aligned_caveat_present(self):
        out = vertex_displacement([[0, 0, 0]], [[0, 0, 0]])
        self.assertEqual(out["metric"], "index_aligned_local_vertex_distance")
        self.assertEqual(out["vertex_count"], 1)
        self.assertEqual(out["tolerance"], 1e-6)

    def test_output_deterministic(self):
        a = [[0, 0, 0], [1, 1, 1]]
        b = [[0, 0, 0], [2, 1, 1]]
        self.assertEqual(vertex_displacement(a, b), vertex_displacement(a, b))



    def test_radial_error_zero_for_reordered_same_vertices(self):
        reference = [[1, 0, 0], [0, 2, 0], [0, 0, 3]]
        reordered = [[0, 0, 3], [1, 0, 0], [0, 2, 0]]
        self.assertGreater(vertex_displacement(reference, reordered)["mean_local_displacement"], 0)
        scored = radial_distribution_error(reference, reordered)
        self.assertEqual(scored["mean_sorted_radius_error"], 0)
        self.assertTrue(scored["invariant_to_vertex_order"])
        self.assertFalse(scored["geometry_equivalence_verified"])

    def test_radial_error_detects_known_synthetic_sphere_direction(self):
        reference = [[1.15, 0, 0], [-1.15, 0, 0]]
        variants = (
            [[0.75, 0, 0], [-0.75, 0, 0]],
            [[0.95, 0, 0], [-0.95, 0, 0]],
            [[0.55, 0, 0], [-0.55, 0, 0]],
        )
        scores = [radial_distribution_error(reference, v)["mean_sorted_radius_error"]
                  for v in variants]
        self.assertEqual(scores, [0.4, 0.2, 0.6])

    def test_radial_distribution_not_a_shape_identity_proof(self):
        left = [[1, 0, 0], [-1, 0, 0]]
        right = [[0, 1, 0], [0, -1, 0]]
        result = radial_distribution_error(left, right)
        self.assertEqual(result["mean_sorted_radius_error"], 0)
        self.assertFalse(result["valid_for_arbitrary_glb"])
        self.assertFalse(result["geometry_equivalence_verified"])

    def test_radial_disallows_unequal_topology(self):
        with self.assertRaises(ExperimentMetricError):
            radial_distribution_error([[1, 0, 0]], [[1, 0, 0], [0, 1, 0]])

    def test_radial_disallows_nonfinite_and_boolean_points(self):
        for bad in (float("nan"), float("inf"), True, "1"):
            with self.subTest(bad=str(bad)), self.assertRaises(ExperimentMetricError):
                radial_distribution_error([[bad, 0, 0]], [[0, 0, 0]])

if __name__ == "__main__":
    unittest.main()
