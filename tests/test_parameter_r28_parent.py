"""A independent exact checkout candidate derivation, no Blender import."""
import unittest
from scripts.blender_parameter_r28_parent import (
    SOURCE, SOURCE_SHA, TRIALS, DIGESTS, fixed_pair, reverse_pair, sha, normalize_history,
)
from scripts.parameter_source_r28_copy import candidate_bytes, inverse_bytes


class R28ParentTests(unittest.TestCase):
    def test_actual_checkout_all_four_pairs(self):
        original = SOURCE.read_bytes()
        self.assertEqual(sha(original), SOURCE_SHA)
        for i, trial in enumerate(TRIALS):
            candidate, diff = fixed_pair(original, trial)
            self.assertEqual(sha(candidate), DIGESTS[i])
            self.assertEqual(candidate, candidate_bytes(original, trial))
            self.assertEqual(reverse_pair(candidate, diff["tokens"]), original)
            self.assertEqual(inverse_bytes(candidate, original, trial), original)
            self.assertEqual(len(diff["tokens"]), 2 if i == 1 else 1)
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_wrong_bytes_and_trial_rejected(self):
        original = SOURCE.read_bytes()
        for bad in (original + b"\n", original.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                fixed_pair(bad, "target")
        with self.assertRaises(ValueError):
            fixed_pair(original, "unknown")
        candidate, diff = fixed_pair(original, "cross_part")
        with self.assertRaises(ValueError):
            reverse_pair(candidate + b"\n", diff["tokens"])
        with self.assertRaises(ValueError):
            reverse_pair(original, diff["tokens"])

    def test_rejected_review_not_normalized(self):
        with self.assertRaises(ValueError):
            normalize_history({"status":"rejected"})
