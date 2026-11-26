"""R27 A tests: actual Git checkout bytes, no test fixture normalization."""
import unittest

from cbdk.parameter_source_candidate_r27 import build_fixed_source_candidate, restore_fixed_source_candidate
from scripts.blender_parameter_r27_parent import SOURCE, SOURCE_SHA, exact_pair, sha


class R27ParentTests(unittest.TestCase):
    def test_actual_checkout_and_independent_pair(self):
        original = SOURCE.read_bytes()
        self.assertEqual(sha(original), SOURCE_SHA)
        candidate, diff = build_fixed_source_candidate(run_id="1" * 32,
            source_sha256=SOURCE_SHA, blender_version="4.4.3")
        self.assertEqual(exact_pair(original, candidate), original)
        self.assertEqual(restore_fixed_source_candidate(candidate), original)
        self.assertEqual(diff["byte_offset"], 570)
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_parent_rejects_other_bytes(self):
        original = SOURCE.read_bytes()
        candidate, _ = build_fixed_source_candidate(run_id="2" * 32,
            source_sha256=SOURCE_SHA, blender_version="4.4.3")
        for old, new in ((original.replace(b"\n", b"\r\n"), candidate),
                         (original, candidate + b"\n"), (original, original)):
            with self.assertRaises(ValueError):
                exact_pair(old, new)
