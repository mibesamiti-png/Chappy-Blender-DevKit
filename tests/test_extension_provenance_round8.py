"""R8 / EXT-001: provenance observations cannot authorize Extension release.

Only CBDK-generated previews and synthetic TOML/validator text are inspected.
No bundled add-on Python is executed, installed, signed or distributed.
"""
from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_manifest import compare_official_validation, review_manifest_fields
from cbdk.extension_manifest_review import review_manifest_file
from cbdk.extension_preflight import diagnose_preview_archive, inspect_preview_archive

RECIPES = (
    "mesh_inspector", "modular_all", "modular_combined",
    "modular_edit", "modular_geometry", "modular_nudge", "modular_objects",
)
PREVIEW_PACKAGE = {
    "mesh_inspector": "cbdk_mesh_inspector_preview",
    "modular_all": "cbdk_modular_preview",
    "modular_combined": "cbdk_modular_preview",
    "modular_edit": "cbdk_modular_preview",
    "modular_geometry": "cbdk_modular_preview",
    "modular_nudge": "cbdk_modular_preview",
    "modular_objects": "cbdk_modular_preview",
}
SYNTHETIC_MARKER = "private_owner_r8@example.invalid"


def _fields():
    """Known bounded TOML subset, NOT a project license or owner decision."""
    return {
        "schema_version": "1.0.0",
        "id": "cbdk_synthetic_fixture",
        "version": "1.2.3",
        "name": "Synthetic fixture",
        "tagline": "Synthetic validation fixture",
        "maintainer": "Synthetic test",
        "type": "add-on",
        "blender_version_min": "4.4.0",
        "license": ["SPDX:GPL-3.0-or-later"],
    }


