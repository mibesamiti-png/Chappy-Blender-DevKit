"""R18: synthetic-only manifest and package generation regression."""
import io
from pathlib import Path
import stat
import tempfile
import tomllib
import unittest
from zipfile import ZipFile, ZipInfo

from cbdk.extension_manifest import review_manifest_fields
from cbdk.extension_preflight import MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS
from cbdk.extension_synthetic_build import (
    FIXTURE_ID, FIXTURE_INIT, MEMBER_NAMES, render_synthetic_manifest,
    synthetic_extension_members, build_synthetic_extension_bytes,
    verify_synthetic_extension_bytes, write_synthetic_extension_zip,
)


def fixture_fields():
    return {
        "schema_version": "1.0.0", "id": FIXTURE_ID, "version": "0.0.1",
        "name": 'Synthetic "quoted" \\ fixture 日本語',
        "tagline": "Synthetic fixture only",
        "maintainer": 'Synthetic "test" \\ maintainer',
        "type": "add-on", "blender_version_min": "4.4.0",
        "license": ["SPDX:GPL-3.0-or-later"],
        "blender_version_max": "5.3.0",
        "permissions": {"network": "Synthetic reason", "files": "Synthetic test only"},
    }


class SyntheticExtensionBuildTests(unittest.TestCase):
    def test_r18_toml_escape_roundtrip_and_optional_omission(self):
        fields = fixture_fields()
        for optional in (True, False):
            with self.subTest(optional=optional):
                if not optional:
                    fields.pop("permissions")
                    fields.pop("blender_version_max")
                data = render_synthetic_manifest(fields)
                parsed = tomllib.loads(data.decode("utf-8"))
                self.assertEqual(parsed, fields)
                self.assertEqual(review_manifest_fields(parsed)["status"],
                                 "structurally_valid_subset")
        fields["permissions"] = {}
        self.assertEqual(tomllib.loads(render_synthetic_manifest(fields).decode())["permissions"], {})

    def test_r18_zip_is_deterministic_and_exact(self):
        fields = fixture_fields()
        data = build_synthetic_extension_bytes(fields)
        reordered = dict(reversed(list(fields.items())))
        reordered["permissions"] = dict(reversed(list(fields["permissions"].items())))
        self.assertEqual(data, build_synthetic_extension_bytes(reordered))
        with ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(tuple(archive.namelist()), MEMBER_NAMES)
            self.assertEqual(archive.read("__init__.py"), FIXTURE_INIT)
            self.assertEqual(tomllib.loads(archive.read("blender_manifest.toml").decode()), fields)
            self.assertIsNone(archive.testzip())
        report = verify_synthetic_extension_bytes(data, fields)
        self.assertEqual(report["member_count"], 2)
        for key in ("official_validation_ran", "source_executed", "owner_approval_verified",
                    "real_component_license_chosen", "release_authorized", "install_authorized"):
            self.assertIs(report[key], False)
        self.assertNotIn(fields["maintainer"], str(report))
        self.assertEqual((MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS),
                         (16 * 1024 * 1024, 2 * 1024 * 1024, 64))

    def test_r18_invalid_metadata_no_output_and_no_values_in_diagnostics(self):
        for changes in ({"license": None}, {"maintainer": None},
                        {"id": "private_real_addon"}, {"type": "theme"},
                        {"private_optional_field": "secret-private-value"},
                        {"permissions": {"unknown_private_permission": "secret-private-value"}},
                        {"blender_version_max": "4.4.0"},
                        {"name": "secret-private-value\ninvalid"},
                        {"version": "bad-version"}):
            with self.subTest(changes=tuple(changes)), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "private_destination.zip"
                with self.assertRaises(ValueError) as exc:
                    write_synthetic_extension_zip({**fixture_fields(), **changes}, target)
                self.assertFalse(target.exists())
                for secret in ("secret-private-value", "private_optional_field",
                               "unknown_private_permission", "private_real_addon", str(target)):
                    self.assertNotIn(secret, str(exc.exception))

    def test_r18_fresh_output_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "fixture.zip"
            report = write_synthetic_extension_zip(fixture_fields(), target)
            original = target.read_bytes()
            self.assertEqual(original, build_synthetic_extension_bytes(fixture_fields()))
            self.assertFalse(report["release_authorized"])
            with self.assertRaises(ValueError):
                write_synthetic_extension_zip(fixture_fields(), target)
            self.assertEqual(target.read_bytes(), original)
            for bad in (root / "missing" / "x.zip", root / "x.txt"):
                with self.assertRaises(ValueError):
                    write_synthetic_extension_zip(fixture_fields(), bad)
                self.assertFalse(bad.exists())

    def test_r18_archive_inventory_rejects_altered_duplicate_and_unsafe_members(self):
        fields = fixture_fields()
        members = list(synthetic_extension_members(fields).items())
        cases = [
            members + [("../private_source.py", b"bad")],
            members + [members[0]],
            members[:-1],
            [("__init__.py", b"bad"), members[1]],
            [(members[0][0], members[0][1]), ("other.toml", members[1][1])],
        ]
        import warnings
        for entries in cases:
            with self.subTest(count=len(entries)):
                stream = io.BytesIO()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with ZipFile(stream, "w") as archive:
                        for name, payload in entries:
                            archive.writestr(name, payload)
                with self.assertRaises(ValueError):
                    verify_synthetic_extension_bytes(stream.getvalue(), fields)
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            info = ZipInfo("__init__.py")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, members[0][1])
            archive.writestr(*members[1])
        with self.assertRaises(ValueError):
            verify_synthetic_extension_bytes(stream.getvalue(), fields)
        with self.assertRaises(ValueError):
            verify_synthetic_extension_bytes(b"bad archive", fields)


if __name__ == "__main__":
    unittest.main()
