"""Round-2 adversarial ZIP tests: synthetic CBDK previews only, never execute addons.

The red-phase tests deliberately exercise archives that stdlib zipfile can
interpret despite not being a canonical CBDK-authored preview ZIP.
"""
from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from cbdk.addon_builder import ROOT, build_addon
from cbdk.extension_preflight import diagnose_preview_archive, inspect_preview_archive


class ExtensionArchiveRound2Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.preview = self.root / "preview.zip"

    def build(self, recipe="modular_all"):
        build_addon(ROOT / f"recipes/{recipe}.json", self.preview, preview_unapproved=True)
        self.assertEqual(inspect_preview_archive(self.preview)["status"],
                         "blocked_for_extension_release")

    def assert_bad(self, path, category, code):
        result = diagnose_preview_archive(path)
        self.assertEqual(result["status"], "invalid_preview_archive")
        self.assertEqual((result["failure_category"], result["failure_code"]),
                         (category, code))
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["provenance_hashes_verified"])
        self.assertFalse(result["extension_zip_created"])
        self.assertFalse(result["official_blender_extension_validate_ran"])
        with self.assertRaises(ValueError):
            inspect_preview_archive(path)
        self.assertNotIn(str(path), json.dumps(result))
        self.assertNotIn("secret-marker", json.dumps(result))

    def test_zip_concatenation_with_two_valid_eocd_records(self):
        self.build()
        first = self.root / "first.zip"
        with ZipFile(first, "x", compression=ZIP_DEFLATED) as archive:
            archive.writestr("secret-marker.txt", "untrusted leading ZIP")
        target = self.root / "concat.zip"
        target.write_bytes(first.read_bytes() + self.preview.read_bytes())
        # Python's reader intentionally tolerates an appended ZIP: prove
        # the second archive is still discoverable before rejecting it.
        with ZipFile(target) as archive:
            self.assertIn("cbdk_modular_preview/CBDK_BUILD_INFO.json", archive.namelist())
        self.assert_bad(target, "archive_structure", "zip_layout_mismatch")

    def test_local_header_compression_disagrees_with_central_directory(self):
        self.build()
        target = self.root / "local-method.zip"
        data = bytearray(self.preview.read_bytes())
        with ZipFile(self.preview) as archive:
            info = archive.getinfo("cbdk_modular_preview/README.txt")
            self.assertEqual(info.compress_type, ZIP_DEFLATED)
            local_offset = info.header_offset
        self.assertEqual(data[local_offset:local_offset + 4], b"PK\x03\x04")
        struct.pack_into("<H", data, local_offset + 8, 0)  # local STORED; central DEFLATED
        target.write_bytes(data)
        with ZipFile(target) as archive:
            # The central directory still selects DEFLATED in zipfile.
            self.assertEqual(archive.read("cbdk_modular_preview/README.txt"),
                             ZipFile(self.preview).read("cbdk_modular_preview/README.txt"))
        self.assert_bad(target, "archive_structure", "zip_layout_mismatch")

    def test_member_extra_and_comment_cannot_hide_unhashed_data(self):
        self.build()
        member = "cbdk_modular_preview/README.txt"
        for kind in ("extra", "comment"):
            with self.subTest(kind=kind):
                target = self.root / (kind + ".zip")
                with ZipFile(self.preview) as original, ZipFile(target, "x") as output:
                    for old in original.infolist():
                        info = ZipInfo(old.filename)
                        info.compress_type = old.compress_type
                        info.external_attr = old.external_attr
                        if old.filename == member:
                            if kind == "extra":
                                info.extra = b"\xfe\xca\x04\x00ABCD"
                            else:
                                info.comment = b"secret-marker"
                        output.writestr(info, original.read(old.filename))
                with ZipFile(target) as archive:
                    self.assertEqual(archive.read(member), ZipFile(self.preview).read(member))
                self.assert_bad(target, "archive_structure", "unexpected_member_metadata")

    def test_part_source_and_source_hash_have_to_match_file_inventory(self):
        for recipe, package, digest_field in (
            ("modular_all", "cbdk_modular_preview", "source_sha256"),
            ("mesh_inspector", "cbdk_mesh_inspector_preview", "sha256"),
        ):
            with self.subTest(recipe=recipe):
                if self.preview.exists():
                    self.preview.unlink()
                self.build(recipe)
                meta_name = f"{package}/CBDK_BUILD_INFO.json"
                with ZipFile(self.preview) as original:
                    metadata = json.loads(original.read(meta_name))
                for field, bad_value in (("source", "secret-marker/outside.py"),
                                         (digest_field, "f" * 64)):
                    with self.subTest(recipe=recipe, field=field):
                        target = self.root / f"{recipe}-{field}.zip"
                        changed = json.loads(json.dumps(metadata))
                        changed["parts"][0][field] = bad_value
                        with ZipFile(self.preview) as source, ZipFile(target, "x") as out:
                            for info in source.infolist():
                                payload = (json.dumps(changed).encode("utf-8")
                                           if info.filename == meta_name else source.read(info.filename))
                                out.writestr(info, payload)
                        # Payload hashes still agree; only part provenance is forged.
                        with ZipFile(target) as archive:
                            self.assertEqual(archive.read(meta_name), json.dumps(changed).encode("utf-8"))
                        self.assert_bad(target, "provenance", "part_provenance_mismatch")


if __name__ == "__main__":
    unittest.main()
