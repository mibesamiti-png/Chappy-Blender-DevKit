"""R7 / EXT-001: data-only TOML review boundaries and privacy regressions.

No user addon, Python source, subprocess, or third-party extension is run.
All fixtures live inside isolated temporary directories.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cbdk.extension_manifest_review import (
    MAX_BYTES, review_manifest_file, write_manifest_review,
)


class ExtensionManifestRound7Tests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "private-marker-r7.toml"

    def write(self, data: str | bytes) -> Path:
        self.source.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return self.source

    def assert_sanitized(self, report):
        encoded = json.dumps(report, sort_keys=True, ensure_ascii=False)
        for private in (
            str(self.root), "private-marker-r7", "private_key_r7",
            "private_value_r7", "private_person_r7", "private_nested_r7",
        ):
            self.assertNotIn(private, encoded)
        self.assertEqual(report["status"], "review_only")
        self.assertFalse(report["source_executed"])
        self.assertFalse(report["source_modified"])
        self.assertFalse(report["official_validation_ran"])
        self.assertFalse(report["release_authorized"])
        return encoded

    def test_r7_byte_limit_minus_exact_plus_one_with_valid_toml(self):
        """Just-below and exact cap are valid TOML, over cap rejects before parse."""
        prefix = 'schema_version = "1.0.0"\n# private_value_r7 '
        for total in (MAX_BYTES - 1, MAX_BYTES, MAX_BYTES + 1):
            with self.subTest(total=total):
                data = (prefix + "x" * (total - len(prefix))).encode("ascii")
                self.assertEqual(len(data), total)
                path = self.write(data)
                if total > MAX_BYTES:
                    with self.assertRaisesRegex(ValueError, "byte limit") as raised:
                        review_manifest_file(path)
                    self.assertNotIn("private_value_r7", str(raised.exception))
                else:
                    report = review_manifest_file(path)
                    self.assert_sanitized(report)
                    self.assertEqual(report["structure"]["status"], "incomplete")
                    self.assertEqual(path.read_bytes(), data)

    def test_r7_top_level_field_limit_63_64_65(self):
        """The 64-field cap applies to parsed top-level TOML fields."""
        for field_count in (63, 64, 65):
            with self.subTest(fields=field_count):
                source = 'schema_version = "1.0.0"\n'
                source += "".join(
                    f'private_key_r7_{index:02d} = "private_value_r7"\n'
                    for index in range(field_count - 1)
                )
                self.write(source)
                if field_count > 64:
                    with self.assertRaisesRegex(ValueError, "field count"):
                        review_manifest_file(self.source)
                else:
                    report = review_manifest_file(self.source)
                    self.assert_sanitized(report)
                    self.assertEqual(
                        len(report["structure"]["errors"]), field_count - 1
                    )
                    self.assertTrue(all(
                        item["field"] == "unsupported_field"
                        for item in report["structure"]["errors"]
                    ))

    def test_r7_unknown_nested_tables_and_private_names_are_sanitized(self):
        """Unknown dotted/nested TOML keys must never appear in review JSON."""
        contents = (
            'schema_version = "1.0.0"\n'
            'maintainer = "private_person_r7@example.invalid"\n'
            '[private_nested_r7]\n'
            'private_key_r7 = "private_value_r7"\n'
        )
        before = self.write(contents).read_bytes()
        report = review_manifest_file(self.source)
        self.assert_sanitized(report)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertTrue(any(
            item["field"] == "unsupported_field"
            for item in report["structure"]["errors"]
        ))
        self.assertFalse(report["structure"]["owner_approval_verified"])

    def test_r7_duplicate_dotted_and_table_keys_fail_closed(self):
        """TOML parser failures cannot return partial success or echo values."""
        invalids = (
            'private_key_r7 = "private_value_r7"\nprivate_key_r7 = "again"\n',
            '[private_nested_r7]\nprivate_key_r7 = "private_value_r7"\n'
            '[private_nested_r7]\nprivate_key_r7 = "again"\n',
            'private_nested_r7.x = "private_value_r7"\n'
            'private_nested_r7.x = "again"\n',
            'private_nested_r7 = 1\n[private_nested_r7]\n'
            'private_key_r7 = "private_value_r7"\n',
        )
        for index, content in enumerate(invalids):
            with self.subTest(case=index):
                original = self.write(content).read_bytes()
                with self.assertRaises(ValueError) as raised:
                    review_manifest_file(self.source)
                self.assertNotIn("private_value_r7", str(raised.exception))
                self.assertNotIn(str(self.source), str(raised.exception))
                self.assertEqual(self.source.read_bytes(), original)

    def test_r7_malformed_utf8_and_toml_are_safe(self):
        """Malformed bytes or syntax cannot leak a source path or value."""
        cases = (
            b'private_key_r7 = "\xff"\n',
            b'private_key_r7 = "\xc3"\n',
            b'private_key_r7 = [1, 2,\n',
        )
        for raw in cases:
            with self.subTest(content=repr(raw[:18])):
                original = self.write(raw).read_bytes()
                with self.assertRaises(ValueError) as raised:
                    review_manifest_file(self.source)
                self.assertNotIn(str(self.source), str(raised.exception))
                self.assertNotIn("private_key_r7", str(raised.exception))
                self.assertEqual(self.source.read_bytes(), original)

    def test_r7_fresh_output_is_sanitized_and_never_overwritten(self):
        """Read-only input and create-only output survive valid review."""
        data = self.write(
            'schema_version = "1.0.0"\n'
            'maintainer = "private_person_r7@example.invalid"\n'
            '[private_nested_r7]\nprivate_key_r7 = "private_value_r7"\n'
        ).read_bytes()
        destination = "reports/latest/r7-manifest-review.json"
        report = write_manifest_review(self.source, destination, root=self.root)
        output = self.root / destination
        saved = output.read_bytes()
        self.assert_sanitized(report)
        self.assertEqual(json.loads(saved), report)
        self.assertEqual(self.source.read_bytes(), data)
        with self.assertRaises(ValueError):
            write_manifest_review(self.source, destination, root=self.root)
        self.assertEqual(output.read_bytes(), saved)

    def test_r7_destination_traversal_and_symlink_escape_do_not_write(self):
        self.write('schema_version = "1.0.0"\n')
        for dest in (
            "reports/latest/../escape.json",
            "reports/latest/../../escape.json",
            "../reports/latest/escape.json",
            "reports/latest/private-marker-r7.txt",
            str(self.root / "absolute-private-marker-r7.json"),
        ):
            with self.subTest(dest=dest):
                with self.assertRaises(ValueError):
                    write_manifest_review(self.source, dest, root=self.root)

        reports = self.root / "reports" / "latest"
        reports.mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        link = reports / "linked-private-marker-r7.json"
        try:
            link.symlink_to(outside / "outside-target.json")
        except (OSError, NotImplementedError):
            # Windows without symlink privilege: previous traversal tests
            # remain valid, and the CI Unix matrix exercises the symlink.
            return
        with self.assertRaises(ValueError):
            write_manifest_review(
                self.source, "reports/latest/linked-private-marker-r7.json",
                root=self.root,
            )
        self.assertFalse((outside / "outside-target.json").exists())
        self.assertTrue(link.is_symlink())

    def test_r7_source_symlink_and_unsafe_output_parent_are_rejected(self):
        self.write('schema_version = "1.0.0"\n')
        source_link = self.root / "source-link.toml"
        try:
            source_link.symlink_to(self.source)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(ValueError):
            review_manifest_file(source_link)
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "reports").mkdir()
        latest = self.root / "reports" / "latest"
        latest.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            write_manifest_review(
                self.source, "reports/latest/private-marker-r7.json",
                root=self.root,
            )
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
