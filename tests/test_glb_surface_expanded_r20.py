"""R20 expanded-profile core checks; native GLB integration is separate."""
import unittest
from unittest.mock import patch

from cbdk.glb_surface_distance import (
    SurfaceDistanceError, _SurfaceWorkBudget, compare_triangle_surfaces,
)
from cbdk.glb_multires_surface import (
    _expanded_review, compare_expanded_triangle_surfaces,
    compare_multires_triangle_surfaces,
)
from cbdk import glb_multires_surface


def grid(n, z=0.0):
    return [((float(i), 0.0, z), (float(i + 1), 0.0, z),
             (float(i), 1.0, z)) for i in range(n)]


class ExpandedSurfaceTests(unittest.TestCase):
    def test_legacy_parity_and_two_builds(self):
        ref, cand = grid(5), grid(5, 0.125)
        old_fixed = compare_triangle_surfaces(ref, cand)
        old_adaptive = compare_multires_triangle_surfaces(ref, cand)
        with patch.object(glb_multires_surface, "_build_bvh",
                          wraps=glb_multires_surface._build_bvh) as build:
            new = compare_expanded_triangle_surfaces(ref, cand)
        self.assertEqual(build.call_count, 2)
        self.assertEqual(new["status"], "review_only")
        self.assertEqual(new["fixed_surface"]["symmetric_mean"], 0.125)
        self.assertEqual(new["adaptive_surface"]["refined_symmetric_mean"], 0.125)
        for key in ("reference_to_candidate", "candidate_to_reference"):
            self.assertEqual(new["fixed_surface"][key], old_fixed[key])
            self.assertEqual(new["adaptive_surface"][key], old_adaptive[key])
        reports = (new["fixed_surface"], new["adaptive_surface"])
        directions = ("reference_to_candidate", "candidate_to_reference")
        self.assertEqual(new["work_budget"]["used"]["triangle_evaluations"],
                         sum(x[k]["triangle_distance_evaluations"]
                             for x in reports for k in directions))

    def test_strict_limits(self):
        with self.assertRaises(SurfaceDistanceError):
            compare_triangle_surfaces(grid(513), grid(1))
        with self.assertRaises(SurfaceDistanceError):
            compare_expanded_triangle_surfaces(grid(2049), grid(1))

    def test_expanded_more_than_legacy(self):
        ref, cand = grid(513), grid(513, 0.25)
        new = compare_expanded_triangle_surfaces(ref, cand)
        self.assertEqual(new["status"], "review_only")
        self.assertEqual(new["fixed_surface"]["symmetric_sampled_max"], 0.25)
        self.assertEqual(new["adaptive_surface"]["refined_symmetric_sampled_max"], 0.25)

    def test_every_budget_can_stop_without_distances(self):
        for key in ("samples", "node_visits", "triangle_evaluations"):
            with self.subTest(key=key):
                budget = _SurfaceWorkBudget()
                budget.LIMITS = dict(budget.LIMITS, **{key: 1})
                new = _expanded_review(grid(3), grid(3), budget)
                self.assertEqual(new["status"], "skipped")
                self.assertEqual(new["exhausted_counter"], key)
                self.assertEqual(new["surface_observation"], "not_measured")
                self.assertNotIn("fixed_surface", new)
                self.assertNotIn("adaptive_surface", new)
                self.assertEqual(new["work_budget"]["used"][key], 1)


if __name__ == "__main__":
    unittest.main()
