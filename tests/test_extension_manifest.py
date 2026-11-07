"""Manifest structure is not license/owner clearance or official validation."""
import unittest
from cbdk.extension_manifest import review_manifest_fields


def fields():
    return {"schema_version": "1.0.0", "id": "cbdk_test", "version": "1.2.3",
            "name": "Synthetic test", "tagline": "Synthetic validation fixture",
            "maintainer": "Synthetic test", "type": "add-on",
            "blender_version_min": "4.4.0", "license": ["SPDX:GPL-3.0-or-later"]}


class ManifestReviewTests(unittest.TestCase):
    def test_valid_subset_does_not_approve_license(self):
        report = review_manifest_fields(fields())
        self.assertEqual(report["status"], "structurally_valid_subset")
        self.assertFalse(report["owner_approval_verified"])
        self.assertFalse(report["license_registry_or_compatibility_verified"])

    def test_missing_owner_inputs_are_not_invalid_syntax(self):
        report = review_manifest_fields({**fields(), "version": None, "license": None})
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["missing_required_fields"], ["version", "license"])

    def test_invalid_fields_report_exact_cause(self):
        for key, value in (("version", "01.0.0"), ("version", "1.0.0-alpha.01"),
                           ("version", "1.0.0+.."), ("tagline", "Invalid!"),
                           ("tagline", "x" * 65), ("id", "bad__name"), ("id", "_bad"),
                           ("maintainer", True), ("license", []), ("license", ["GPL-3.0"]),
                           ("license", [True]), ("blender_version_min", "4.1.0")):
            with self.subTest(key=key, value=value):
                report = review_manifest_fields({**fields(), key: value})
                self.assertEqual(report["status"], "invalid")
                self.assertEqual(report["errors"][0]["field"], key)

    def test_unknown_fields_are_outside_bounded_subset(self):
        report = review_manifest_fields({**fields(), "permissions": {"network": "Fetch data"}})
        self.assertEqual(report["errors"][0]["code"], "unsupported_field_requires_official_validation")

    def test_semver_prerelease_and_build_identifiers(self):
        for value in ("1.0.0+build-id", "1.0.0-alpha.1+build-id", "0.1.0"):
            self.assertEqual(review_manifest_fields({**fields(), "version": value})["status"], "structurally_valid_subset")
