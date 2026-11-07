"""EXT-001 R6: bounded synthetic ZIP/validator-input failure regressions.

No untrusted addon source or ZIP payload is ever executed. ZIP member sizes
are changed *only in central-directory metadata*, so budget tests do not
allocate multi-megabyte uncompressed entries or perform decompression.
"""
from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_manifest import compare_official_validation, observe_official_validation
from cbdk.extension_preflight import (
    MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS,
    diagnose_preview_archive, inspect_preview_archive,
)

PACKAGE = "cbdk_modular_preview"


class ExtensionLimitsRound6Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def assert_rejected(self, path, category=None, code=None):
        result = diagnose_preview_archive(path)
        self.assertEqual(result["status"], "invalid_preview_archive")
        if category is not None:
            self.assertEqual(result["failure_category"], category)
        if code is not None:
            self.assertEqual(result["failure_code"], code)
        self.assertFalse(result["provenance_hashes_verified"])
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["python_code_executed"])
        self.assertFalse(result["extension_zip_created"])
        self.assertFalse(result["official_blender_extension_validate_ran"])
        sanitized = json.dumps(result)
        self.assertNotIn(str(self.root), sanitized)
        self.assertNotIn("private-marker-r6", sanitized)
        with self.assertRaises(ValueError):
            inspect_preview_archive(path)
        return result

    def make_small_zip(self, label, entries):
        """One known package prefix, canonical tiny archives, no code execution."""
        target = self.root / (label + ".zip")
        with ZipFile(target, "x", compression=ZIP_STORED) as archive:
            for index in range(entries):
                archive.writestr(f"{PACKAGE}/fixture_{index:03d}.txt", b"")
        return target

    def pretend_sizes(self, path, expanded_size):
        """Alter ZIP central-directory sizes, not the local payloads."""
        data = bytearray(path.read_bytes())
        position = 0
        count = 0
        while True:
            central = data.find(b"PK\x01\x02", position)
            if central < 0:
                break
            self.assertLess(central + 46, len(data))
            struct.pack_into("<I", data, central + 24, expanded_size)
            position = central + 46
            count += 1
        self.assertGreater(count, 0)
        path.write_bytes(data)
        return count

    def test_r6_archive_byte_limit_exact_boundary_without_large_payload(self):
        """Sparse-like files test stat budget ordering, not ZIP decompression."""
        for size, expected in (
            (MAX_ARCHIVE_BYTES - 1, "zip_envelope"),
            (MAX_ARCHIVE_BYTES, "zip_envelope"),
            (MAX_ARCHIVE_BYTES + 1, "archive_too_large"),
        ):
            with self.subTest(size=size):
                path = self.root / f"limit-{size}.zip"
                with path.open("wb") as stream:
                    stream.write(b"PK\x03\x04")
                    stream.truncate(size)
                self.assertEqual(path.stat().st_size, size)
                self.assert_rejected(path, "archive_structure", expected)

    def test_r6_member_count_exact_boundary(self):
        for count in (MAX_MEMBERS - 1, MAX_MEMBERS, MAX_MEMBERS + 1):
            with self.subTest(count=count):
                path = self.make_small_zip(f"count-{count}", count)
                expected = (
                    ("archive_structure", "duplicate_or_count") if count > MAX_MEMBERS
                    else ("provenance", "missing_metadata")
                )
                self.assert_rejected(path, *expected)

    def test_r6_per_entry_size_boundary_from_tiny_central_records(self):
        for expanded, failure in (
            (MAX_ENTRY_BYTES - 1, "zip_layout_mismatch"),
            (MAX_ENTRY_BYTES, "zip_layout_mismatch"),
            (MAX_ENTRY_BYTES + 1, "unsafe_member"),
        ):
            with self.subTest(expanded=expanded):
                path = self.make_small_zip(f"entry-{expanded}", 3)
                self.assertEqual(self.pretend_sizes(path, expanded), 3)
                self.assertLess(path.stat().st_size, 1024)
                self.assert_rejected(path, "archive_structure", failure)

    def test_r6_uncompressed_total_budget_boundary_without_decompression(self):
        """Eight virtual 2-MiB entries are at budget; nine are over budget."""
        for entries, failure in (
            (MAX_ARCHIVE_BYTES // MAX_ENTRY_BYTES, "zip_layout_mismatch"),
            (MAX_ARCHIVE_BYTES // MAX_ENTRY_BYTES + 1, "uncompressed_budget"),
        ):
            with self.subTest(entries=entries):
                path = self.make_small_zip(f"aggregate-{entries}", entries)
                self.assertEqual(self.pretend_sizes(path, MAX_ENTRY_BYTES), entries)
                self.assertLess(path.stat().st_size, 2048)
                self.assert_rejected(path, "archive_structure", failure)

    def test_r6_corrupt_local_and_central_records_fail_closed(self):
        authored = self.root / "authored.zip"
        build_addon(ROOT / "recipes/modular_all.json", authored, preview_unapproved=True)
        self.assertEqual(inspect_preview_archive(authored)["status"], "blocked_for_extension_release")
        baseline = authored.read_bytes()
        with ZipFile(authored) as archive:
            first_local = archive.infolist()[0].header_offset
        for label, position, replacement in (
            ("local-version", first_local + 4, b"\x63\x00"),
            ("central-marker", baseline.find(b"PK\x01\x02"), b"XXXX"),
            ("directory-length", len(baseline) - 22 + 12, b"\x00\x00\x00\x00"),
        ):
            with self.subTest(case=label):
                self.assertGreaterEqual(position, 0)
                altered = bytearray(baseline)
                altered[position:position + len(replacement)] = replacement
                target = self.root / (label + "-private-marker-r6.zip")
                target.write_bytes(altered)
                result = self.assert_rejected(target)
                self.assertIn(result["failure_category"],
                              ("archive_structure", "archive_integrity"))

    def test_r6_validator_output_character_limit(self):
        success = 'Success parsing TOML in "/private/private-marker-r6/manifest.toml"'
        fields = {
            "schema_version": "1.0.0", "id": "cbdk_test", "version": "1.2.3",
            "name": "Synthetic test", "tagline": "Synthetic validation fixture",
            "maintainer": "Synthetic test", "type": "add-on",
            "blender_version_min": "4.4.0", "license": ["SPDX:GPL-3.0-or-later"],
        }
        limit = 200_000
        for length in (limit - 1, limit):
            with self.subTest(length=length):
                output = success + "\n" + " " * (length - len(success) - 1)
                self.assertEqual(len(output), length)
                accepted = compare_official_validation(fields, 0, output)
                self.assertEqual(accepted["status"], "agreement")
                self.assertTrue(accepted["complete_diagnostic_agreement"])
                self.assertNotIn("private-marker-r6", str(accepted))
                self.assertFalse(accepted["official_observation"]["authenticates_log"])

        with self.assertRaisesRegex(ValueError, "oversized"):
            observe_official_validation(0, success + " " * (limit + 1 - len(success)))

        unknown = "WARNING: private-marker-r6"
        log = success + "\n" + " " * (limit - len(success) - len(unknown) - 2) + "\n" + unknown
        self.assertEqual(len(log), limit)
        report = compare_official_validation(fields, 0, log)
        self.assertEqual(report["status"], "unclassified")
        self.assertFalse(report["complete_diagnostic_agreement"])
        self.assertTrue(report["official_observation"]["has_unrecognized_diagnostics"])
        self.assertNotIn("private-marker-r6", str(report))


if __name__ == "__main__":
    unittest.main()
