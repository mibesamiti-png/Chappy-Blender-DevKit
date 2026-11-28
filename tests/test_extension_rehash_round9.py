"""EXT-001 R9: self-consistent ZIP hashes are not proof of author identity.

Every ZIP is assembled from an authored CBDK preview inside a temporary folder.
Changes to packaged helpers add only an inert comment; no source is executed,
imported, installed or published. The updated SHA values are self-asserted.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, SOURCES, build_addon
from cbdk.extension_preflight import diagnose_preview_archive, inspect_preview_archive
from cbdk.modular_builder import HELPERS

RECIPES = (
    "mesh_inspector",
    "modular_all", "modular_combined", "modular_edit",
    "modular_geometry", "modular_nudge", "modular_objects",
)
MARKER = "synthetic_r9_not_an_author_signature"


class ExtensionSelfRehashRound9Tests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def build(self, recipe: str) -> Path:
        path = self.root / (recipe + "-original.zip")
        report = build_addon(ROOT / "recipes" / (recipe + ".json"),
                             path, preview_unapproved=True)
        self.assertTrue(report["preview_only"])
        self.assertFalse(report["approved"])
        self.assertEqual(
            inspect_preview_archive(path)["status"],
            "blocked_for_extension_release",
        )
        return path

    def prepare(self, original: Path):
        """Choose an actually catalogued helper and all dependent part hashes."""
        with ZipFile(original) as archive:
            prefix = archive.namelist()[0].split("/")[0] + "/"
            metadata = json.loads(archive.read(prefix + "CBDK_BUILD_INFO.json"))
            mappings = []
            for part in metadata["parts"]:
                source = part["source"]
                helper = (
                    SOURCES[source] if metadata["schema_version"] == 1
                    else HELPERS[source]
                )
                mappings.append((part, helper))
            helper = sorted({item[1] for item in mappings})[0]
            before = archive.read(prefix + helper)
        # A text-only inert suffix. The test never imports or executes the file.
        after = before + ("\n# " + MARKER + "\n").encode("ascii")
        self.assertNotEqual(before, after)
        original_digest = hashlib.sha256(before).hexdigest()
        changed_digest = hashlib.sha256(after).hexdigest()
        self.assertNotEqual(original_digest, changed_digest)
        self.assertEqual(metadata["files_sha256"][helper], original_digest)
        relevant = [part for part, filename in mappings if filename == helper]
        self.assertTrue(relevant)
        field = "sha256" if metadata["schema_version"] == 1 else "source_sha256"
        self.assertTrue(all(p[field] == original_digest for p in relevant))
        return prefix, metadata, mappings, helper, after, changed_digest, field

    def mutate(self, original: Path, label: str, *,
               inventory: bool, parts: bool, extra_claims: bool = False,
               skip_one_part: bool = False) -> tuple[Path, str]:
        """Repack exact member names with a single changed helper and selected hashes.

        'inventory' and 'parts' independently control the two provenance SHA
        sources. Leaving either out is an intentionally inconsistent ZIP.
        """
        prefix, metadata, mappings, helper, after, changed_sha, field = self.prepare(original)
        if inventory:
            metadata["files_sha256"][helper] = changed_sha
        if parts:
            applicable = [p for p, name in mappings if name == helper]
            for part in applicable[:-1] if skip_one_part else applicable:
                part[field] = changed_sha
        if extra_claims:
            metadata.update({
                "author_consent_verified": True,
                "source_authenticity_verified": True,
                "spdx_compatibility_verified": True,
                "redistribution_authorized": True,
                "official_validator_accepted": True,
                "release_authorized": True,
            })
        target = self.root / (label + ".zip")
        with ZipFile(original) as archive, ZipFile(target, "x") as output:
            for info in archive.infolist():
                if info.filename == prefix + helper:
                    payload = after
                elif info.filename == prefix + "CBDK_BUILD_INFO.json":
                    payload = (json.dumps(metadata, sort_keys=True) + "\n").encode("utf-8")
                else:
                    payload = archive.read(info.filename)
                output.writestr(info, payload)
        self.assertNotEqual(target.read_bytes(), original.read_bytes())
        self.assertTrue(target.is_file())
        return target, helper

    def assert_invalid(self, path: Path, category: str, code: str):
        result = diagnose_preview_archive(path)
        self.assertEqual(result["status"], "invalid_preview_archive")
        self.assertEqual(
            (result["failure_category"], result["failure_code"]),
            (category, code),
        )
        for flag in (
            "provenance_hashes_verified",
            "source_authenticity_verified", "python_code_executed",
            "extension_zip_created", "official_blender_extension_validate_ran",
            "release_authorized",
        ):
            self.assertFalse(result[flag], flag)
        for secret in (MARKER, str(path), str(self.root)):
            self.assertNotIn(secret, json.dumps(result, sort_keys=True))
        with self.assertRaises(ValueError):
            inspect_preview_archive(path)

    def assert_blocked(self, path: Path):
        report = inspect_preview_archive(path)
        self.assertEqual(report, diagnose_preview_archive(path))
        self.assertEqual(report["status"], "blocked_for_extension_release")
        self.assertTrue(report["archive_structure_checked"])
        self.assertTrue(report["provenance_hashes_verified"])
        self.assertTrue(report["preview_only"])
        self.assertFalse(report["source_authenticity_verified"])
        self.assertFalse(report["python_code_executed"])
        self.assertFalse(report["extension_zip_created"])
        self.assertFalse(report["official_blender_extension_validate_ran"])
        self.assertFalse(report["manifest_toml_emitted"])
        self.assertFalse(report.get("release_authorized", False))
        self.assertIsNone(report["manifest_fields_review_only"]["license"])
        self.assertIsNone(report["manifest_fields_review_only"]["maintainer"])
        self.assertFalse(report["manifest_structure_review"]["owner_approval_verified"])
        self.assertFalse(
            report["manifest_structure_review"]["license_registry_or_compatibility_verified"]
        )
        self.assertIn("redistribution_authorization", report["blocker_categories"]["approval"])
        self.assertIn(
            "owner_release_and_redistribution_authorization_required",
            report["blockers"],
        )
        for secret in (MARKER, str(path), str(self.root)):
            self.assertNotIn(secret, json.dumps(report, sort_keys=True))
        return report

    def test_r9_seven_authored_positive_previews_preserved(self):
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                self.assert_blocked(self.build(recipe))

    def test_r9_unsynchronized_helper_change_fails_closed(self):
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                bad, helper = self.mutate(
                    original, recipe + "-unsynced", inventory=False, parts=False,
                )
                self.assertIn("helpers/", helper)
                self.assert_invalid(bad, "archive_integrity", "hash_mismatch")
                self.assert_blocked(original)

    def test_r9_file_inventory_only_rehash_fails_part_provenance(self):
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                bad, _ = self.mutate(
                    original, recipe + "-inventory-only", inventory=True, parts=False,
                )
                self.assert_invalid(bad, "provenance", "part_provenance_mismatch")
                self.assert_blocked(original)

    def test_r9_part_sha_only_rehash_fails_file_inventory(self):
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                bad, _ = self.mutate(
                    original, recipe + "-part-only", inventory=False, parts=True,
                )
                self.assert_invalid(bad, "archive_integrity", "hash_mismatch")
                self.assert_blocked(original)

    def test_r9_self_consistent_rehash_is_integrity_only_not_authenticity(self):
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                self.assert_blocked(original)
                changed, helper = self.mutate(
                    original, recipe + "-fully-rehashed",
                    inventory=True, parts=True,
                )
                self.assertIn("helpers/", helper)
                report = self.assert_blocked(changed)
                self.assertEqual(
                    report["verified_source_file_count"],
                    inspect_preview_archive(original)["verified_source_file_count"],
                )
                self.assertEqual(report["package_id"],
                                 inspect_preview_archive(original)["package_id"])
                with ZipFile(original) as before, ZipFile(changed) as after:
                    full = report["package_id"] + "/" + helper
                    self.assertNotEqual(before.read(full), after.read(full))
                    self.assertIn(MARKER.encode("ascii"), after.read(full))

    def test_r9_rehashed_zip_with_forged_rights_claims_stays_blocked(self):
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                changed, _ = self.mutate(
                    original, recipe + "-rehashed-with-fake-rights",
                    inventory=True, parts=True, extra_claims=True,
                )
                report = self.assert_blocked(changed)
                for false_claim in (
                    "author_consent_verified", "spdx_compatibility_verified",
                    "redistribution_authorized", "official_validator_accepted",
                    "release_authorized",
                ):
                    self.assertNotIn(false_claim, report)
                self.assertFalse(report["source_authenticity_verified"])

    def test_r9_shared_helper_requires_every_part_sha_consistent(self):
        """An inventory update is insufficient if one dependent part is stale."""
        original = self.build("mesh_inspector")
        prefix, metadata, mappings, helper, _, _, _ = self.prepare(original)
        affected = [p for p, filename in mappings if filename == helper]
        self.assertGreaterEqual(len(affected), 2)
        bad, _ = self.mutate(
            original, "legacy-partial-shared-helper",
            inventory=True, parts=True, skip_one_part=True,
        )
        self.assert_invalid(bad, "provenance", "part_provenance_mismatch")
        self.assert_blocked(original)


if __name__ == "__main__":
    unittest.main()
