"""CBDK extension readiness preflight, no executable source or release build."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from cbdk.__main__ import main
from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_preflight import inspect_preview_archive, write_preflight_report


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


if __name__ == "__main__":
    unittest.main()
