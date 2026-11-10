"""R16 EXT-001: bounded two-observation blind spots, synthetic fixtures only.

Test-only exploratory reviewer. A pair of equal reads does not establish
stability during the gap, present-file freshness, source authenticity, owner
consent, or permission to distribute a Blender Extension.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import test_extension_reference_race_round14 as r14
import test_extension_reference_digest_round15 as r15
import test_extension_source_reference_round10 as r10

from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_preflight import (
    MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS, inspect_preview_archive,
)

MAX_SAMPLES = 2
MAX_OBSERVED_BYTES = MAX_SAMPLES * (MAX_ENTRY_BYTES + 1)
MAX_REVIEW_MILLISECONDS = 30_000
R16_REASONS = frozenset({
    "observed_two_samples_match_prior_digest",
    "inconclusive_sample_disagreement",
    "inconclusive_prior_digest_mismatch",
    "inconclusive_gap_mutation",
    "inconclusive_review_budget",
}) | r15.RESULT_CODES


def _reason_only(code: str, *samples: dict) -> dict:
    """Aggregate bounded counts. NEVER embed source/digest/path in a report."""
    assert code in R16_REASONS
    positive = code == "observed_two_samples_match_prior_digest"
    result = r14._review_only(
        "reference_bytes_observed" if positive else "inconclusive_reference_basis",
        opened=sum(x["content_opens"] for x in samples),
        read=sum(x["bytes_read"] for x in samples),
    )
    result.update({
        "status": "review_only" if positive else "inconclusive",
        "reason_code": code,
        "samples_attempted": len(samples),
        "sample_gap_stability_verified": False,
        "current_source_stability_verified": False,
        "independent_reference_origin_verified": False,
    })
    return result


def _two_sample_review(
    pinned_fd: int | None,
    expected_root: tuple[int, int] | None,
    source_rel: str,
    *,
    prior_digest: object,
    between_samples=None,
    max_review_ms: int = MAX_REVIEW_MILLISECONDS,
) -> dict:
    """Two R15 observations, bounded, from the same synthetic pinned root.

    The prior digest must come from a separate test-harness snapshot, NOT
    the ZIP's self-declared inventory. No sample reports current stability.
    An explicitly injected gap edit is conservatively INCONCLUSIVE even
    if bytes are restored before the second sample. Unobserved edits can
    evade both samples, which is precisely the R16 limitation under test.
    """
    if (
        not isinstance(source_rel, str) or
        source_rel not in r10.ALLOWLISTED_REPO_SOURCES
    ):
        return _reason_only("inconclusive_reference_path")
    if (
        not isinstance(prior_digest, str) or len(prior_digest) != 64 or
        any(char not in "0123456789abcdef" for char in prior_digest)
    ):
        return _reason_only("inconclusive_reference_basis")
    if (
        not isinstance(max_review_ms, int) or isinstance(max_review_ms, bool) or
        not 1 <= max_review_ms <= MAX_REVIEW_MILLISECONDS
    ):
        return _reason_only("inconclusive_review_budget")

    started = time.monotonic_ns()
    allowed_ns = max_review_ms * 1_000_000

    first = r15._digest_review(
        pinned_fd, expected_root, source_rel, independent_digest=prior_digest)
    if first["reason_code"] not in (
        "observed_bytes_equal_independent_digest",
        "observed_bytes_different_independent_digest",
    ):
        return _reason_only(first["reason_code"], first)
    if (
        first["bytes_read"] > MAX_ENTRY_BYTES + 1 or
        time.monotonic_ns() - started >= allowed_ns
    ):
        return _reason_only("inconclusive_review_budget", first)

    # This callback is only injected by controlled tests, never obtained
    # from a ZIP or an untrusted addon. Its existence is itself evidence
    # that an edit occurred between samples.
    known_gap_edit = between_samples is not None
    if between_samples is not None:
        try:
            between_samples()
        except OSError:
            return _reason_only("inconclusive_gap_mutation", first)

    if time.monotonic_ns() - started >= allowed_ns:
        return _reason_only("inconclusive_review_budget", first)

    second = r15._digest_review(
        pinned_fd, expected_root, source_rel, independent_digest=prior_digest)
    samples = (first, second)
    if (
        sum(x["bytes_read"] for x in samples) > MAX_OBSERVED_BYTES or
        sum(x["content_opens"] for x in samples) > MAX_SAMPLES or
        time.monotonic_ns() - started >= allowed_ns
    ):
        return _reason_only("inconclusive_review_budget", *samples)
    if second["reason_code"] not in (
        "observed_bytes_equal_independent_digest",
        "observed_bytes_different_independent_digest",
    ):
        return _reason_only(second["reason_code"], *samples)

    observed = (first["reason_code"], second["reason_code"])
    if observed[0] != observed[1]:
        return _reason_only("inconclusive_sample_disagreement", *samples)
    if known_gap_edit:
        return _reason_only("inconclusive_gap_mutation", *samples)
    if observed[0] != "observed_bytes_equal_independent_digest":
        return _reason_only("inconclusive_prior_digest_mismatch", *samples)
    return _reason_only("observed_two_samples_match_prior_digest", *samples)


class R16TwoSampleLimitsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name).resolve()
        self.root = self.work / "synthetic-r16-checkout"
        self.root.mkdir()
        self.rel = "parts/blender/context.py"
        self.assertIn(self.rel, r10.ALLOWLISTED_REPO_SOURCES)
        self.file = self.root / self.rel
        self.file.parent.mkdir(parents=True)
        self.initial = b"# " + b"P" * 40 + b"\r\n"
        self.other = b"# " + b"Q" * 40 + b"\r\n"
        self.assertEqual(len(self.initial), len(self.other))
        self.file.write_bytes(self.initial)
        self.prior = hashlib.sha256(
            self.initial.replace(b"\r\n", b"\n")
        ).hexdigest()

    def pinned(self):
        if os.name != "posix":
            return None, None
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.addCleanup(os.close, fd)
        info = os.fstat(fd)
        return fd, (info.st_dev, info.st_ino)

    def assert_not_authorized(self, result):
        self.assertIn(result["reason_code"], R16_REASONS)
        for flag in (
            "source_authenticity_verified", "owner_consent_verified",
            "license_compatibility_verified", "redistribution_authorized",
            "signature_verified", "official_blender_extension_validate_ran",
            "python_code_executed", "release_authorized",
            "sample_gap_stability_verified",
            "current_source_stability_verified",
            "independent_reference_origin_verified",
        ):
            self.assertFalse(result[flag], flag)
        self.assertLessEqual(result["samples_attempted"], MAX_SAMPLES)
        self.assertLessEqual(result["content_opens"], MAX_SAMPLES)
        self.assertLessEqual(result["bytes_read"], MAX_OBSERVED_BYTES)
        for secret in (str(self.work), str(self.file), self.prior,
                       "synthetic-r16-checkout"):
            self.assertNotIn(secret, repr(result))

    def test_r16_missing_independent_reference_and_unknown_path_never_read(self):
        fd, identity = self.pinned()
        for digest in (None, "not-a-hash", "A" * 64, "0" * 63, b"0" * 64):
            with self.subTest(digest=type(digest).__name__):
                with patch.object(
                    r15, "_digest_review",
                    side_effect=AssertionError("invalid digest must not read"),
                ):
                    report = _two_sample_review(
                        fd, identity, self.rel, prior_digest=digest)
                self.assertEqual(report["reason_code"],
                                 "inconclusive_reference_basis")
                self.assertEqual(report["samples_attempted"], 0)
                self.assert_not_authorized(report)
        for name in ("../private/secret.py", "./" + self.rel,
                     self.rel.upper(), "PARTS~1/BLENDER/CONTEXT.PY",
                     "/absolute/private.py"):
            with self.subTest(name=name):
                with patch.object(
                    r15, "_digest_review",
                    side_effect=AssertionError("unknown path must not read"),
                ):
                    report = _two_sample_review(
                        fd, identity, name, prior_digest=self.prior)
                self.assertEqual(report["reason_code"],
                                 "inconclusive_reference_path")
                self.assertEqual(report["content_opens"], 0)
                self.assert_not_authorized(report)

    def test_r16_no_race_two_equal_samples_never_prove_current_stability(self):
        fd, identity = self.pinned()
        result = _two_sample_review(fd, identity, self.rel, prior_digest=self.prior)
        if os.name == "posix":
            self.assertEqual(result["reason_code"],
                             "observed_two_samples_match_prior_digest")
            self.assertEqual(result["samples_attempted"], 2)
            self.assertEqual(result["content_opens"], 2)
            self.assertEqual(result["bytes_read"], 2 * len(self.initial))
        else:
            self.assertEqual(result["reason_code"],
                             "inconclusive_platform_handle_guarantee")
            self.assertEqual(result["samples_attempted"], 1)
            self.assertEqual(result["content_opens"], 0)
        self.assert_not_authorized(result)
        self.assertEqual(self.file.read_bytes(), self.initial)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r16_changed_between_samples_remains_unknown(self):
        fd, identity = self.pinned()
        before = self.file.stat()
        invoked = []

        def edit_gap():
            invoked.append("gap")
            self.file.write_bytes(self.other)
            os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))

        result = _two_sample_review(
            fd, identity, self.rel, prior_digest=self.prior,
            between_samples=edit_gap)
        self.assertEqual(invoked, ["gap"])
        self.assertEqual(result["reason_code"],
                         "inconclusive_sample_disagreement")
        self.assertEqual(result["samples_attempted"], 2)
        self.assertEqual(result["content_opens"], 2)
        self.assert_not_authorized(result)
        self.assertEqual(self.file.read_bytes(), self.other)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r16_restoration_between_samples_is_invisible_without_event_evidence(self):
        """Two real R15 reads agree even if a same-inode edit happened in between."""
        fd, identity = self.pinned()
        first = r15._digest_review(
            fd, identity, self.rel, independent_digest=self.prior)
        before = self.file.stat()
        self.file.write_bytes(self.other)
        os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))
        transient = self.file.read_bytes()
        self.assertEqual(transient, self.other)
        self.file.write_bytes(self.initial)
        os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))
        second = r15._digest_review(
            fd, identity, self.rel, independent_digest=self.prior)
        self.assertEqual(first["reason_code"],
                         "observed_bytes_equal_independent_digest")
        self.assertEqual(second["reason_code"],
                         "observed_bytes_equal_independent_digest")
        self.assertFalse(first["source_authenticity_verified"])
        self.assertFalse(second["release_authorized"])
        self.assertEqual(self.file.read_bytes(), self.initial)
        # Even with equal independent SHA-256 observations, no sample
        # captured the temporary Q bytes. Without trusted event evidence
        # the time between observations is not authenticated.

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r16_injected_change_and_restore_gap_returns_unknown_not_equal(self):
        fd, identity = self.pinned()
        before = self.file.stat()
        seen = []

        def edit_and_restore():
            self.file.write_bytes(self.other)
            os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))
            seen.append(self.file.read_bytes())
            self.file.write_bytes(self.initial)
            os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))

        result = _two_sample_review(
            fd, identity, self.rel, prior_digest=self.prior,
            between_samples=edit_and_restore)
        self.assertEqual(seen, [self.other])
        self.assertEqual(result["reason_code"], "inconclusive_gap_mutation")
        self.assertEqual(result["samples_attempted"], 2)
        self.assertEqual(result["content_opens"], 2)
        self.assert_not_authorized(result)
        self.assertEqual(self.file.read_bytes(), self.initial)

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r16_changed_before_both_samples_cannot_be_attributed(self):
        fd, identity = self.pinned()
        self.file.write_bytes(self.other)
        result = _two_sample_review(fd, identity, self.rel,
                                    prior_digest=self.prior)
        self.assertEqual(result["reason_code"],
                         "inconclusive_prior_digest_mismatch")
        self.assertEqual(result["samples_attempted"], 2)
        self.assert_not_authorized(result)
        # Same report for lawful repository source update and malicious
        # change, so a mismatch cannot identify either origin or intent.

    @unittest.skipUnless(os.name == "posix", "POSIX pinned dirfd required")
    def test_r16_change_after_second_sample_is_not_detected_by_prior_report(self):
        fd, identity = self.pinned()
        result = _two_sample_review(fd, identity, self.rel,
                                    prior_digest=self.prior)
        self.assertEqual(result["reason_code"],
                         "observed_two_samples_match_prior_digest")
        self.file.write_bytes(self.other)
        self.assertEqual(self.file.read_bytes(), self.other)
        self.assert_not_authorized(result)
        self.assertFalse(result["current_source_stability_verified"])

    def test_r16_review_time_budget_or_invalid_budget_fails_before_open(self):
        fd, identity = self.pinned()
        for max_ms in (None, 0, -1, True, 30_001, "30"):
            with self.subTest(max_ms=max_ms):
                with patch.object(
                    r15, "_digest_review",
                    side_effect=AssertionError("invalid budget must not read"),
                ):
                    result = _two_sample_review(
                        fd, identity, self.rel,
                        prior_digest=self.prior, max_review_ms=max_ms)
                self.assertEqual(result["reason_code"],
                                 "inconclusive_review_budget")
                self.assertEqual(result["samples_attempted"], 0)
                self.assert_not_authorized(result)

    def test_r16_platform_restrictions_and_stale_pinned_root_fail_closed(self):
        fd, identity = self.pinned()
        with patch.object(
            os, "read", side_effect=AssertionError("must not read on invalid root"),
        ):
            result = _two_sample_review(
                fd, (identity[0], identity[1] + 1)
                if os.name == "posix" else None,
                self.rel, prior_digest=self.prior)
        self.assertEqual(
            result["reason_code"],
            "inconclusive_reference_basis" if os.name == "posix"
            else "inconclusive_platform_handle_guarantee")
        self.assertEqual(result["content_opens"], 0)
        self.assert_not_authorized(result)

    def test_r16_all_seven_positive_zips_and_bounds_are_unchanged(self):
        self.assertEqual((MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS),
                         (16 * 1024 * 1024, 2 * 1024 * 1024, 64))
        self.assertEqual(MAX_OBSERVED_BYTES, 2 * (MAX_ENTRY_BYTES + 1))
        for recipe in r10.RECIPES:
            with self.subTest(recipe=recipe):
                output = self.work / (recipe + ".zip")
                build_addon(ROOT / "recipes" / (recipe + ".json"),
                            output, preview_unapproved=True)
                result = inspect_preview_archive(output)
                self.assertEqual(result["status"],
                                 "blocked_for_extension_release")
                self.assertTrue(result["provenance_hashes_verified"])
                self.assertFalse(result["source_authenticity_verified"])
                self.assertFalse(result.get("release_authorized", False))


if __name__ == "__main__":
    unittest.main()