class ExtensionProvenanceRound8Tests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)

    def build(self, recipe: str) -> Path:
        path = self.root / (recipe + ".zip")
        built = build_addon(
            ROOT / "recipes" / (recipe + ".json"), path,
            preview_unapproved=True,
        )
        self.assertTrue(built["preview_only"])
        self.assertFalse(built["approved"])
        return path

    def rewrite_provenance(self, original: Path, label: str, changes: dict) -> Path:
        """Repackage original verified bytes; metadata is still self-asserted."""
        target = self.root / (label + ".zip")
        with ZipFile(original) as source:
            package = source.namelist()[0].split("/")[0]
            meta = package + "/CBDK_BUILD_INFO.json"
            stored = json.loads(source.read(meta))
            stored.update(changes)
            with ZipFile(target, "x") as out:
                for info in source.infolist():
                    data = (
                        json.dumps(stored, sort_keys=True).encode("utf-8")
                        if info.filename == meta else source.read(info.filename)
                    )
                    out.writestr(info, data)
        return target

    def assert_release_blocked(self, report: dict) -> None:
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
        self.assertEqual(
            report["manifest_structure_review"]["missing_required_fields"],
            ["version", "maintainer", "license"],
        )
        self.assertFalse(report["manifest_structure_review"]["owner_approval_verified"])
        self.assertFalse(
            report["manifest_structure_review"]["license_registry_or_compatibility_verified"]
        )
        self.assertEqual(
            set(report["blocker_categories"]),
            {"owner_metadata", "approval", "packaging", "verification"},
        )
        self.assertIn(
            "owner_release_and_redistribution_authorization_required",
            report["blockers"],
        )
        text = json.dumps(report, sort_keys=True)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn(SYNTHETIC_MARKER, text)

    def test_r8_seven_authored_zip_structural_success_never_grants_rights(self):
        """Positive provenance/hash checks are not consent/license/release."""
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                archive = self.build(recipe)
                report = inspect_preview_archive(archive)
                self.assertEqual(report, diagnose_preview_archive(archive))
                self.assertEqual(report["package_id"], PREVIEW_PACKAGE[recipe])
                self.assert_release_blocked(report)

    def test_r8_self_asserted_approval_metadata_cannot_upgrade_valid_zip(self):
        """Invented authority fields must remain ignored rather than trusted."""
        fabricated = {
            "author_consent_verified": True,
            "owner_release_approved": True,
            "spdx_compatibility_verified": True,
            "license_attribution": SYNTHETIC_MARKER,
            "redistribution_permission_granted": True,
            "official_blender_validator_accepted": True,
            "extension_signature_valid": True,
            "release_authorized": True,
        }
        for recipe in ("mesh_inspector", "modular_all"):
            with self.subTest(recipe=recipe):
                original = self.build(recipe)
                modified = self.rewrite_provenance(
                    original, recipe + "-untrusted-evidence-r8", fabricated,
                )
                result = inspect_preview_archive(modified)
                self.assert_release_blocked(result)
                self.assertEqual(result["package_id"], PREVIEW_PACKAGE[recipe])
                # Nothing in the archive's own JSON can authenticate a claim.
                for key in fabricated:
                    self.assertNotIn(key, result)
                self.assertNotIn(SYNTHETIC_MARKER, json.dumps(result))
                self.assert_release_blocked(inspect_preview_archive(original))

    def test_r8_forged_mandatory_approval_states_fail_closed(self):
        """Legacy and modular flags cannot be flipped to 'release ready'."""
        critical = (
            ("preview_only", False),
            ("approved", True),
            ("redistribution_cleared", True),
            ("blender_runtime_verified_for_this_build", True),
        )
        for recipe in ("mesh_inspector", "modular_all"):
            original = self.build(recipe)
            for key, injected in critical:
                with self.subTest(recipe=recipe, forged=key):
                    modified = self.rewrite_provenance(
                        original, recipe + "-forged-" + key, {key: injected},
                    )
                    result = diagnose_preview_archive(modified)
                    self.assertEqual(result["status"], "invalid_preview_archive")
                    self.assertEqual(
                        (result["failure_category"], result["failure_code"]),
                        ("provenance", "unsafe_approval_flag"),
                    )
                    for flag in (
                        "provenance_hashes_verified",
                        "source_authenticity_verified",
                        "python_code_executed",
                        "extension_zip_created",
                        "official_blender_extension_validate_ran",
                        "release_authorized",
                    ):
                        self.assertFalse(result[flag])
                    self.assertNotIn(str(self.root), json.dumps(result))

    def test_r8_traversal_in_zip_stays_invalid_despite_claims(self):
        original = self.build("modular_all")
        bad_member = "cbdk_modular_preview/helpers/../private_owner_r8.py"
        modified = self.root / "unsafe-private-owner-r8.zip"
        with ZipFile(original) as source, ZipFile(modified, "x") as out:
            for info in source.infolist():
                out.writestr(info, source.read(info.filename))
            # Synthetic file name only; no Python code is imported/executed.
            out.writestr(bad_member, b"synthetic content not executed")
        bad = diagnose_preview_archive(modified)
        self.assertEqual(bad["status"], "invalid_preview_archive")
        self.assertEqual(
            (bad["failure_category"], bad["failure_code"]),
            ("archive_structure", "unsafe_member"),
        )
        self.assertFalse(bad["release_authorized"])
        self.assertFalse(bad["provenance_hashes_verified"])
        self.assertNotIn(bad_member, json.dumps(bad))
        self.assertNotIn(str(modified), json.dumps(bad))

    def test_r8_synthetic_official_validator_agreement_is_not_ownership(self):
        """A plausible/clean text observation is consistency, never trust."""
        preview = inspect_preview_archive(self.build("mesh_inspector"))
        self.assert_release_blocked(preview)
        banners = (
            "Blender 4.4.3",
            "Blender 4.5.15 LTS",
            "Blender 5.2.1 LTS",
        )
        for banner in banners:
            with self.subTest(version=banner):
                text = (
                    banner + "\n"
                    'Success parsing TOML in "/private/private_owner_r8/fixture"\n'
                    "Blender quit\n"
                )
                review = review_manifest_fields(_fields())
                self.assertEqual(review["status"], "structurally_valid_subset")
                self.assertFalse(review["owner_approval_verified"])
                self.assertFalse(review["license_registry_or_compatibility_verified"])
                agreement = compare_official_validation(_fields(), 0, text)
                self.assertEqual(agreement["status"], "agreement")
                self.assertTrue(agreement["complete_diagnostic_agreement"])
                self.assertEqual(agreement["official_observation"]["status"], "accepted")
                self.assertFalse(agreement["official_observation"]["authenticates_log"])
                self.assertFalse(agreement["owner_approval_verified"])
                self.assertFalse(agreement["license_compatibility_verified"])
                self.assertNotIn("private_owner_r8", json.dumps(agreement))
                # Both independent observations exist, but neither grants rights.
                self.assertEqual(preview["status"], "blocked_for_extension_release")
                self.assertFalse(preview.get("release_authorized", False))

    def test_r8_unknown_and_contradictory_official_logs_never_authorize(self):
        """Unknown official text cannot be laundered into agreement."""
        missing_license = {**_fields(), "license": None}
        for output in (
            'Error parsing TOML "synthetic"\nmissing "license"\n'
            "Unexpected private_owner_r8 diagnostic",
            'Error parsing TOML "synthetic"\nmissing "license"\n'
            'key "license" invalid: private_owner_r8 contradictory text',
            'Success parsing TOML in "synthetic"\n'
            'Error parsing TOML "synthetic"\nmissing "license"',
            'Error parsing TOML "synthetic"\nmissing "license"\n'
            'missing "license"',
        ):
            with self.subTest(diagnostic=output[:34]):
                compared = compare_official_validation(missing_license, 1, output)
                self.assertEqual(compared["status"], "unclassified")
                self.assertFalse(compared["complete_diagnostic_agreement"])
                self.assertFalse(compared["owner_approval_verified"])
                self.assertFalse(compared["license_compatibility_verified"])
                self.assertFalse(compared["official_observation"]["authenticates_log"])
                self.assertNotIn("private_owner_r8", json.dumps(compared))

    def test_r8_manifest_owner_and_spdx_claims_are_only_untrusted_text(self):
        """Even valid TOML claims cannot set author/license/release flags."""
        valid = (
            'schema_version = "1.0.0"\n'
            'id = "cbdk_synthetic_fixture"\n'
            'version = "1.2.3"\n'
            'name = "Synthetic fixture"\n'
            'tagline = "Synthetic validation fixture"\n'
            f'maintainer = "{SYNTHETIC_MARKER}"\n'
            'type = "add-on"\n'
            'blender_version_min = "4.4.0"\n'
            'license = ["SPDX:GPL-3.0-or-later"]\n'
        )
        manifest = self.root / "private_owner_r8.toml"
        for claims in (
            "",
            'owner_consent_verified = true\n'
            'redistribution_authorized = true\n'
            'release_authorized = true\n',
            '[private_claims_r8]\n'
            'signature_accepted = "private_owner_r8"\n'
            'license_attribution = "private_owner_r8"\n',
        ):
            with self.subTest(extra_claims=bool(claims)):
                contents = (valid + claims).encode("utf-8")
                manifest.write_bytes(contents)
                report = review_manifest_file(manifest)
                self.assertEqual(report["status"], "review_only")
                self.assertFalse(report["release_authorized"])
                self.assertFalse(report["official_validation_ran"])
                self.assertFalse(report["source_executed"])
                self.assertFalse(report["source_modified"])
                self.assertFalse(report["structure"]["owner_approval_verified"])
                self.assertFalse(
                    report["structure"]["license_registry_or_compatibility_verified"]
                )
                if claims:
                    self.assertIn(
                        "unsupported_field",
                        [row["field"] for row in report["structure"]["errors"]],
                    )
                self.assertNotIn(SYNTHETIC_MARKER, json.dumps(report))
                self.assertNotIn("private_claims_r8", json.dumps(report))
                self.assertNotIn(str(manifest), json.dumps(report))
                self.assertEqual(manifest.read_bytes(), contents)

    def test_r8_nested_toml_claim_fanout_does_not_bypass_authority_gate(self):
        """64 top-level fields is NOT a limit on nested TOML descendants."""
        text = (
            'schema_version = "1.0.0"\n'
            '[private_claims_r8]\n'
            + "".join(
                f'private_authority_{index:03d} = "private_owner_r8"\n'
                for index in range(96)
            )
        )
        manifest = self.root / "nested-evidence.toml"
        manifest.write_text(text, encoding="utf-8")
        self.assertLess(manifest.stat().st_size, 32 * 1024)
        fields = tomllib.loads(text)
        self.assertEqual(len(fields), 2)
        self.assertEqual(len(fields["private_claims_r8"]), 96)
        report = review_manifest_file(manifest)
        self.assertEqual(report["status"], "review_only")
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["source_executed"])
        self.assertFalse(report["structure"]["owner_approval_verified"])
        self.assertFalse(
            report["structure"]["license_registry_or_compatibility_verified"]
        )
        self.assertIn(
            "unsupported_field",
            [row["field"] for row in report["structure"]["errors"]],
        )
        self.assertNotIn("private_owner_r8", json.dumps(report))
        self.assertNotIn("private_claims_r8", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
