"""EXT-001 R14: bounded handle-anchored reference review probes.

TEST-ONLY security research: this is neither a public source-reading API nor
an authenticator, license checker or Extension publishing permission. All
paths and payloads below are generated under disposable synthetic checkouts.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_extension_source_reference_round10 as r10
import test_extension_source_reference_round12 as r12
import test_extension_source_reference_round13 as r13

from cbdk.extension_preflight import MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS

PRIVATE_MARKER = "synthetic_r14_private_value_must_not_leak"
REASON_CODES = frozenset({
    "reference_bytes_observed",
    "inconclusive_reference_basis",
    "inconclusive_reference_path",
    "inconclusive_reference_changed",
    "inconclusive_reference_limit",
    "inconclusive_platform_handle_guarantee",
})


def _review_only(reason: str, *, opened: int = 0, read: int = 0) -> dict:
    """Only stable codes and bounded counters; never log a value or filename."""
    assert reason in REASON_CODES
    return {
        "status": "review_only" if reason == "reference_bytes_observed" else "inconclusive",
        "reason_code": reason,
        "content_opens": opened,
        "bytes_read": read,
        "source_authenticity_verified": False,
        "owner_consent_verified": False,
        "license_compatibility_verified": False,
        "redistribution_authorized": False,
        "signature_verified": False,
        "official_blender_extension_validate_ran": False,
        "python_code_executed": False,
        "release_authorized": False,
        "unverified_reason_codes": (
            "source_origin_unverified",
            "owner_consent_unverified",
            "license_rights_unverified",
            "redistribution_unverified",
            "release_authorization_unverified",
        ),
    }


def _identity(info) -> tuple:
    """Stat identity and clocks are a change detector, never an attestation."""
    return (
        info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode),
        info.st_size, info.st_mtime_ns, info.st_ctime_ns,
    )


def _anchored_reference_probe(
    root_fd: int | None,
    expected_root: tuple[int, int] | None,
    source_rel: str,
    *,
    before_open=None,
    after_read=None,
) -> tuple[dict, bytes | None]:
    """Prototype: openat-style dirfd walk; no untrusted absolute path opening.

    The *trusted caller* must already have pinned a directory descriptor.
    On Windows, Python's ordinary os.open does not establish the necessary
    no-reparse handle-relative guarantees: fail closed without content I/O.
    """
    if not isinstance(source_rel, str) or source_rel not in r10.ALLOWLISTED_REPO_SOURCES:
        return _review_only("inconclusive_reference_path"), None
    if (
        os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or
        not hasattr(os, "O_DIRECTORY") or
        os.open not in os.supports_dir_fd or
        os.stat not in os.supports_dir_fd
    ):
        return _review_only("inconclusive_platform_handle_guarantee"), None
    if (
        not isinstance(root_fd, int) or isinstance(root_fd, bool) or root_fd < 0 or
        not isinstance(expected_root, tuple) or len(expected_root) != 2 or
        any(not isinstance(i, int) or isinstance(i, bool) for i in expected_root)
    ):
        return _review_only("inconclusive_reference_basis"), None
    try:
        actual_root = os.fstat(root_fd)
        if (
            not stat.S_ISDIR(actual_root.st_mode) or
            (actual_root.st_dev, actual_root.st_ino) != expected_root
        ):
            return _review_only("inconclusive_reference_basis"), None
    except (OSError, ValueError):
        return _review_only("inconclusive_reference_basis"), None

    current = None
    opened = 0
    read = 0
    try:
        current = os.dup(root_fd)
        parts = Path(source_rel).parts
        # source_rel is an exact allowlisted POSIX-style spelling. No source
        # component is allowed to be a symlink, junction or arbitrary alias.
        for index, component in enumerate(parts):
            leaf = index == len(parts) - 1
            before = os.stat(component, dir_fd=current, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                return _review_only("inconclusive_reference_path", opened=opened), None
            if leaf and (not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ENTRY_BYTES):
                return _review_only(
                    "inconclusive_reference_limit" if before.st_size > MAX_ENTRY_BYTES
                    else "inconclusive_reference_path", opened=opened
                ), None
            if not leaf and not stat.S_ISDIR(before.st_mode):
                return _review_only("inconclusive_reference_path", opened=opened), None

            # A deterministic race hook runs after the vulnerable precheck,
            # before opening the entry. The open is *relative to the held fd*
            # and rejects a new symlink even if the pathname now resolves out.
            if before_open is not None:
                before_open(index, component)
            flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            if leaf:
                flags |= getattr(os, "O_NONBLOCK", 0)
            else:
                flags |= os.O_DIRECTORY
            next_fd = os.open(component, flags, dir_fd=current)
            try:
                opened_info = os.fstat(next_fd)
                if _identity(before) != _identity(opened_info):
                    return _review_only("inconclusive_reference_changed", opened=opened), None
                if leaf:
                    if (
                        not stat.S_ISREG(opened_info.st_mode) or
                        opened_info.st_size > MAX_ENTRY_BYTES
                    ):
                        return _review_only("inconclusive_reference_limit", opened=opened), None
                    opened += 1
                    chunk = os.read(next_fd, MAX_ENTRY_BYTES + 1)
                    read = len(chunk)
                    if after_read is not None:
                        after_read()
                    final = os.fstat(next_fd)
                    if read > MAX_ENTRY_BYTES:
                        return _review_only("inconclusive_reference_limit", opened=opened, read=read), None
                    if _identity(opened_info) != _identity(final):
                        return _review_only("inconclusive_reference_changed", opened=opened, read=read), None
                    return _review_only("reference_bytes_observed", opened=opened, read=read), chunk.replace(b"\r\n", b"\n")
                os.close(current)
                current = next_fd
                next_fd = None
            finally:
                if next_fd is not None:
                    os.close(next_fd)
    except (OSError, ValueError, TypeError):
        return _review_only("inconclusive_reference_path", opened=opened, read=read), None
    finally:
        if current is not None:
            os.close(current)
    return _review_only("inconclusive_reference_path", opened=opened, read=read), None


class R14HandleBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name).resolve()
        self.root = self.work / "r14-synthetic-pinned-checkout"
        self.root.mkdir()
        self.rel = "parts/blender/context.py"
        self.assertIn(self.rel, r10.ALLOWLISTED_REPO_SOURCES)
        self.source = self.root / self.rel
        self.source.parent.mkdir(parents=True)
        self.payload = ("# " + PRIVATE_MARKER + "\r\n").encode("ascii")
        self.source.write_bytes(self.payload)

    def _pin(self):
        if os.name != "posix":
            return None, None
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.addCleanup(os.close, fd)
        info = os.fstat(fd)
        return fd, (info.st_dev, info.st_ino)

    def _assert_false_rights(self, result):
        for flag in (
            "source_authenticity_verified", "owner_consent_verified",
            "license_compatibility_verified", "redistribution_authorized",
            "signature_verified", "official_blender_extension_validate_ran",
            "python_code_executed", "release_authorized"
        ):
            self.assertFalse(result[flag], flag)
        for sentinel in (PRIVATE_MARKER, str(self.root), str(self.source)):
            self.assertNotIn(sentinel, str(result))
        self.assertLessEqual(result["bytes_read"], MAX_ENTRY_BYTES + 1)
        self.assertLessEqual(result["content_opens"], 1)
        self.assertEqual(len(result["unverified_reason_codes"]), 5)

    def test_r14_known_good_static_pinned_fd_normalizes_without_mutation(self):
        fd, identity = self._pin()
        result, raw = _anchored_reference_probe(fd, identity, self.rel)
        if os.name == "posix":
            self.assertEqual(result["reason_code"], "reference_bytes_observed")
            self.assertEqual(result["content_opens"], 1)
            self.assertEqual(raw, self.payload.replace(b"\r\n", b"\n"))
            self.assertEqual(result["bytes_read"], len(self.payload))
        else:
            self.assertEqual(result["reason_code"], "inconclusive_platform_handle_guarantee")
            self.assertIsNone(raw)
            self.assertEqual(result["content_opens"], 0)
        self.assertEqual(self.source.read_bytes(), self.payload)
        self._assert_false_rights(result)

    def test_r14_unknown_source_alias_and_root_fd_rejected_without_open(self):
        fd, identity = self._pin()
        for rel in (
            "../secret.py", "./" + self.rel, self.rel.upper(),
            self.rel.replace("/", "\\"), "PARTS~1/BLENDER/CONTEXT.PY",
            "/absolute/private.py", "private/" + PRIVATE_MARKER,
        ):
            with self.subTest(rel=rel):
                with patch.object(os, "open", side_effect=AssertionError("must not open")):
                    result, raw = _anchored_reference_probe(fd, identity, rel)
                self.assertEqual(result["reason_code"], "inconclusive_reference_path")
                self.assertIsNone(raw)
                self.assertEqual(result["content_opens"], 0)
                self._assert_false_rights(result)
        if os.name == "posix":
            with patch.object(os, "open", side_effect=AssertionError("wrong root")):
                result, raw = _anchored_reference_probe(
                    fd, (identity[0], identity[1] + 1), self.rel)
            self.assertEqual(result["reason_code"], "inconclusive_reference_basis")
            self.assertIsNone(raw)

    @unittest.skipUnless(os.name == "posix", "Requires POSIX dirfd O_NOFOLLOW")
    def test_r14_parent_symlink_swap_after_precheck_reads_zero_external_bytes(self):
        fd, identity = self._pin()
        external = self.work / "external-only"
        target = external / "blender" / "context.py"
        target.parent.mkdir(parents=True)
        secret = b"EXTERNAL-PRIVATE-CONTENT-R14"
        target.write_bytes(secret)
        original_parent = self.root / "parts"
        stashed = self.root / "parts-pinned-old"
        invoked = []
        content_reads = []
        real_read = os.read

        def hook(index, component):
            if index == 0:
                invoked.append(component)
                original_parent.rename(stashed)
                original_parent.symlink_to(external, target_is_directory=True)

        def spy_read(descriptor, count):
            content_reads.append(count)
            return real_read(descriptor, count)

        with patch.object(os, "read", side_effect=spy_read):
            result, raw = _anchored_reference_probe(
                fd, identity, self.rel, before_open=hook)
        self.assertEqual(invoked, ["parts"])
        self.assertEqual(content_reads, [])
        self.assertIsNone(raw)
        self.assertEqual(result["content_opens"], 0)
        self.assertIn(result["reason_code"], (
            "inconclusive_reference_path", "inconclusive_reference_changed"))
        self.assertEqual(target.read_bytes(), secret)
        self._assert_false_rights(result)

    @unittest.skipUnless(os.name == "posix", "Requires POSIX dirfd O_NOFOLLOW")
    def test_r14_leaf_symlink_swap_after_precheck_reads_zero_external_bytes(self):
        fd, identity = self._pin()
        outside = self.work / "leaf-private"
        outside.write_bytes(b"EXTERNAL-PRIVATE-CONTENT-R14")
        stash = self.source.with_name("context-original.py")
        reads = []
        real_read = os.read

        def hook(index, component):
            if index == len(Path(self.rel).parts) - 1:
                self.source.rename(stash)
                self.source.symlink_to(outside)

        with patch.object(os, "read", side_effect=lambda f, size: (
                reads.append(size), real_read(f, size))[1]):
            result, raw = _anchored_reference_probe(
                fd, identity, self.rel, before_open=hook)
        self.assertEqual(reads, [])
        self.assertIsNone(raw)
        self.assertEqual(result["content_opens"], 0)
        self.assertIn(result["reason_code"], (
            "inconclusive_reference_path", "inconclusive_reference_changed"))
        self._assert_false_rights(result)

    @unittest.skipUnless(os.name == "posix", "Requires POSIX dirfd O_NOFOLLOW")
    def test_r14_equal_size_and_mtime_replacement_fails_before_content_read(self):
        fd, identity = self._pin()
        before = self.source.stat()
        alternate = self.work / "r14-other-inode"
        alternate.write_bytes(b"X" * len(self.payload))
        os.utime(alternate, ns=(before.st_atime_ns, before.st_mtime_ns))
        reads = []
        real_read = os.read

        def hook(index, component):
            if index == len(Path(self.rel).parts) - 1:
                os.replace(alternate, self.source)

        with patch.object(os, "read", side_effect=lambda f, n: (
                reads.append(n), real_read(f, n))[1]):
            result, raw = _anchored_reference_probe(
                fd, identity, self.rel, before_open=hook)
        self.assertEqual(result["reason_code"], "inconclusive_reference_changed")
        self.assertIsNone(raw)
        self.assertEqual(reads, [])
        self.assertEqual(result["content_opens"], 0)
        self._assert_false_rights(result)

    @unittest.skipUnless(os.name == "posix", "Requires POSIX dirfd O_NOFOLLOW")
    def test_r14_inplace_rewrite_after_bounded_read_is_unknown_not_approved(self):
        fd, identity = self._pin()
        def rewrite():
            self.source.write_bytes(self.payload + b"# AFTER-READ-R14\n")
        result, raw = _anchored_reference_probe(
            fd, identity, self.rel, after_read=rewrite)
        self.assertEqual(result["reason_code"], "inconclusive_reference_changed")
        self.assertIsNone(raw)
        self.assertEqual(result["content_opens"], 1)
        self._assert_false_rights(result)

    @unittest.skipUnless(os.name == "posix", "Requires POSIX dirfd O_NOFOLLOW")
    def test_r14_source_size_exact_cap_and_over_cap_no_unbounded_read(self):
        fd, identity = self._pin()
        self.source.write_bytes(b"Q" * MAX_ENTRY_BYTES)
        accepted, raw = _anchored_reference_probe(fd, identity, self.rel)
        self.assertEqual(accepted["reason_code"], "reference_bytes_observed")
        self.assertEqual(accepted["bytes_read"], MAX_ENTRY_BYTES)
        self.assertEqual(len(raw), MAX_ENTRY_BYTES)
        self._assert_false_rights(accepted)

        self.source.write_bytes(b"Q" * (MAX_ENTRY_BYTES + 1))
        with patch.object(os, "read", side_effect=AssertionError("oversize read")):
            denied, data = _anchored_reference_probe(fd, identity, self.rel)
        self.assertEqual(denied["reason_code"], "inconclusive_reference_limit")
        self.assertIsNone(data)
        self.assertEqual(denied["content_opens"], 0)
        self._assert_false_rights(denied)

    @unittest.skipUnless(os.name == "posix", "Requires POSIX pinned dirfd")
    def test_r14_symlinked_root_name_after_pinning_does_not_redirect_fd(self):
        fd, identity = self._pin()
        original = self.work / "r14-original-root-renamed"
        external = self.work / "r14-external-root"
        leaf = external / self.rel
        leaf.parent.mkdir(parents=True)
        leaf.write_bytes(b"PRIVATE-EXTERNAL-R14")
        self.root.rename(original)
        self.root.symlink_to(external, target_is_directory=True)
        result, raw = _anchored_reference_probe(fd, identity, self.rel)
        self.assertEqual(result["reason_code"], "reference_bytes_observed")
        self.assertEqual(raw, self.payload.replace(b"\r\n", b"\n"))
        self.assertEqual(leaf.read_bytes(), b"PRIVATE-EXTERNAL-R14")
        self._assert_false_rights(result)
        # A held FD protects the original inode; it is NOT an origin signature.

    @unittest.skipUnless(os.name == "nt", "Windows native junction capability")
    def test_r14_windows_junction_swap_no_python_handle_authority(self):
        """Native junction fixture; Windows test-only probe MUST refuse reads."""
        folder = self.root / "parts"
        outside = self.work / "r14-win-external"
        outside.mkdir()
        (outside / "blender").mkdir()
        (outside / "blender" / "context.py").write_bytes(b"private-foreign-data")
        saved = self.root / "parts-saved"
        folder.rename(saved)
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(folder), str(outside)],
            capture_output=True,
        )
        if result.returncode:
            self.skipTest("Windows junction creation capability unavailable")
        try:
            with patch.object(os, "open", side_effect=AssertionError("no Windows content open")):
                report, data = _anchored_reference_probe(None, None, self.rel)
            self.assertEqual(report["reason_code"], "inconclusive_platform_handle_guarantee")
            self.assertEqual(report["content_opens"], 0)
            self.assertIsNone(data)
            self._assert_false_rights(report)
        finally:
            folder.rmdir()

    def test_r14_unverified_reason_codes_and_existing_seven_preview_controls(self):
        for reason in REASON_CODES:
            self._assert_false_rights(_review_only(reason))
        for recipe in r10.RECIPES:
            with self.subTest(recipe=recipe):
                with tempfile.TemporaryDirectory() as td:
                    output = Path(td) / "preview.zip"
                    from cbdk.addon_builder import ROOT, build_addon
                    build_addon(
                        ROOT / "recipes" / (recipe + ".json"),
                        output, preview_unapproved=True)
                    report = r10.inspect_preview_archive(output)
                    self.assertEqual(report["status"], "blocked_for_extension_release")
                    self.assertTrue(report["provenance_hashes_verified"])
                    self.assertFalse(report["source_authenticity_verified"])
                    self.assertFalse(report.get("release_authorized", False))
        self.assertEqual((MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS),
                         (16 * 1024 * 1024, 2 * 1024 * 1024, 64))


if __name__ == "__main__":
    unittest.main()
