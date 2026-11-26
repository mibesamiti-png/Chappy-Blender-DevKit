"""R27 C transaction failure controls; no Blender execution in Python tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.parameter_source_r27_copy import (
    SOURCE, SOURCE_SHA256, OLD, NEW, COPY_NAME, candidate_bytes, inverse_bytes, isolated_copy, sha,
)


class R27CopyTests(unittest.TestCase):
    def setUp(self):
        # Windows checkout may convert LF to CRLF. Use only a pinned,
        # canonical LF specimen in the pure unit tests; the actual native
        # execution guard must continue rejecting any nonidentical bytes.
        checkout = SOURCE.read_bytes()
        canonical = checkout.replace(b"\r\n", b"\n")
        self.assertEqual(sha(canonical), SOURCE_SHA256)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = Path(folder.name) / COPY_NAME
        self.source.write_bytes(canonical)
        self.addCleanup(self.assertEqual, SOURCE.read_bytes(), checkout)
        patcher = patch("scripts.parameter_source_r27_copy.SOURCE", self.source)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_native_guard_rejects_crlf_bytes_without_normalization(self):
        original = self.source.read_bytes()
        converted = original.replace(b"\n", b"\r\n")
        self.assertNotEqual(sha(converted), SOURCE_SHA256)
        with self.assertRaisesRegex(ValueError, "fixed source"):
            candidate_bytes(converted)
        self.source.write_bytes(converted)
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "fresh"
            with self.assertRaisesRegex(ValueError, "fixed source"):
                with isolated_copy(work):
                    self.fail("CRLF copy must not be executed")
            self.assertFalse(work.exists())
        self.assertEqual(self.source.read_bytes(), converted)

    def test_pinned_single_change_inverse_and_real_copy(self):
        original = self.source.read_bytes()
        candidate = candidate_bytes(original)
        self.assertEqual(sha(original), SOURCE_SHA256)
        self.assertEqual(candidate, original.replace(OLD, NEW, 1))
        self.assertEqual(inverse_bytes(candidate, original), original)
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "fresh"
            with isolated_copy(work) as tx:
                self.assertEqual(tx.read_verified("original"), original)
                tx.apply()
                self.assertEqual(tx.read_verified("candidate"), candidate)
                tx.restore()
                self.assertEqual(tx.read_verified("restored"), original)
            self.assertEqual((work / COPY_NAME).read_bytes(), original)
            with self.assertRaises(FileExistsError):
                with isolated_copy(work):
                    self.fail("must not use existing directory")
        self.assertEqual(self.source.read_bytes(), original)

    def test_candidate_rejects_altered_original_and_extra_change(self):
        original = self.source.read_bytes()
        candidate = candidate_bytes(original)
        for data in (original + b"\n", original.replace(OLD, NEW), original + OLD):
            with self.subTest(data=sha(data)), self.assertRaises(ValueError):
                candidate_bytes(data)
        for data in (original, candidate + b"\n", candidate.replace(b"default=0.08", b"default=0.09")):
            with self.subTest(data=sha(data)), self.assertRaises(ValueError):
                inverse_bytes(data, original)

    def test_failure_after_apply_restores_actual_copy(self):
        original = self.source.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "fresh"
            with self.assertRaisesRegex(RuntimeError, "controlled"):
                with isolated_copy(work) as tx:
                    tx.apply()
                    raise RuntimeError("controlled")
            self.assertEqual((work / COPY_NAME).read_bytes(), original)
            self.assertEqual(self.source.read_bytes(), original)

    def test_corrupt_candidate_refused_before_execution_and_recovered(self):
        original = self.source.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "fresh"
            with self.assertRaisesRegex(ValueError, "differs"):
                with isolated_copy(work) as tx:
                    tx.apply()
                    tx.path.write_bytes(tx.candidate + b"\n")
                    tx.read_verified("candidate")
            self.assertEqual((work / COPY_NAME).read_bytes(), original)
