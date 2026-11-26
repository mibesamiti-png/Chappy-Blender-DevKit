"""R28 fixed-byte and isolation controls, no native execution."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.parameter_source_r28_copy import (
    SOURCE, SOURCE_SHA256, TRIAL_IDS, TOKENS, COPY_NAME, candidate_bytes, inverse_bytes,
    isolated_trial, sha,
)
from scripts.parameter_source_r27_copy import candidate_bytes as r27_candidate


class R28CopyTests(unittest.TestCase):
    def setUp(self):
        checkout = SOURCE.read_bytes()
        self.original = checkout.replace(b"\r\n", b"\n")
        self.assertEqual(sha(self.original), SOURCE_SHA256)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.source = self.root / COPY_NAME
        self.source.write_bytes(self.original)
        self.addCleanup(self.assertEqual, SOURCE.read_bytes(), checkout)
        patcher = patch("scripts.parameter_source_r28_copy.SOURCE", self.source)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_four_independent_exact_candidates_and_inverse(self):
        hashes = set()
        for trial_id in TRIAL_IDS:
            with self.subTest(trial=trial_id):
                radius, bevel = TOKENS[trial_id]
                candidate = candidate_bytes(self.original, trial_id)
                self.assertEqual(candidate, self.original.replace(b"default=0.75", b"default="+radius, 1)
                                 .replace(b"default=0.08", b"default="+bevel, 1))
                self.assertEqual(inverse_bytes(candidate, self.original, trial_id), self.original)
                hashes.add(sha(candidate))
                with isolated_trial(self.root / trial_id, trial_id) as tx:
                    self.assertEqual(tx.read_verified("original"), self.original)
                    tx.apply()
                    self.assertEqual(tx.read_verified("candidate"), candidate)
                    tx.restore()
                    self.assertEqual(tx.read_verified("restored"), self.original)
                self.assertEqual((self.root / trial_id / COPY_NAME).read_bytes(), self.original)
        self.assertEqual(len(hashes), 4)
        self.assertEqual(candidate_bytes(self.original, "target"), r27_candidate(self.original))

    def test_wrong_source_unknown_trial_and_extra_edits_rejected(self):
        for bad in ("unknown", None, True, 1):
            with self.assertRaises(ValueError):
                candidate_bytes(self.original, bad)
        for bad in (self.original+b"\n", self.original.replace(b"\n", b"\r\n"),
                    candidate_bytes(self.original, "target")):
            with self.assertRaises(ValueError):
                candidate_bytes(bad, "intermediate")
        for trial_id in TRIAL_IDS:
            candidate = candidate_bytes(self.original, trial_id)
            for bad in (candidate+b"\n", candidate.replace(b"segments=24", b"segments=25"),
                        candidate_bytes(self.original, next(t for t in TRIAL_IDS if t != trial_id))):
                with self.assertRaises(ValueError):
                    inverse_bytes(bad, self.original, trial_id)

    def test_only_fixed_cross_part_allows_second_change(self):
        cross = candidate_bytes(self.original, "cross_part")
        for trial_id in ("target", "intermediate", "wrong_direction"):
            with self.assertRaises(ValueError):
                inverse_bytes(cross, self.original, trial_id)
        self.assertEqual(inverse_bytes(cross, self.original, "cross_part"), self.original)

    def test_failure_and_corruption_recover_each_trial(self):
        for trial_id in TRIAL_IDS:
            folder = self.root / trial_id
            with self.assertRaisesRegex(RuntimeError, "controlled"):
                with isolated_trial(folder, trial_id) as tx:
                    tx.apply()
                    raise RuntimeError("controlled")
            self.assertEqual((folder / COPY_NAME).read_bytes(), self.original)
            with self.assertRaises(FileExistsError):
                with isolated_trial(folder, trial_id):
                    self.fail("reuse forbidden")
            other = self.root / (trial_id + "_corrupt")
            with self.assertRaises(ValueError):
                with isolated_trial(other, trial_id) as tx:
                    tx.apply()
                    tx.path.write_bytes(tx.candidate+b"\n")
                    tx.read_verified("candidate")
            self.assertEqual((other / COPY_NAME).read_bytes(), self.original)
        self.assertEqual(self.source.read_bytes(), self.original)
