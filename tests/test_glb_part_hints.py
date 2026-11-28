"""Conservative anonymous triangle-count matching regression checks."""
from __future__ import annotations
import unittest
from cbdk.glb_part_hints import count_based_part_hints


class PartCountHintTests(unittest.TestCase):
    def test_unique_counts_are_only_weak_candidates(self):
        result = count_based_part_hints([12, 8, 4], [12, 8, 5],
                                        reference_total=3, candidate_total=3)
        self.assertEqual(result["weak_candidate_triangle_counts"], [8, 12])
        self.assertFalse(result["correspondence_verified"])
        self.assertFalse(result["shape_equivalence_verified"])

    def test_duplicates_and_zero_have_no_identity_claim(self):
        result = count_based_part_hints([8, 8, 0], [8, 8, 0],
                                        reference_total=3, candidate_total=3)
        self.assertEqual(result["candidate_count"], 0)

    def test_truncated_inventory_is_not_matchable(self):
        result = count_based_part_hints([30] * 32, [30] * 32,
                                        reference_total=33, candidate_total=33)
        self.assertEqual(result["status"], "insufficient_inventory")
        self.assertEqual(result["weak_candidate_triangle_counts"], [])

    def test_rejects_bad_counts_and_totals(self):
        for bad in (-1, True, 0.5, "3"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                count_based_part_hints([bad], [2],
                                       reference_total=1, candidate_total=1)
        with self.assertRaises(ValueError):
            count_based_part_hints([2], [2], reference_total=3,
                                   candidate_total=1)
        with self.assertRaises(ValueError):
            count_based_part_hints([1] * 33, [1], reference_total=33,
                                   candidate_total=1)


if __name__ == "__main__":
    unittest.main()
