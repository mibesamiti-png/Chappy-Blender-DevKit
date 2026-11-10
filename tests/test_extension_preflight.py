"""CBDK extension readiness preflight, no executable source or release build."""
# Round-two adversarial ZIP regressions: test_extension_archive_round2.py.
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from cbdk.__main__ import main
from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_preflight import diagnose_preview_archive, inspect_preview_archive, write_preflight_report


class ExtensionPreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.zip = self.root / "preview.zip"

    def build(self, recipe="modular_all"):
        return build_addon(
            ROOT / ("recipes/" + recipe + ".json"), self.zip,
            preview_unapproved=True,
        )

    def replace_zip_member(self, name, content):
        old = self.zip
        target = self.root / "tampered.zip"
        with ZipFile(old) as source, ZipFile(target, "x", compression=ZIP_DEFLATED) as out:
            for entry in source.infolist():
                out.writestr(entry, content if entry.filename == name else
                             source.read(entry.filename))
        return target

    def test_r4_all_authored_recipes_remain_safe_and_release_blocked(self):
        """R2 strict ZIP layout must preserve all seven authentic preview recipes.

        Two independently generated archives per recipe also catch accidental
        metadata/timestamp drift. No addon import or execution occurs here.
        """
        recipes = (
            "mesh_inspector",
            "modular_all", "modular_combined", "modular_edit",
            "modular_geometry", "modular_nudge", "modular_objects",
        )
        for recipe in recipes:
            with self.subTest(recipe=recipe):
                first = self.root / (recipe + "-one.zip")
                second = self.root / (recipe + "-two.zip")
                source = ROOT / "recipes" / (recipe + ".json")
                built = build_addon(source, first, preview_unapproved=True)
                rebuilt = build_addon(source, second, preview_unapproved=True)
                self.assertTrue(built["preview_only"])
                self.assertFalse(built["approved"])
                self.assertEqual(built["files"], rebuilt["files"])
                self.assertEqual(first.read_bytes(), second.read_bytes())

                for archive in (first, second):
                    report = inspect_preview_archive(archive)
                    self.assertEqual(report, diagnose_preview_archive(archive))
                    self.assertEqual(report["status"], "blocked_for_extension_release")
                    self.assertEqual(report["package_id"], built["package_id"])
                    self.assertEqual(report["verified_source_file_count"], built["files"] - 1)
                    self.assertTrue(report["archive_structure_checked"])
                    self.assertTrue(report["provenance_hashes_verified"])
                    self.assertTrue(report["preview_only"])
                    self.assertFalse(report["source_authenticity_verified"])
                    self.assertFalse(report["python_code_executed"])
                    self.assertFalse(report["extension_zip_created"])
                    self.assertFalse(report["manifest_toml_emitted"])
                    self.assertFalse(report["official_blender_extension_validate_ran"])
                    self.assertFalse(report.get("release_authorized", False))
                    self.assertEqual(report["manifest_structure_review"]["status"], "incomplete")
                    self.assertEqual(
                        report["manifest_structure_review"]["missing_required_fields"],
                        ["version", "maintainer", "license"])
                    self.assertFalse(report["manifest_structure_review"]["owner_approval_verified"])
                    self.assertFalse(report["manifest_structure_review"]["license_registry_or_compatibility_verified"])
                    self.assertIn("license", report["blocker_categories"]["owner_metadata"])
                    self.assertNotIn(str(self.root), json.dumps(report))
                    self.assertNotIn(str(archive), json.dumps(report))

                # One negative control per recipe: a trailer must never
                # downgrade a malformed ZIP to merely "release blocked".
                corrupt = self.root / (recipe + "-trailer.zip")
                corrupt.write_bytes(first.read_bytes() + b"synthetic-hidden-tail")
                result = diagnose_preview_archive(corrupt)
                self.assertEqual(result["status"], "invalid_preview_archive")
                self.assertEqual(result["failure_category"], "archive_structure")
                self.assertEqual(result["failure_code"], "zip_envelope")
                self.assertFalse(result["provenance_hashes_verified"])
                self.assertNotIn("synthetic-hidden-tail", json.dumps(result))
                self.assertNotIn(str(corrupt), json.dumps(result))

    def test_r8_valid_preview_and_synthetic_validator_remain_independent(self):
        """Two successful *technical* observations never imply release rights."""
        from cbdk.extension_manifest import compare_official_validation
        self.build("mesh_inspector")
        inspected = inspect_preview_archive(self.zip)
        self.assertEqual(inspected["status"], "blocked_for_extension_release")
        self.assertTrue(inspected["archive_structure_checked"])
        self.assertTrue(inspected["provenance_hashes_verified"])
        self.assertFalse(inspected["source_authenticity_verified"])
        self.assertFalse(inspected["official_blender_extension_validate_ran"])
        self.assertFalse(inspected.get("release_authorized", False))

        # A fabricated clean official-log string is not an authenticated
        # official CLI execution or evidence of author/license permission.
        fields = {
            "schema_version": "1.0.0", "id": "cbdk_synthetic_fixture",
            "version": "1.2.3", "name": "Synthetic fixture",
            "tagline": "Synthetic validation fixture",
            "maintainer": "Synthetic test", "type": "add-on",
            "blender_version_min": "4.4.0",
            "license": ["SPDX:GPL-3.0-or-later"],
        }
        compared = compare_official_validation(
            fields, 0, 'Success parsing TOML in "synthetic"\nBlender quit',
        )
        self.assertEqual(compared["status"], "agreement")
        self.assertTrue(compared["complete_diagnostic_agreement"])
        self.assertFalse(compared["official_observation"]["authenticates_log"])
        self.assertFalse(compared["owner_approval_verified"])
        self.assertFalse(compared["license_compatibility_verified"])
        self.assertIn(
            "owner_release_and_redistribution_authorization_required",
            inspected["blockers"],
        )
        self.assertFalse(inspected.get("release_authorized", False))

    def test_r9_rehashed_helper_is_still_release_blocked(self):
        """Changing self-asserted hashes cannot turn authored ZIP into release."""
        import hashlib
        self.build("mesh_inspector")
        with ZipFile(self.zip) as source:
            package = "cbdk_mesh_inspector_preview/"
            info_name = package + "CBDK_BUILD_INFO.json"
            metadata = json.loads(source.read(info_name))
            helper_name = "helpers/context.py"
            payload = source.read(package + helper_name) + b"\n# synthetic r9 only\n"
            digest = hashlib.sha256(payload).hexdigest()
            self.assertNotEqual(metadata["files_sha256"][helper_name], digest)
            metadata["files_sha256"][helper_name] = digest
            for part in metadata["parts"]:
                if part["source"] == "parts/blender/context.py":
                    part["sha256"] = digest
            modified = self.root / "self-rehashed-r9.zip"
            with ZipFile(modified, "x") as output:
                for info in source.infolist():
                    if info.filename == info_name:
                        content = (json.dumps(metadata, sort_keys=True) + "\n").encode()
                    elif info.filename == package + helper_name:
                        content = payload
                    else:
                        content = source.read(info.filename)
                    output.writestr(info, content)

        report = inspect_preview_archive(modified)
        self.assertTrue(report["provenance_hashes_verified"])
        self.assertEqual(report["status"], "blocked_for_extension_release")
        self.assertFalse(report["source_authenticity_verified"])
        self.assertFalse(report["python_code_executed"])
        self.assertFalse(report["official_blender_extension_validate_ran"])
        self.assertFalse(report.get("release_authorized", False))
        self.assertIn("owner_release_and_redistribution_authorization_required",
                      report["blockers"])
        self.assertEqual(report, diagnose_preview_archive(modified))
        self.assertNotIn(str(modified), json.dumps(report))

    def test_r10_checked_out_source_bytes_cannot_grant_release(self):
        """Fixed CBDK source bytes are independent of archive-declared SHA."""
        from cbdk.addon_builder import ROOT, _trusted_read
        self.build("mesh_inspector")
        with ZipFile(self.zip) as archive:
            packaged = archive.read("cbdk_mesh_inspector_preview/helpers/context.py")
        repository_bytes = _trusted_read("parts/blender/context.py", root=ROOT)
        self.assertEqual(packaged, repository_bytes)
        result = inspect_preview_archive(self.zip)
        self.assertEqual(result["status"], "blocked_for_extension_release")
        self.assertTrue(result["provenance_hashes_verified"])
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["official_blender_extension_validate_ran"])
        self.assertFalse(result.get("release_authorized", False))
        self.assertIn(
            "owner_release_and_redistribution_authorization_required",
            result["blockers"],
        )
        self.assertNotIn(str(ROOT), json.dumps(result))

    def test_r13_commit_inventory_binding_is_independent_of_zip(self):
        """R13 watched smoke: same commit, changed source inventory is unknown."""
        import test_extension_source_reference_round10 as r10
        import test_extension_source_reference_round12 as r12
        import test_extension_source_reference_round13 as r13
        self.build("mesh_inspector")
        result = inspect_preview_archive(self.zip)
        self.assertEqual(result["status"], "blocked_for_extension_release")
        package = result["package_id"]
        with ZipFile(self.zip) as z:
            included = {name.removeprefix(package + "/") for name in z.namelist()}
        reference = r10._current_reference_snapshot(package, included)
        pinned = r12.snapshot_basis(reference, r13.COMMIT)
        first = next(iter(reference))
        different = dict(reference, **{first: reference[first] + b"synthetic-r13"})
        unknown = r13._compare_frozen_basis(self.zip, different, pinned, pinned)
        self.assertEqual(unknown["status"], "inconclusive_reference_basis")
        self.assertFalse(unknown["source_authenticity_verified"])
        self.assertFalse(unknown["release_authorized"])
        known = r13._compare_frozen_basis(self.zip, reference, pinned, pinned)
        self.assertEqual(known["status"], "same_known_repo_bytes")
        self.assertFalse(known["source_authenticity_verified"])
        self.assertFalse(known["release_authorized"])

    def test_r14_handle_probes_do_not_elevate_release_authority(self):
        """R14 CI-watched smoke: stable reason-only status never approves source."""
        import test_extension_reference_race_round14 as r14
        self.assertEqual(len(r14.REASON_CODES), 6)
        for reason in r14.REASON_CODES:
            report = r14._review_only(reason)
            self.assertEqual(report["reason_code"], reason)
            self.assertFalse(report["source_authenticity_verified"])
            self.assertFalse(report["owner_consent_verified"])
            self.assertFalse(report["license_compatibility_verified"])
            self.assertFalse(report["redistribution_authorized"])
            self.assertFalse(report["release_authorized"])
            self.assertFalse(report["python_code_executed"])
            self.assertEqual(report["content_opens"], 0)
            self.assertEqual(report["bytes_read"], 0)
        self.build("mesh_inspector")
        observed = inspect_preview_archive(self.zip)
        self.assertEqual(observed["status"], "blocked_for_extension_release")
        self.assertFalse(observed["source_authenticity_verified"])
        self.assertFalse(observed.get("release_authorized", False))

    def test_r15_missing_independent_digest_never_implies_authority(self):
        """R15 watched CI: absent prior reference fails without a source read."""
        import test_extension_reference_digest_round15 as r15
        from unittest.mock import patch
        with patch.object(
            r15.r14, "_anchored_reference_probe",
            side_effect=AssertionError("missing digest must not read source"),
        ):
            report = r15._digest_review(
                None, None, "parts/blender/context.py",
                independent_digest=None,
            )
        self.assertEqual(report["reason_code"], "inconclusive_reference_basis")
        self.assertEqual(report["content_opens"], 0)
        self.assertEqual(report["bytes_read"], 0)
        self.assertFalse(report["source_authenticity_verified"])
        self.assertFalse(report["owner_consent_verified"])
        self.assertFalse(report["license_compatibility_verified"])
        self.assertFalse(report["redistribution_authorized"])
        self.assertFalse(report["release_authorized"])
        self.build("mesh_inspector")
        known = inspect_preview_archive(self.zip)
        self.assertEqual(known["status"], "blocked_for_extension_release")
        self.assertFalse(known["source_authenticity_verified"])
        self.assertFalse(known.get("release_authorized", False))

    def test_all_feature_preview_is_verified_but_not_extension_approved(self):
        self.build()
        result = inspect_preview_archive(self.zip)
        self.assertTrue(result["provenance_hashes_verified"])
        self.assertTrue(result["archive_structure_checked"])
        self.assertEqual(result["status"], "blocked_for_extension_release")
        self.assertFalse(result["python_code_executed"])
        self.assertFalse(result["extension_zip_created"])
        self.assertIsNone(result["manifest_fields_review_only"]["license"])
        self.assertIsNone(result["manifest_fields_review_only"]["maintainer"])
        self.assertFalse(result["official_blender_extension_validate_ran"])
        self.assertEqual(result["package_id"], "cbdk_modular_preview")

    def test_legacy_preview_also_gets_readiness_report(self):
        self.build("mesh_inspector")
        result = inspect_preview_archive(self.zip)
        self.assertEqual(result["package_id"], "cbdk_mesh_inspector_preview")
        self.assertEqual(result["manifest_fields_review_only"]["blender_version_min"], "4.4.0")
        self.assertIn("owner_release_and_redistribution_authorization_required", result["blockers"])

    def test_manifest_missing_inputs_and_approvals_are_separate(self):
        self.build()
        report = inspect_preview_archive(self.zip)
        self.assertEqual(report["manifest_structure_review"]["status"], "incomplete")
        self.assertEqual(report["manifest_structure_review"]["missing_required_fields"], ["version", "maintainer", "license"])
        self.assertFalse(report["source_authenticity_verified"])
        self.assertIn("component_approval", report["blocker_categories"]["approval"])

    def test_metadata_cannot_invent_or_duplicate_dependencies(self):
        self.build()
        name = "cbdk_modular_preview/CBDK_BUILD_INFO.json"
        with ZipFile(self.zip) as z:
            original = json.loads(z.read(name))
        for ids in (["UNKNOWN-001"], [p["part_id"] for p in original["parts"]] + [original["parts"][0]["part_id"]]):
            changed = dict(original)
            changed["parts"] = [{"part_id": pid, "catalog_approved": False, "license_review": "pending"} for pid in ids]
            target = self.replace_zip_member(name, json.dumps(changed).encode())
            with self.assertRaises(ValueError):
                inspect_preview_archive(target)
            target.unlink()

    def test_tampered_source_byte_detected_without_executing(self):
        self.build()
        with ZipFile(self.zip) as z:
            name = "cbdk_modular_preview/features/object_selection.py"
            payload = z.read(name) + b'\nraise RuntimeError("never execute")\n'
        changed = self.replace_zip_member(name, payload)
        with self.assertRaisesRegex(ValueError, "changed since build"):
            inspect_preview_archive(changed)

    def test_missing_or_changed_provenance_fails_closed(self):
        self.build()
        with ZipFile(self.zip) as z:
            name = "cbdk_modular_preview/CBDK_BUILD_INFO.json"
            data = json.loads(z.read(name))
        for field, val in [("approved", True), ("redistribution_cleared", True),
                           ("preview_only", False), ("schema_version", True)]:
            with self.subTest(field=field):
                changed = dict(data, **{field: val})
                target = self.replace_zip_member(name, json.dumps(changed).encode())
                with self.assertRaises(ValueError):
                    inspect_preview_archive(target)
                target.unlink()

    def test_duplicate_metadata_key_rejected(self):
        self.build()
        name = "cbdk_modular_preview/CBDK_BUILD_INFO.json"
        with ZipFile(self.zip) as z:
            data = z.read(name).decode("utf-8")
        bad = data[:-2] + ', "approved": true}'
        changed = self.replace_zip_member(name, bad.encode("utf-8"))
        with self.assertRaises(ValueError):
            inspect_preview_archive(changed)

    def test_archive_path_traversal_and_duplicate_entries_rejected(self):
        self.build()
        for name in ("../exfiltrate.py", "cbdk_modular_preview/../unsafe.py",
                     "cbdk_modular_preview/README.txt"):
            with self.subTest(name=name):
                target = self.root / "extra.zip"
                with ZipFile(self.zip) as original, ZipFile(target, "x") as out:
                    for info in original.infolist():
                        out.writestr(info, original.read(info.filename))
                    out.writestr(name, "unsafe")
                with self.assertRaises(ValueError):
                    inspect_preview_archive(target)
                target.unlink()

    def test_symlink_member_rejected(self):
        self.build()
        source = self.zip
        target = self.root / "symlink.zip"
        name = "cbdk_modular_preview/extra.py"
        with ZipFile(source) as original, ZipFile(target, "x") as out:
            for info in original.infolist():
                out.writestr(info, original.read(info.filename))
            info = ZipInfo(name)
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            out.writestr(info, "elsewhere")
        with self.assertRaises(ValueError):
            inspect_preview_archive(target)

    def test_fails_if_file_missing(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            inspect_preview_archive(self.root / "missing.zip")

    def test_readiness_report_is_non_overwriting_and_static(self):
        self.build()
        report = self.root / "readiness.json"
        first = write_preflight_report(self.zip, report)
        self.assertEqual(first, json.loads(report.read_text()))
        with self.assertRaises(FileExistsError):
            write_preflight_report(self.zip, report)
        self.assertEqual(first, json.loads(report.read_text()))
        self.assertEqual(list(self.root.glob("*.zip")), [self.zip])

    def test_cli_creates_only_local_json_report(self):
        self.build()
        report = self.root / "readiness.json"
        self.assertEqual(main(["extension-preflight", str(self.zip),
                               "--output", str(report)]), 0)
        result = json.loads(report.read_text())
        self.assertEqual(result["kind"], "cbdk_extension_readiness_preflight")
        self.assertEqual(result["status"], "blocked_for_extension_release")


    def test_clean_zip_envelope_rejects_prefix_trailer_and_comment(self):
        self.build()
        original = self.zip.read_bytes()
        for label, payload in (("prefix", b"#!/bin/sh\n" + original),
                               ("trailer", original + b"hidden payload")):
            with self.subTest(label=label):
                path = self.root / (label + ".zip")
                path.write_bytes(payload)
                report = diagnose_preview_archive(path)
                self.assertEqual(report["status"], "invalid_preview_archive")
                self.assertEqual(report["failure_category"], "archive_structure")
                self.assertEqual(report["failure_code"], "zip_envelope")
                self.assertFalse(report["provenance_hashes_verified"])
        path = self.root / "comment.zip"
        with ZipFile(self.zip) as source, ZipFile(path, "x") as target:
            for info in source.infolist():
                target.writestr(info, source.read(info.filename))
            target.comment = b"not expected in CBDK builder"
        self.assertEqual(diagnose_preview_archive(path)["failure_code"], "zip_envelope")

    def test_archive_member_special_modes_and_compression_are_rejected(self):
        self.build()
        for kind in ("device", "bzip2"):
            with self.subTest(kind=kind):
                path = self.root / (kind + ".zip")
                with ZipFile(self.zip) as source, ZipFile(path, "x") as target:
                    for old in source.infolist():
                        info = ZipInfo(old.filename)
                        info.compress_type = old.compress_type
                        info.external_attr = old.external_attr
                        if old.filename.endswith("/README.txt"):
                            if kind == "device":
                                info.external_attr = 0o020644 << 16
                            else:
                                from zipfile import ZIP_BZIP2
                                info.compress_type = ZIP_BZIP2
                        target.writestr(info, source.read(old.filename))
                result = diagnose_preview_archive(path)
                self.assertEqual(result["failure_code"], "unsafe_member")
                self.assertFalse(result["python_code_executed"])

    def test_corrupt_member_crc_is_integrity_failure(self):
        from zipfile import ZIP_STORED
        self.build()
        target = self.root / "corrupted.zip"
        member = "cbdk_modular_preview/README.txt"
        with ZipFile(self.zip) as original, ZipFile(target, "x") as output:
            for old in original.infolist():
                info = ZipInfo(old.filename)
                info.compress_type = ZIP_STORED
                info.external_attr = old.external_attr
                output.writestr(info, original.read(old.filename))
        with ZipFile(target) as archive:
            info = archive.getinfo(member)
            position = info.header_offset + 30 + len(info.filename.encode("utf-8")) + len(info.extra)
        with target.open("r+b") as stream:
            stream.seek(position)
            first = stream.read(1)
            stream.seek(position)
            stream.write(bytes([first[0] ^ 1]))
        report = diagnose_preview_archive(target)
        self.assertEqual(report["status"], "invalid_preview_archive")
        self.assertEqual(report["failure_category"], "archive_integrity")
        self.assertEqual(report["failure_code"], "corrupt_or_unreadable")

    def test_duplicate_metadata_key_has_specific_provenance_code(self):
        self.build()
        name = "cbdk_modular_preview/CBDK_BUILD_INFO.json"
        with ZipFile(self.zip) as archive:
            raw = archive.read(name).decode("utf-8")
        changed = self.replace_zip_member(name, (raw[:-2] + ', "approved": true}').encode("utf-8"))
        result = diagnose_preview_archive(changed)
        self.assertEqual(result["failure_category"], "provenance")
        self.assertEqual(result["failure_code"], "duplicate_metadata_key")

    def test_tampered_manifest_name_not_reflected_in_report(self):
        self.build()
        name = "cbdk_modular_preview/CBDK_BUILD_INFO.json"
        with ZipFile(self.zip) as archive:
            metadata = json.loads(archive.read(name))
        metadata["display_name"] = "Private Person email@example.invalid"
        changed = self.replace_zip_member(name, json.dumps(metadata).encode())
        report = inspect_preview_archive(changed)
        self.assertNotIn("Private Person", json.dumps(report))
        self.assertNotIn("email@example", json.dumps(report))
        self.assertEqual(report["status"], "blocked_for_extension_release")

    def test_invalid_minimum_blender_metadata_is_provenance_error(self):
        self.build()
        name = "cbdk_modular_preview/CBDK_BUILD_INFO.json"
        with ZipFile(self.zip) as archive:
            metadata = json.loads(archive.read(name))
        metadata["minimum_blender"] = "danger/private/5.0"
        changed = self.replace_zip_member(name, json.dumps(metadata).encode())
        result = diagnose_preview_archive(changed)
        self.assertEqual(result["failure_code"], "invalid_minimum_blender")
        self.assertNotIn("danger/private", json.dumps(result))
        with self.assertRaises(ValueError):
            inspect_preview_archive(changed)

    def test_invalid_archive_distinct_from_legal_approval_blockers(self):
        self.build()
        legitimate = diagnose_preview_archive(self.zip)
        self.assertEqual(legitimate["status"], "blocked_for_extension_release")
        self.assertIn("license", legitimate["blocker_categories"]["owner_metadata"])
        bad = self.root / "missing.zip"
        result = diagnose_preview_archive(bad)
        self.assertEqual(result["status"], "invalid_preview_archive")
        self.assertEqual(result["failure_category"], "archive_structure")
        self.assertEqual(result["failure_code"], "missing_or_unsafe_input")
        self.assertNotIn(str(bad), json.dumps(result))


if __name__ == "__main__":
    unittest.main()
