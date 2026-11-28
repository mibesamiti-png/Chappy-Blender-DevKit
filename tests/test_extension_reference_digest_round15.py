"""EXT-001 R15: same-inode metadata replay and independently pinned digest limits.

Only synthetic, temporary sources and known CBDK-authored ZIP previews.
This module is TEST-ONLY, not a trusted production reader or release API.
No private/untrusted addon code is opened, imported, installed or executed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import test_extension_reference_race_round14 as r14
import test_extension_source_reference_round10 as r10
from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_preflight import (
    MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS,
    inspect_preview_archive,
)

# These are observation-only labels. They never assert an authenticated
# commit, signed origin, copyright clearance or current filesystem stability.
RESULT_CODES = frozenset({
    "inconclusive_reference_basis",
    "inconclusive_reference_freshness",
    "observed_bytes_equal_independent_digest",
    "observed_bytes_different_independent_digest",
}) | r14.REASON_CODES


def _digest_review(
    pinned_fd: int | None,
    root_identity: tuple[int, int] | None,
    source_rel: str,
    *,
    independent_digest: str | None = None,
    before_open=None,
    after_read=None,
) -> dict:
    """Bounded comparison to a test-harness-held digest, never ZIP metadata.

    The caller's prior digest is an *independent reference assumption*. This
    function cannot authenticate the caller/commit or establish that an
    in-place, same-inode file remained current after its bytes were sampled.
    In particular, any supplied after-read mutation hook forces inconclusive.
    """
    if (
        not isinstance(independent_digest, str) or
        len(independent_digest) != 64 or
        any(letter not in "0123456789abcdef" for letter in independent_digest)
    ):
        return r14._review_only("inconclusive_reference_basis")

    report, observed = r14._anchored_reference_probe(
        pinned_fd, root_identity, source_rel,
        before_open=before_open, after_read=after_read,
    )
    if report["reason_code"] != "reference_bytes_observed" or observed is None:
        return report

    checked = dict(report)
    if after_read is not None:
        # The test deliberately introduced a potentially undetectable
        # mutation. A metadata-equal stat does not make it safe to report
        # a *current* source match; drop sampled bytes, never approve.
        checked["status"] = "inconclusive"
        checked["reason_code"] = "inconclusive_reference_freshness"
        return checked

    matched = hashlib.sha256(observed).hexdigest() == independent_digest
    checked["reason_code"] = (
        "observed_bytes_equal_independent_digest" if matched else
        "observed_bytes_different_independent_digest"
    )
    # Even a byte match is only an observation relative to a caller-held
    # digest. The canonical source identity/rights flags remain false.
    checked["status"] = "review_only"
    return checked


class R15DigestLimitsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name).resolve()
        self.root = self.work / "synthetic-r15-checkout"
        self.root.mkdir()
        self.rel = "parts/blender/context.py"
        self.assertIn(self.rel, r10.ALLOWLISTED_REPO_SOURCES)
        self.source = self.root / self.rel
        self.source.parent.mkdir(parents=True)
        self.original = b"# " + b"A" * 48 + b"\r\n"
        self.changed = b"# " + b"B" * 48 + b"\r\n"
        self.assertEqual(len(self.original), len(self.changed))
        self.source.write_bytes(self.original)
        self.prior_digest = hashlib.sha256(
            self.original.replace(b"\r\n", b"\n")
        ).hexdigest()

    def pin(self):
        if os.name != "posix":
            return None, None
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.addCleanup(os.close, fd)
        info = os.fstat(fd)
        return fd, (info.st_dev, info.st_ino)

    def assert_no_authority(self, result):
        self.assertIn(result["reason_code"], RESULT_CODES)
        for key in (
            "source_authenticity_verified", "owner_consent_verified",
            "license_compatibility_verified", "redistribution_authorized",
            "signature_verified", "official_blender_extension_validate_ran",
            "python_code_executed", "release_authorized",
        ):
            self.assertFalse(result[key], key)
        for private in (str(self.work), str(self.root), str(self.source),
                        "synthetic-r15-checkout", self.prior_digest):
            self.assertNotIn(private, repr(result))
        self.assertLessEqual(result["content_opens"], 1)
        self.assertLessEqual(result["bytes_read"], MAX_ENTRY_BYTES + 1)

    def test_r15_missing_prior_digest_refuses_before_any_source_read(self):
        fd, identity = self.pin()
        for digest in (None, "", "0" * 63, "f" * 65, "G" * 64, 4, b"0" * 64):
            with self.subTest(digest_type=type(digest).__name__):
                with patch.object(
                    r14, "_anchored_reference_probe",
                    side_effect=AssertionError("must not open source")
                ):
                    result = _digest_review(fd, identity, self.rel,
                                            independent_digest=digest)
                self.assertEqual(result["reason_code"],
                                 "inconclusive_reference_basis")
                self.assertEqual(result["content_opens"], 0)
                self.assertEqual(result["bytes_read"], 0)
                self.assert_no_authority(result)

    def test_r15_prior_digest_match_is_only_observed_normalized_bytes(self):
        fd, identity = self.pin()
        observed = _digest_review(
            fd, identity, self.rel, independent_digest=self.prior_digest)
        if os.name == "posix":
            self.assertEqual(observed["reason_code"],
                             "observed_bytes_equal_independent_digest")
            self.assertEqual(observed["content_opens"], 1)
            self.assertEqual(observed["bytes_read"], len(self.original))
        else:
            self.assertEqual(observed["reason_code"],
                             "inconclusive_platform_handle_guarantee")
            self.assertEqual(observed["content_opens"], 0)
        self.assert_no_authority(observed)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_r15_bad_pinned_root_and_unknown_path_fail_without_content(self):
        fd, identity = self.pin()
        for bad in ("../private.py", "./" + self.rel, self.rel.upper(),
                    "PARTS~1/BLENDER/CONTEXT.PY", "/absolute/private.py"):
            with self.subTest(name=bad):
                with patch.object(os, "read",
                                  side_effect=AssertionError("read denied")):
                    result = _digest_review(
                        fd, identity, bad, independent_digest=self.prior_digest)
                self.assertEqual(result["reason_code"],
                                 "inconclusive_reference_path")
                self.assertEqual(result["content_opens"], 0)
                self.assert_no_authority(result)
        if os.name == "posix":
            with patch.object(os, "read",
                              side_effect=AssertionError("read denied")):
                result = _digest_review(
                    fd, (identity[0], identity[1] + 1), self.rel,
                    independent_digest=self.prior_digest)
            self.assertEqual(result["reason_code"],
                             "inconclusive_reference_basis")
            self.assert_no_authority(result)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r15_same_inode_same_size_mtime_restored_is_detected_by_ctime(self):
        fd, identity = self.pin()
        before = self.source.stat()
        real_read = os.read
        reads = []

        def rewrite(index, component):
            if component == "context.py":
                self.source.write_bytes(self.changed)
                os.utime(self.source,
                         ns=(before.st_atime_ns, before.st_mtime_ns))

        def spy_read(handle, count):
            reads.append(count)
            return real_read(handle, count)

        with patch.object(os, "read", side_effect=spy_read):
            result = _digest_review(
                fd, identity, self.rel, independent_digest=self.prior_digest,
                before_open=rewrite)
        self.assertEqual(result["reason_code"],
                         "inconclusive_reference_changed")
        self.assertEqual(reads, [])
        self.assertEqual(result["content_opens"], 0)
        after = self.source.stat()
        self.assertEqual(after.st_ino, before.st_ino)
        self.assertEqual(after.st_size, before.st_size)
        self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(self.source.read_bytes(), self.changed)
        self.assert_no_authority(result)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r15_simulated_stat_replay_needs_independent_digest(self):
        """A forged ctime/stat view demonstrates an actual detection limit.

        We do NOT claim to restore ctime on a real filesystem: test-patch the
        metadata comparator and preserve inode/size/mtime in actual fixture.
        """
        fd, identity = self.pin()
        before = self.source.stat()

        def rewrite(index, component):
            if component == "context.py":
                self.source.write_bytes(self.changed)
                os.utime(self.source,
                         ns=(before.st_atime_ns, before.st_mtime_ns))

        def metadata_without_ctime(info):
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

        with patch.object(r14, "_identity",
                          side_effect=metadata_without_ctime):
            reviewed = _digest_review(
                fd, identity, self.rel, independent_digest=self.prior_digest,
                before_open=rewrite)
        self.assertEqual(reviewed["reason_code"],
                         "observed_bytes_different_independent_digest")
        self.assertEqual(reviewed["content_opens"], 1)
        self.assert_no_authority(reviewed)
        self.assertEqual(self.source.read_bytes(), self.changed)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r15_same_stat_replay_without_prior_digest_stays_unknown(self):
        fd, identity = self.pin()
        before = self.source.stat()

        def rewrite(index, component):
            if component == "context.py":
                self.source.write_bytes(self.changed)
                os.utime(self.source,
                         ns=(before.st_atime_ns, before.st_mtime_ns))

        with patch.object(r14, "_anchored_reference_probe",
                          side_effect=AssertionError("must reject pre-read")):
            report = _digest_review(
                fd, identity, self.rel, independent_digest=None,
                before_open=rewrite)
        self.assertEqual(report["reason_code"],
                         "inconclusive_reference_basis")
        self.assertEqual(report["content_opens"], 0)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assert_no_authority(report)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r15_after_read_same_inode_mutation_is_inconclusive(self):
        fd, identity = self.pin()
        before = self.source.stat()

        def change_after_read():
            self.source.write_bytes(self.changed)
            os.utime(self.source,
                     ns=(before.st_atime_ns, before.st_mtime_ns))

        with patch.object(r14, "_identity",
                          side_effect=lambda s:
                          (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)):
            # Metadata replay can make R14's observed bytes *look* stable.
            # With the deterministic mutation hook known, the R15 wrapper
            # refuses to claim even a current-source byte match.
            result = _digest_review(
                fd, identity, self.rel, independent_digest=self.prior_digest,
                after_read=change_after_read)
        self.assertEqual(result["reason_code"],
                         "inconclusive_reference_freshness")
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["content_opens"], 1)
        self.assert_no_authority(result)
        self.assertEqual(self.source.read_bytes(), self.changed)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r15_identical_difference_cannot_distinguish_drift_from_tamper(self):
        fd, identity = self.pin()
        reasons = []
        for source_context in ("legitimate-synthetic-update",
                               "synthetic-unauthorized-edit"):
            self.source.write_bytes(self.changed)
            report = _digest_review(
                fd, identity, self.rel, independent_digest=self.prior_digest)
            reasons.append(report["reason_code"])
            self.assert_no_authority(report)
            self.assertNotIn(source_context, str(report))
        self.assertEqual(reasons, [
            "observed_bytes_different_independent_digest",
            "observed_bytes_different_independent_digest",
        ])

    def test_r15_2mib_limit_and_windows_handle_refusal_unchanged(self):
        fd, identity = self.pin()
        self.source.write_bytes(b"Z" * (MAX_ENTRY_BYTES + 1))
        with patch.object(os, "read",
                          side_effect=AssertionError("oversize denied")):
            report = _digest_review(
                fd, identity, self.rel, independent_digest=self.prior_digest)
        self.assertEqual(report["content_opens"], 0)
        self.assertEqual(report["reason_code"],
                         "inconclusive_reference_limit" if os.name == "posix"
                         else "inconclusive_platform_handle_guarantee")
        self.assert_no_authority(report)
        self.assertEqual((MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS),
                         (16 * 1024 * 1024, 2 * 1024 * 1024, 64))

    def test_r15_all_seven_preview_zips_remain_blocked(self):
        for recipe in r10.RECIPES:
            with self.subTest(recipe=recipe):
                dest = self.work / (recipe + ".zip")
                build_addon(ROOT / "recipes" / (recipe + ".json"),
                            dest, preview_unapproved=True)
                result = inspect_preview_archive(dest)
                self.assertEqual(result["status"],
                                 "blocked_for_extension_release")
                self.assertTrue(result["provenance_hashes_verified"])
                self.assertFalse(result["source_authenticity_verified"])
                self.assertFalse(result.get("release_authorized", False))


if __name__ == "__main__":
    unittest.main()
