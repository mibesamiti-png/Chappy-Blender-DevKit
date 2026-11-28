"""EXT-001 R10: compare preview bytes against a fixed, separate repo snapshot.

Test-only review probes, NOT a public trust API or release gate. Repository
sources stay read-only; only CBDK-authored ZIP fixtures enter this suite.
Packaged Python is never imported, executed, installed or distributed.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, SOURCES, build_addon
from cbdk.extension_preflight import (
    MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS,
    diagnose_preview_archive, inspect_preview_archive,
)
from cbdk.feature_catalog import TRUSTED_FEATURES
from cbdk.modular_builder import HELPERS

FIXED_REPO_ROOT = ROOT.resolve()
MARKER = "private_r10_synthetic_source_delta"
RECIPES = (
    "mesh_inspector", "modular_all", "modular_combined",
    "modular_edit", "modular_geometry", "modular_nudge", "modular_objects",
)
PACKAGE_SOURCES = {
    "cbdk_mesh_inspector_preview": {
        output: source for source, output in SOURCES.items()
    },
    "cbdk_modular_preview": {
        **{output: source for source, output in HELPERS.items()},
        **{
            "features/" + feature_id + ".py": definition["source"]
            for feature_id, definition in TRUSTED_FEATURES.items()
        },
    },
}
ALLOWLISTED_REPO_SOURCES = frozenset(
    source for source_map in PACKAGE_SOURCES.values() for source in source_map.values()
)


def _read_fixed_repository_source(source_rel: str, *, root: Path = FIXED_REPO_ROOT) -> bytes:
    """Reject alternate roots/paths; read <=2MiB only from known CBDK sources."""
    if (not isinstance(source_rel, str) or
            source_rel not in ALLOWLISTED_REPO_SOURCES or
            Path(root).resolve() != FIXED_REPO_ROOT):
        raise ValueError("Source is not in the fixed repository allowlist")
    path = FIXED_REPO_ROOT / source_rel
    if (path.is_symlink() or not path.is_file()
            or not path.resolve().is_relative_to(FIXED_REPO_ROOT)
            or path.stat().st_size > MAX_ENTRY_BYTES):
        raise ValueError("Known source is missing or unsafe")
    with path.open("rb") as stream:
        raw = stream.read(MAX_ENTRY_BYTES + 1)
    if len(raw) > MAX_ENTRY_BYTES:
        raise ValueError("Known source exceeds byte limit")
    return raw.replace(b"\r\n", b"\n")


def _current_reference_snapshot(package: str, included: set[str]) -> dict[str, bytes]:
    """Map only present helper/feature members, not templates or private data."""
    mapping = PACKAGE_SOURCES[package]
    keys = sorted(included & mapping.keys())
    if not keys or len(keys) > MAX_MEMBERS:
        raise ValueError("No bounded source comparison inventory")
    return {name: _read_fixed_repository_source(mapping[name]) for name in keys}


def _compare_bounded_preview(archive_path: Path, references: dict[str, bytes]) -> dict:
    """Test-only static comparison; hashes are NOT authentication or consent."""
    preflight = inspect_preview_archive(archive_path)
    if preflight["status"] != "blocked_for_extension_release":
        raise ValueError("Only a structurally valid development preview can be compared")
    if (not archive_path.is_file() or archive_path.is_symlink()
            or archive_path.stat().st_size > MAX_ARCHIVE_BYTES):
        raise ValueError("Invalid source ZIP")
    package = preflight["package_id"]
    mapping = PACKAGE_SOURCES[package]
    with ZipFile(archive_path) as archive:
        included = {
            name.removeprefix(package + "/") for name in archive.namelist()
            if name.startswith(package + "/")
        }
        expected = included & mapping.keys()
        if (not expected or len(expected) > MAX_MEMBERS
                or set(references) != expected):
            raise ValueError("Reference snapshot does not match bounded inventory")
        differences = 0
        for member in sorted(expected):
            trusted_bytes = references[member]
            if not isinstance(trusted_bytes, bytes) or len(trusted_bytes) > MAX_ENTRY_BYTES:
                raise ValueError("Oversize or unsafe reference value")
            with archive.open(package + "/" + member) as stream:
                member_bytes = stream.read(MAX_ENTRY_BYTES + 1)
            if len(member_bytes) > MAX_ENTRY_BYTES:
                raise ValueError("ZIP member exceeds static comparison limit")
            differences += member_bytes != trusted_bytes
    return {
        "status": "same_known_repo_bytes" if differences == 0 else "different_known_repo_bytes",
        "entries_compared": len(expected),
        "entries_different": differences,
        "reference_is_independent_of_zip_metadata": True,
        "source_authenticity_verified": False,
        "owner_consent_verified": False,
        "license_compatibility_verified": False,
        "redistribution_authorized": False,
        "official_blender_extension_validate_ran": False,
        "python_code_executed": False,
        "release_authorized": False,
    }


def _compare_to_current_repo(archive_path: Path) -> dict:
    """Bind the report to a separately read, current checkout reference."""
    preflight = inspect_preview_archive(archive_path)
    package = preflight["package_id"]
    with ZipFile(archive_path) as archive:
        included = {
            name.removeprefix(package + "/") for name in archive.namelist()
            if name.startswith(package + "/")
        }
    return _compare_bounded_preview(
        archive_path, _current_reference_snapshot(package, included)
    )


class ExtensionSourceReferenceRound10Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)

    def build(self, recipe: str) -> Path:
        output = self.work / (recipe + "-preview.zip")
        built = build_addon(
            FIXED_REPO_ROOT / "recipes" / (recipe + ".json"),
            output, preview_unapproved=True,
        )
        self.assertTrue(built["preview_only"])
        self.assertFalse(built["approved"])
        return output

    def mutate(self, original: Path, recipe: str, *,
               inventory_hash: bool, part_hashes: bool) -> tuple[Path, str, bytes]:
        """Change only an inert helper comment and selected self-declared SHA."""
        with ZipFile(original) as source:
            prefix = source.namelist()[0].split("/")[0] + "/"
            raw_info = source.read(prefix + "CBDK_BUILD_INFO.json")
            metadata = json.loads(raw_info)
            map_by_source = SOURCES if metadata["schema_version"] == 1 else HELPERS
            mapping = PACKAGE_SOURCES[prefix[:-1]]
            helper = sorted(name for name in mapping if name.startswith("helpers/")
                            and prefix + name in source.namelist())[0]
            changed = source.read(prefix + helper) + ("\n# " + MARKER + "\n").encode("ascii")
            self.assertLessEqual(len(changed), MAX_ENTRY_BYTES)
            changed_sha = hashlib.sha256(changed).hexdigest()
            if inventory_hash:
                metadata["files_sha256"][helper] = changed_sha
            if part_hashes:
                field = "sha256" if metadata["schema_version"] == 1 else "source_sha256"
                for part in metadata["parts"]:
                    if map_by_source[part["source"]] == helper:
                        part[field] = changed_sha
            target = self.work / (recipe + f"-inv{inventory_hash}-parts{part_hashes}.zip")
            with ZipFile(target, "x") as output:
                for info in source.infolist():
                    data = (
                        changed if info.filename == prefix + helper else
                        (json.dumps(metadata, sort_keys=True) + "\n").encode("utf-8")
                        if info.filename == prefix + "CBDK_BUILD_INFO.json" else
                        source.read(info.filename)
                    )
                    output.writestr(info, data)
        self.assertNotEqual(original.read_bytes(), target.read_bytes())
        return target, helper, changed

    def assert_sanitized_and_blocked(self, report: dict):
        self.assertFalse(report["source_authenticity_verified"])
        self.assertFalse(report["owner_consent_verified"])
        self.assertFalse(report["license_compatibility_verified"])
        self.assertFalse(report["redistribution_authorized"])
        self.assertFalse(report["official_blender_extension_validate_ran"])
        self.assertFalse(report["python_code_executed"])
        self.assertFalse(report["release_authorized"])
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn(MARKER, serialized)
        self.assertNotIn(str(self.work), serialized)
        self.assertNotIn(str(FIXED_REPO_ROOT), serialized)

    def test_r10_all_seven_known_recipes_equal_current_repo_sources(self):
        """Compare actual repository bytes, never the ZIP's SHA dictionary."""
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                preflight = inspect_preview_archive(original)
                self.assertEqual(preflight["status"], "blocked_for_extension_release")
                self.assertTrue(preflight["provenance_hashes_verified"])
                report = _compare_to_current_repo(original)
                self.assertEqual(report["status"], "same_known_repo_bytes")
                self.assertGreater(report["entries_compared"], 0)
                self.assertEqual(report["entries_different"], 0)
                self.assert_sanitized_and_blocked(report)

    def test_r10_unupdated_tamper_is_rejected_before_reference_comparison(self):
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                changed, _, _ = self.mutate(
                    original, recipe, inventory_hash=False, part_hashes=False
                )
                rejected = diagnose_preview_archive(changed)
                self.assertEqual(rejected["status"], "invalid_preview_archive")
                self.assertEqual(rejected["failure_code"], "hash_mismatch")
                with self.assertRaises(ValueError):
                    _compare_to_current_repo(changed)
                self.assert_sanitized_and_blocked(_compare_to_current_repo(original))

    def test_r10_self_rehashed_preview_differs_from_current_repo_bytes(self):
        """Self-consistency is not equivalence with separate checked-out sources."""
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                changed, helper, changed_payload = self.mutate(
                    original, recipe, inventory_hash=True, part_hashes=True
                )
                self.assertTrue(inspect_preview_archive(changed)["provenance_hashes_verified"])
                self.assertEqual(
                    inspect_preview_archive(changed)["status"],
                    "blocked_for_extension_release",
                )
                result = _compare_to_current_repo(changed)
                self.assertEqual(result["status"], "different_known_repo_bytes")
                self.assertEqual(result["entries_different"], 1)
                self.assert_sanitized_and_blocked(result)
                self.assertNotEqual(
                    changed_payload,
                    _read_fixed_repository_source(PACKAGE_SOURCES[
                        inspect_preview_archive(changed)["package_id"]
                    ][helper]),
                )

    def test_r10_updated_reference_positive_is_only_synthetic_snapshot(self):
        """Hypothetical repository change is modeled *in memory*, not written."""
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                package = inspect_preview_archive(original)["package_id"]
                with ZipFile(original) as z:
                    present = {name.removeprefix(package + "/") for name in z.namelist()}
                trusted_before = _current_reference_snapshot(package, present)
                changed, helper, changed_payload = self.mutate(
                    original, recipe, inventory_hash=True, part_hashes=True,
                )
                simulated_after = dict(trusted_before, **{helper: changed_payload})
                actual_report = _compare_bounded_preview(changed, trusted_before)
                self.assertEqual(actual_report["status"], "different_known_repo_bytes")
                hypothetical_report = _compare_bounded_preview(changed, simulated_after)
                self.assertEqual(hypothetical_report["status"], "same_known_repo_bytes")
                self.assertEqual(hypothetical_report["entries_different"], 0)
                self.assert_sanitized_and_blocked(hypothetical_report)
                # This is a synthetic test snapshot, not an alternate trusted root.
                self.assertEqual(_compare_to_current_repo(changed)["status"],
                                 "different_known_repo_bytes")

    def test_r10_unknown_root_and_traversal_path_are_not_reference_sources(self):
        for source in (
            "../input_sources_private/secret.py", "/private/source.py",
            "parts/blender/../hidden.py", "unknown/placeholder.py",
            "templates/modular_preview/other.py",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "allowlist"):
                    _read_fixed_repository_source(source)
        real = sorted(ALLOWLISTED_REPO_SOURCES)[0]
        with self.assertRaisesRegex(ValueError, "allowlist"):
            _read_fixed_repository_source(real, root=self.work)
        self.assertFalse(any(self.work.iterdir()))

    def test_r10_reference_inventory_and_size_must_be_bounded(self):
        original = self.build("mesh_inspector")
        package = inspect_preview_archive(original)["package_id"]
        with ZipFile(original) as z:
            present = {name.removeprefix(package + "/") for name in z.namelist()}
        reference = _current_reference_snapshot(package, present)
        first = next(iter(reference))
        for altered in (
            {},
            dict(reference, **{"unapproved.py": b"not permitted"}),
            dict(reference, **{first: b"X" * (MAX_ENTRY_BYTES + 1)}),
            dict(reference, **{first: "not bytes"}),
        ):
            with self.subTest(change=len(altered)):
                with self.assertRaises(ValueError):
                    _compare_bounded_preview(original, altered)
        good = _compare_bounded_preview(original, reference)
        self.assertEqual(good["status"], "same_known_repo_bytes")
        self.assert_sanitized_and_blocked(good)

    def test_r10_repo_source_bytes_are_never_modified(self):
        """Cross-compare preserves the known reference byte-for-byte."""
        source = sorted(ALLOWLISTED_REPO_SOURCES)[0]
        path = FIXED_REPO_ROOT / source
        before = path.read_bytes()
        original = self.build("modular_all")
        _compare_to_current_repo(original)
        changed, _, _ = self.mutate(original, "modular_all", inventory_hash=True, part_hashes=True)
        _compare_to_current_repo(changed)
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(path.is_file())

    def test_r10_no_source_comparison_claims_license_or_official_validation(self):
        original = self.build("modular_all")
        baseline = _compare_to_current_repo(original)
        changed, _, _ = self.mutate(original, "modular_all", inventory_hash=True, part_hashes=True)
        divergent = _compare_to_current_repo(changed)
        for report in (baseline, divergent):
            self.assert_sanitized_and_blocked(report)
            self.assertTrue(report["reference_is_independent_of_zip_metadata"])
            self.assertNotIn("license_verified", report)
            self.assertNotIn("approved", report)
            self.assertNotIn("author_signature_valid", report)
        self.assertEqual(inspect_preview_archive(original)["status"],
                         "blocked_for_extension_release")
        self.assertEqual(inspect_preview_archive(changed)["status"],
                         "blocked_for_extension_release")


if __name__ == "__main__":
    unittest.main()
