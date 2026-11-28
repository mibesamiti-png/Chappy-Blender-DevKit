"""GLB-020: finite, bounded second-pass sampling, never a completeness claim."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from cbdk.glb_sampling_audit import (
    METHOD, counts_by_part, probe_sampling_sensitivity,
)

TRI = [[(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)]]


class SamplingAuditTests(unittest.TestCase):
    def test_identical_shapes_have_no_observed_sensitivity_but_remain_unverified(self):
        result = probe_sampling_sensitivity(TRI, TRI, .01, .05)
        self.assertEqual(result["method"], METHOD)
        self.assertEqual(result["initial_samples_per_triangle"], 24)
        self.assertEqual(result["additional_samples_per_triangle"], 24)
        self.assertEqual(result["reference_flags"], [False])
        self.assertEqual(result["candidate_flags"], [False])
        self.assertEqual(result["reference_summary"]["sensitive_faces"], 0)
        self.assertFalse(result["unobserved_regions_verified"])
        self.assertFalse(result["complete_surface_equivalence_proven"])

    def test_additional_probe_can_reveal_a_missed_corner(self):
        inset = [[(.04, .04, 0.), (.92, .04, 0.), (.04, .92, 0.)]]
        # The added sample is an actual corner of each source triangle, and
        # exposes the region that the 24 interior Halton samples may miss.
        with patch("cbdk.glb_sampling_audit._additional_points",
                   side_effect=lambda face: [face[0]]):
            result = probe_sampling_sensitivity(TRI, inset, .01, .05)
        self.assertTrue(result["reference_flags"][0])
        self.assertEqual(counts_by_part(result["reference_flags"], [1]), [1])
        self.assertFalse(result["unobserved_regions_verified"])

    def test_flags_preserve_input_order_and_sum_per_anonymous_part(self):
        faces = TRI + [[(3., 0., .3), (4., 0., .3), (3., 1., .3)]]
        result = probe_sampling_sensitivity(faces, TRI, .02, .10)
        self.assertEqual(len(result["reference_flags"]), 2)
        counts = counts_by_part(result["reference_flags"], [1, 1])
        self.assertEqual(sum(counts), result["reference_summary"]["sensitive_faces"])
        self.assertTrue(all(type(flag) is bool for flag in result["reference_flags"]))

    def test_invalid_thresholds_and_input_faces_are_rejected(self):
        for low, high in ((0., .1), (.1, .1), (.2, .1), (float("nan"), 1.),
                          (.01, True), (True, 1.), (.1, float("inf"))):
            with self.subTest(low=low, high=high):
                with self.assertRaises(ValueError):
                    probe_sampling_sensitivity(TRI, TRI, low, high)
        for values in ([], TRI * 513, [[(0., 0., float("nan"))] * 3]):
            with self.assertRaises(ValueError):
                probe_sampling_sensitivity(values, TRI, .01, .05)

    def test_part_aggregator_rejects_inconsistent_or_non_boolean_flags(self):
        for flags, counts in (([True], [2]), ([1], [1]), ([False], [0, 1]),
                              ([False], [True]), ([], []), ([False], [1] * 65)):
            with self.subTest(flags=flags, counts=counts):
                with self.assertRaises(ValueError):
                    counts_by_part(flags, counts)


if __name__ == "__main__":
    unittest.main()
