"""R13 / EXT-001: pin known reference inventory and fail closed on path/read races.

All observations here are *test-only* review candidates, not a release API.
Only synthetic temporary checkouts and CBDK-authored ZIP previews are used.
No packaged code is imported, executed, installed, or published.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import stat
import subprocess
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import test_extension_source_reference_round10 as r10
import test_extension_source_reference_round12 as r12

from cbdk.extension_preflight import MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS

COMMIT = "ab42913d300efd003450027a2697586e15ca76ad"
SECRET = "synthetic-private-r13-must-never-appear"


def _unknown(status: str) -> dict:
    """Safe, path-free review-only result. Never turn unknown into approval."""
    return {
        "status": status,
        "source_authenticity_verified": False,
        "owner_consent_verified": False,
        "license_compatibility_verified": False,
        "redistribution_authorized": False,
        "official_blender_extension_validate_ran": False,
        "python_code_executed": False,
        "release_authorized": False,
    }


def _bounded_inventory(references: object) -> bool:
    if (not isinstance(references, dict) or
            not 1 <= len(references) <= MAX_MEMBERS):
        return False
    total = 0
    for name, raw in references.items():
        if (not isinstance(name, str) or
                len(name) > 160 or
                not isinstance(raw, bytes) or len(raw) > MAX_ENTRY_BYTES):
            return False
        total += len(raw)
        if total > MAX_ARCHIVE_BYTES:
            return False
    return True


def _compare_frozen_basis(archive: Path, references: dict,
                          recorded: object, independent_basis: object) -> dict:
    """Basis is independently frozen by the caller; the ZIP cannot elect it.

    A commit string on its own is insufficient: the inventory digest and
    normalization policy have to agree with that same frozen observation.
    Check all of this *before* opening the ZIP.
    """
    if (not _bounded_inventory(references) or
            not isinstance(independent_basis, dict) or
            set(independent_basis) != {"commit", "normalization", "inventory_sha256"} or
            not isinstance(recorded, dict) or recorded != independent_basis):
        return _unknown("inconclusive_reference_basis")
    try:
        actual = r12.snapshot_basis(references, independent_basis["commit"])
    except (ValueError, TypeError):
        return _unknown("inconclusive_reference_basis")
    if actual != independent_basis:
        return _unknown("inconclusive_reference_basis")
    try:
        report = r10._compare_bounded_preview(archive, references)
    except (ValueError, OSError):
        return _unknown("inconclusive_reference_source")
    return report


def _reparse_or_link(path: Path) -> bool:
    """Check *each* component, not just the final .py symlink.

    On Windows a junction is a reparse point, not necessarily a symlink.
    """
    try:
        metadata = os.lstat(path)
    except OSError:
        return True
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse
    )


def _fingerprint(info) -> tuple:
    """File identity/size and two modification clocks, not trust evidence."""
    return (info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _stable_reference_read(
    source_rel: str, *, requested_root: Path, pinned_root: Path,
    after_read=None,
) -> tuple[str, bytes | None]:
    """Test-only bounded read of *only* an exact allowlisted repo-relative name.

    Authoritative root is provided independently of the archive. Caller root
    may be a Windows case/8.3 spelling alias after canonical resolution, but
    may not itself be a symlink/junction. Every source path component must be
    free of reparse points, and the resolved leaf must remain within root.

    A changed file between read and final check is INCONCLUSIVE, not matched.
    No file contents or paths appear in status on any failure.
    """
    if not isinstance(source_rel, str) or source_rel not in r10.ALLOWLISTED_REPO_SOURCES:
        return "inconclusive_reference_path", None
    try:
        pinned = Path(pinned_root).resolve(strict=True)
        requested = Path(requested_root)
        if _reparse_or_link(requested):
            return "inconclusive_reference_path", None
        if requested.resolve(strict=True) != pinned:
            return "inconclusive_reference_path", None
        relative = Path(source_rel)
        candidate = pinned
        for component in relative.parts:
            candidate = candidate / component
            if _reparse_or_link(candidate):
                return "inconclusive_reference_path", None
        if not candidate.resolve(strict=True).is_relative_to(pinned):
            return "inconclusive_reference_path", None
        before = os.stat(candidate, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ENTRY_BYTES:
            return "inconclusive_reference_path", None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags)
        # Close the handle *before* the deterministic change-after-read probe:
        # on Windows, a second writer may be denied while this handle is open.
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _fingerprint(before) != _fingerprint(opened):
                return "inconclusive_reference_changed", None
            raw = stream.read(MAX_ENTRY_BYTES + 1)
        if after_read is not None:
            after_read()
        final = os.stat(candidate, follow_symlinks=False)
        if (len(raw) > MAX_ENTRY_BYTES or
                _fingerprint(before) != _fingerprint(final)):
            return "inconclusive_reference_changed", None
        if _reparse_or_link(candidate):
            return "inconclusive_reference_path", None
        return "stable_repo_bytes", raw.replace(b"\r\n", b"\n")
    except (OSError, ValueError, TypeError):
        return "inconclusive_reference_path", None


class R13FrozenReferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = r10.ExtensionSourceReferenceRound10Tests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work.resolve()
        self.root = (self.work / "R13 Synthetic Checkout Long Name").resolve()
        self.root.mkdir()
        self.source = sorted(r10.ALLOWLISTED_REPO_SOURCES)[0]
        self.path = self.root / self.source
        self.path.parent.mkdir(parents=True)
        self.initial = b"# " + SECRET.encode("ascii") + b"\r\n"
        self.path.write_bytes(self.initial)

    def report_is_unauthorized(self, report):
        for field in ("source_authenticity_verified", "owner_consent_verified",
                      "license_compatibility_verified", "redistribution_authorized",
                      "official_blender_extension_validate_ran",
                      "python_code_executed", "release_authorized"):
            self.assertFalse(report[field], field)
        self.assertNotIn(SECRET, str(report))
        self.assertNotIn(str(self.work), str(report))

    def references(self, archive):
        with ZipFile(archive) as stream:
            package = r10.inspect_preview_archive(archive)["package_id"]
            included = {item.removeprefix(package + "/") for item in stream.namelist()}
        return r10._current_reference_snapshot(package, included)

    def test_r13_same_commit_with_different_inventory_fails_before_zip_read(self):
        archive = self.fixture.build("modular_all")
        original = self.references(archive)
        frozen = r12.snapshot_basis(original, COMMIT)
        first = next(iter(original))
        changed = dict(original, **{first: original[first] + b"\n# synthetic changed source"})
        alternate = r12.snapshot_basis(changed, COMMIT)
        self.assertEqual(frozen["commit"], alternate["commit"])
        self.assertNotEqual(frozen["inventory_sha256"], alternate["inventory_sha256"])
        for data, recorded in ((changed, frozen), (changed, alternate), (original, alternate)):
            with self.subTest(case=recorded["inventory_sha256"][:6]):
                with patch.object(Path, "open", side_effect=AssertionError("forbidden archive read")):
                    result = _compare_frozen_basis(archive, data, recorded, frozen)
                self.assertEqual(result["status"], "inconclusive_reference_basis")
                self.report_is_unauthorized(result)
        good = _compare_frozen_basis(archive, original, frozen, frozen)
        self.assertEqual(good["status"], "same_known_repo_bytes")
        self.report_is_unauthorized(good)

    def test_r13_unknown_commit_or_normalization_is_never_promoted(self):
        archive = self.fixture.build("mesh_inspector")
        references = self.references(archive)
        frozen = r12.snapshot_basis(references, COMMIT)
        wrong = (
            None, {}, {"commit": COMMIT}, "untrusted",
            dict(frozen, commit="0" * 40),
            dict(frozen, commit="UNKNOWN"),
            dict(frozen, normalization="unknown-policy"),
            dict(frozen, inventory_sha256="0" * 64),
            dict(frozen, ignored_extra=True),
        )
        for snapshot in wrong:
            with self.subTest(snapshot=repr(snapshot)[:40]):
                with patch.object(Path, "open", side_effect=AssertionError("forbidden archive read")):
                    result = _compare_frozen_basis(archive, references, snapshot, frozen)
                self.assertEqual(result["status"], "inconclusive_reference_basis")
                self.report_is_unauthorized(result)

    def test_r13_oversize_unknown_or_partial_inventory_is_fail_closed(self):
        archive = self.fixture.build("mesh_inspector")
        references = self.references(archive)
        frozen = r12.snapshot_basis(references, COMMIT)
        first = next(iter(references))
        for candidate in ({},
                          dict(references, **{"unknown/private.py": b"unauthorized"}),
                          dict(references, **{first: b"x" * (MAX_ENTRY_BYTES + 1)}),
                          dict(references, **{first: "non-bytes"}),
                          dict(references, **{first: references[first] + b"x"})):
            with self.subTest(keys=len(candidate)):
                with patch.object(Path, "open", side_effect=AssertionError("forbidden archive read")):
                    response = _compare_frozen_basis(archive, candidate, frozen, frozen)
                self.assertEqual(response["status"], "inconclusive_reference_basis")
                self.report_is_unauthorized(response)

    def test_r13_changed_source_between_read_and_final_stat_is_inconclusive(self):
        def mutate():
            self.path.write_bytes(self.initial + b"# updated during observation\n")
        status, data = _stable_reference_read(
            self.source, requested_root=self.root,
            pinned_root=self.root, after_read=mutate,
        )
        self.assertEqual(status, "inconclusive_reference_changed")
        self.assertIsNone(data)
        self.assertNotIn(SECRET, status)
        self.assertNotIn(str(self.path), status)
        self.assertNotEqual(self.path.read_bytes(), self.initial)

    def test_r13_stable_reference_normalizes_line_endings_without_rewriting(self):
        status, value = _stable_reference_read(
            self.source, requested_root=self.root, pinned_root=self.root,
        )
        self.assertEqual(status, "stable_repo_bytes")
        self.assertEqual(value, self.initial.replace(b"\r\n", b"\n"))
        self.assertEqual(self.path.read_bytes(), self.initial)
        self.assertFalse(r10._compare_to_current_repo(
            self.fixture.build("mesh_inspector"))["release_authorized"])

    def test_r13_disallowed_names_and_other_root_have_zero_content_opens(self):
        values = ("../private/other.py", "./" + self.source,
                  self.source.upper(), self.source.replace("/", "\\"),
                  self.source.replace("/", "/../", 1),
                  "PARTS~1/BLENDER/CONTEXT.PY", "/tmp/secret.py", "")
        for value in values:
            with self.subTest(alias=value):
                with patch.object(os, "open", side_effect=AssertionError("forbidden content open")):
                    state, data = _stable_reference_read(
                        value, requested_root=self.root, pinned_root=self.root)
                self.assertEqual(state, "inconclusive_reference_path")
                self.assertIsNone(data)
        with patch.object(os, "open", side_effect=AssertionError("forbidden other root")):
            state, data = _stable_reference_read(
                self.source, requested_root=self.work, pinned_root=self.root)
        self.assertEqual((state, data), ("inconclusive_reference_path", None))

    def test_r13_leaf_and_parent_symlink_escapes_have_zero_content_opens(self):
        outside = (self.work / "outside-fixture").resolve()
        outside.mkdir()
        leaf_target = outside / "external.py"
        leaf_target.write_bytes(b"# outside leaf marker\n")
        self.path.unlink()
        try:
            self.path.symlink_to(leaf_target)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink privilege unavailable on this host")
        with patch.object(os, "open", side_effect=AssertionError("forbidden source read")):
            self.assertEqual(_stable_reference_read(
                self.source, requested_root=self.root, pinned_root=self.root),
                ("inconclusive_reference_path", None))
        self.path.unlink()
        # A directory-link escape can be detected before a file read.
        parent = self.root / Path(self.source).parts[0]
        import shutil
        shutil.rmtree(parent)
        external_tree = outside / Path(*Path(self.source).parts[1:])
        external_tree.parent.mkdir(parents=True)
        external_tree.write_bytes(b"# outside directory fixture\n")
        parent.symlink_to(outside, target_is_directory=True)
        with patch.object(os, "open", side_effect=AssertionError("forbidden source read")):
            self.assertEqual(_stable_reference_read(
                self.source, requested_root=self.root, pinned_root=self.root),
                ("inconclusive_reference_path", None))
        self.assertEqual(external_tree.read_bytes(), b"# outside directory fixture\n")

    @unittest.skipUnless(os.name == "nt", "Windows junction probe")
    def test_r13_windows_junction_escape_has_zero_content_opens(self):
        self.path.unlink()
        import shutil
        shutil.rmtree(self.root / Path(self.source).parts[0])
        outside = self.work / "junction-outside"
        outside.mkdir()
        dest = outside / Path(*Path(self.source).parts[1:])
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"# synthetic junction payload\n")
        link = self.root / Path(self.source).parts[0]
        process = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
        )
        if process.returncode:
            self.skipTest("Windows junction creation permission unavailable")
        try:
            with patch.object(os, "open", side_effect=AssertionError("forbidden junction content open")):
                result = _stable_reference_read(
                    self.source, requested_root=self.root, pinned_root=self.root)
            self.assertEqual(result, ("inconclusive_reference_path", None))
        finally:
            link.rmdir()
        self.assertEqual(dest.read_bytes(), b"# synthetic junction payload\n")

    @unittest.skipUnless(os.name == "nt", "Windows case alias probe")
    def test_r13_windows_root_case_alias_canonicalizes_but_source_case_denied(self):
        case_alias = Path(str(self.root).swapcase())
        state, data = _stable_reference_read(
            self.source, requested_root=case_alias, pinned_root=self.root)
        self.assertEqual(state, "stable_repo_bytes")
        self.assertEqual(data, self.initial.replace(b"\r\n", b"\n"))
        with patch.object(os, "open", side_effect=AssertionError("forbidden alias content open")):
            state, data = _stable_reference_read(
                self.source.upper(), requested_root=case_alias, pinned_root=self.root)
        self.assertEqual((state, data), ("inconclusive_reference_path", None))

    @unittest.skipUnless(os.name == "nt", "Windows 8.3 short-name probe")
    def test_r13_windows_short_root_alias_is_checked_by_resolved_identity(self):
        winfunc = ctypes.windll.kernel32.GetShortPathNameW
        winfunc.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        winfunc.restype = ctypes.c_uint
        size = winfunc(str(self.root), None, 0)
        if not size:
            self.skipTest("8.3 short-name lookup unavailable")
        buffer = ctypes.create_unicode_buffer(size)
        count = winfunc(str(self.root), buffer, size)
        if not count or count >= size:
            self.skipTest("8.3 short-name conversion unavailable")
        short = Path(buffer.value)
        if str(short).casefold() == str(self.root).casefold():
            self.skipTest("8.3 short names disabled; case-alias test runs separately")
        state, data = _stable_reference_read(
            self.source, requested_root=short, pinned_root=self.root)
        self.assertEqual(state, "stable_repo_bytes")
        self.assertEqual(data, self.initial.replace(b"\r\n", b"\n"))

    def test_r13_known_seven_preview_and_official_rights_gates_remain_blocked(self):
        for recipe in r10.RECIPES:
            with self.subTest(recipe=recipe):
                archive = self.fixture.build(recipe)
                refs = self.references(archive)
                pinned = r12.snapshot_basis(refs, COMMIT)
                result = _compare_frozen_basis(archive, refs, pinned, pinned)
                self.assertEqual(result["status"], "same_known_repo_bytes")
                self.report_is_unauthorized(result)
                self.assertEqual(r10.inspect_preview_archive(
                    archive)["status"], "blocked_for_extension_release")


if __name__ == "__main__":
    unittest.main()
