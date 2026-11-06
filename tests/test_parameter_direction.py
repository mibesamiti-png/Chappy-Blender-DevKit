"""Pure review-only probe direction decisions for trusted synthetic GLB runs."""
from __future__ import annotations

import math
import unittest

from cbdk.parameter_direction import DirectionEvidenceError, choose_review_direction


class ParameterDirectionTests(unittest.TestCase):
    def test_increase_direction(self):
        result = choose_review_direction(0.4, 0.2, 0.6)
        self.assertEqual(result["decision"], "increase")
        self.assertAlmostEqual(result["absolute_error_reduction_from_baseline"], 0.2)
        self.assertFalse(result["auto_apply"])
        self.assertIsNone(result["suggested_numeric_value"])

    def test_decrease_direction(self):
        result = choose_review_direction(0.4, 0.6, 0.2)
        self.assertEqual(result["decision"], "decrease")
        self.assertAlmostEqual(result["best_observed_error"], 0.2)

    def test_neither_probe_improves(self):
        self.assertEqual(choose_review_direction(0.2, 0.3, 0.4)["decision"],
                         "inconclusive")

    def test_ambiguous_equal_improvements(self):
        self.assertEqual(choose_review_direction(0.5, 0.3, 0.3)["decision"],
                         "inconclusive")

    def test_noise_smaller_than_margin(self):
        self.assertEqual(
            choose_review_direction(1.0, 0.9999999, 1.2)["decision"],
            "inconclusive")

    def test_custom_margin_prevents_uncertain_choice(self):
        self.assertEqual(
            choose_review_direction(1.0, 0.95, 1.2, margin=0.1)["decision"],
            "inconclusive")
        self.assertEqual(
            choose_review_direction(1.0, 0.95, 1.2, margin=0.01)["decision"],
            "increase")

    def test_zero_baseline_has_no_improvement(self):
        self.assertEqual(choose_review_direction(0, 0, 0)["decision"],
                         "inconclusive")

    def test_nonfinite_negative_boolean_or_non_numeric_rejected(self):
        for bad in (math.nan, math.inf, -math.inf, -1, True, None, "0.4", 10**1000):
            for i in range(3):
                nums = [0.4, 0.2, 0.6]
                nums[i] = bad
                with self.subTest(bad=str(bad), index=i), self.assertRaises(DirectionEvidenceError):
                    choose_review_direction(*nums)

    def test_bad_margin_rejected(self):
        for bad in (-1, 0, math.inf, math.nan, True, "0.01"):
            with self.subTest(margin=str(bad)), self.assertRaises(DirectionEvidenceError):
                choose_review_direction(0.4, 0.2, 0.6, margin=bad)

    def test_result_has_review_and_privacy_flags(self):
        result = choose_review_direction(1, 0.3, 2)
        self.assertEqual(result["status"], "review_only_synthetic_fixture")
        self.assertFalse(result["verified_for_arbitrary_user_addons"])
        self.assertEqual(result["reference_error"]["baseline"], 1)
        self.assertEqual(result["reference_error"]["increase_probe"], 0.3)
        self.assertEqual(result["reference_error"]["decrease_probe"], 2)

    def test_repeatable_result(self):
        a = choose_review_direction(0.8, 0.45, 1.2)
        self.assertEqual(a, choose_review_direction(0.8, 0.45, 1.2))


if __name__ == "__main__":
    unittest.main()
