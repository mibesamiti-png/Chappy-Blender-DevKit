"""Manifest structure is not license/owner clearance or official validation."""
import unittest
from cbdk.extension_manifest import review_manifest_fields, compare_official_validation, manifest_field_diagnostics


def fields():
    return {"schema_version": "1.0.0", "id": "cbdk_test", "version": "1.2.3",
            "name": "Synthetic test", "tagline": "Synthetic validation fixture",
            "maintainer": "Synthetic test", "type": "add-on",
            "blender_version_min": "4.4.0", "license": ["SPDX:GPL-3.0-or-later"]}


class ManifestReviewTests(unittest.TestCase):
    def test_r4_official_synthetic_matrix_preserves_known_good_classification(self):
        """R3's fail-closed parser must not reject known Blender CLI output.

        The six data-only cases match the existing A-owned official validator
        script. These strings are synthetic, not a substitute for Blender CI.
        """
        variants = (
            ("valid_subset", {}, None, 0),
            ("missing_license", {"license": None}, 'missing "license"', 1),
            ("punctuated_tagline", {"tagline": "Invalid tagline!"},
             'key "tagline" invalid: synthetic validation detail', 1),
            ("invalid_id", {"id": "invalid-id"},
             'key "id" invalid: synthetic validation detail', 1),
            ("invalid_version", {"version": "not-version"},
             'key "version" invalid: synthetic validation detail', 1),
            ("empty_maintainer", {"maintainer": ""},
             'key "maintainer" invalid: synthetic validation detail', 1),
        )
        known_banners = (
            "Blender 4.4.3 (hash 802179c51ccc built 2025-04-29 15:12:13)",
            "Blender 4.5.15 LTS (hash 5afeabba6097 built 2026-10-22 01:33:47)",
            "Blender 5.2.1 LTS (hash 9e2066aef7ef built 2026-08-25 02:12:34)",
        )
        for banner in known_banners:
            for label, changes, diagnostic, exitcode in variants:
                with self.subTest(version=banner.split()[1], case=label):
                    example = {**fields(), **changes}
                    core = ('Success parsing TOML in "synthetic fixture"'
                            if diagnostic is None else
                            'Error parsing TOML "synthetic fixture"\n' + diagnostic)
                    output = banner + "\n" + core + "\nBlender quit\n"
                    compared = compare_official_validation(example, exitcode, output)
                    self.assertEqual(compared["status"], "agreement")
                    self.assertTrue(compared["complete_diagnostic_agreement"])
                    self.assertEqual(compared["official_observation"]["status"],
                                     "accepted" if exitcode == 0 else "rejected")
                    self.assertFalse(compared["official_observation"]["has_unrecognized_diagnostics"])
                    self.assertFalse(compared["official_observation"]["authenticates_log"])
                    self.assertFalse(compared["owner_approval_verified"])
                    self.assertFalse(compared["license_compatibility_verified"])
                    self.assertNotIn("synthetic fixture", str(compared))

                    # The exact same valid/invalid observation becomes
                    # unclassified when an unknown value-bearing line appears.
                    injected = output + "Unknown validator note: private-marker-42\n"
                    blocked = compare_official_validation(example, exitcode, injected)
                    self.assertEqual(blocked["status"], "unclassified")
                    self.assertFalse(blocked["complete_diagnostic_agreement"])
                    self.assertTrue(blocked["official_observation"]["has_unrecognized_diagnostics"])
                    self.assertNotIn("private-marker-42", str(blocked))
                    self.assertNotIn("synthetic fixture", str(blocked))

    def test_r5_official_versioned_logs_are_stable_with_line_ending_variants(self):
        """Known 3-version x 6-case observations must survive CRLF and blank lines.

        Exact banner shapes were observed in prior official Blender CI runs.
        Logs below are synthetic; the actual CLI is exercised separately in CI.
        """
        cases = (
            ("valid_subset", {}, 0, None),
            ("missing_license", {"license": None}, 1, 'missing "license"'),
            ("punctuated_tagline", {"tagline": "Invalid tagline!"}, 1,
             'key "tagline" invalid: synthetic detail'),
            ("invalid_id", {"id": "invalid-id"}, 1,
             'key "id" invalid: synthetic detail'),
            ("invalid_version", {"version": "not-version"}, 1,
             'key "version" invalid: synthetic detail'),
            ("empty_maintainer", {"maintainer": ""}, 1,
             'key "maintainer" invalid: synthetic detail'),
        )
        banners = (
            "Blender 4.4.3 (hash 802179c51ccc built 2025-04-29 15:12:13)",
            "Blender 4.5.15 LTS (hash 5afeabba6097 built 2026-10-22 01:33:47)",
            "Blender 5.2.1 LTS (hash 9e2066aef7ef built 2026-08-25 02:12:34)",
        )
        for banner in banners:
            for name, change, exitcode, diagnostic in cases:
                for newline in ("\n", "\r\n"):
                    with self.subTest(blender=banner.split()[1], case=name, newline=repr(newline)):
                        status_line = (
                            'Success parsing TOML in "/synthetic/private-token/manifest"'
                            if diagnostic is None else
                            'Error parsing TOML "/synthetic/private-token/manifest"')
                        lines = ["", banner, status_line]
                        if diagnostic:
                            lines.append(diagnostic)
                        lines += ["", "Blender quit", ""]
                        output = newline.join(lines)
                        report = compare_official_validation({**fields(), **change}, exitcode, output)
                        self.assertEqual(report["status"], "agreement")
                        self.assertTrue(report["complete_diagnostic_agreement"])
                        self.assertEqual(report["official_observation"]["status"],
                                         "accepted" if exitcode == 0 else "rejected")
                        self.assertFalse(report["official_observation"]["has_unrecognized_diagnostics"])
                        self.assertFalse(report["official_observation"]["authenticates_log"])
                        self.assertFalse(report["owner_approval_verified"])
                        self.assertFalse(report["license_compatibility_verified"])
                        self.assertNotIn("private-token", str(report))
                        self.assertNotIn("/synthetic/", str(report))

    def test_r5_partial_wrong_and_ambiguous_official_logs_do_not_agree(self):
        """Missing, mismatched, and unrecognized fields are separate outcomes."""
        # The correct local findings are TWO missing fields. Do not promote a
        # partial matching validator log to complete diagnostic agreement.
        source = {**fields(), "license": None, "version": None}
        cases = (
            ("both_expected", 'missing "license"\nmissing "version"', "agreement", False),
            ("only_one_expected", 'missing "license"', "partial_diagnostic_agreement", False),
            ("wrong_known_field", 'missing "id"', "disagreement", False),
            ("unexpected_field", 'missing "license"\nmissing "private_field"', "unclassified", True),
            ("duplicate", 'missing "license"\nmissing "license"', "unclassified", True),
            ("contradiction",
             'missing "license"\nkey "license" invalid: conflicting data', "unclassified", True),
            ("success_and_missing",
             'Success parsing TOML in "synthetic"\nmissing "license"', "unclassified", True),
            ("error_after_success",
             'Success parsing TOML in "synthetic"\nError parsing TOML "synthetic"\nmissing "license"',
             "unclassified", True),
            ("new_warning", 'missing "license"\nWARNING: private-marker-r5', "unclassified", True),
        )
        banners = ("Blender 4.4.3", "Blender 4.5.15 LTS", "Blender 5.2.1 LTS")
        for banner in banners:
            for name, lines, expected, unknown in cases:
                with self.subTest(blender=banner, case=name):
                    output = banner + "\nError parsing TOML \"synthetic\"\n" + lines + "\nBlender quit"
                    result = compare_official_validation(source, 1, output)
                    # The success/error conflict is unclassified even when
                    # the known field lines agree with the local findings.
                    self.assertEqual(result["status"], expected)
                    self.assertEqual(result["complete_diagnostic_agreement"], expected == "agreement")
                    self.assertEqual(result["official_observation"]["has_unrecognized_diagnostics"], unknown)
                    self.assertFalse(result["official_observation"]["authenticates_log"])
                    self.assertNotIn("private-marker-r5", str(result))
                    self.assertNotIn("private_field", str(result))
                    self.assertNotIn("conflicting data", str(result))

    def test_r5_unknown_output_position_and_value_never_leak(self):
        """Unknown stdout/stderr lines cannot be silently ignored or echoed."""
        from cbdk.extension_manifest import observe_official_validation
        secret = "synthetic-secret-r5@example.invalid"
        source = {**fields(), "maintainer": secret}
        success = 'Success parsing TOML in "/private/synthetic-secret-r5/manifest.toml"'
        known = "Blender 5.2.1 LTS (hash 9e2066aef7ef built 2026-08-25 02:12:34)"
        self.assertEqual(compare_official_validation(source, 0, known + "\n" + success)["status"],
                         "agreement")
        for location in ("before", "between", "after"):
            with self.subTest(location=location):
                unexpected = "Unknown validator note: " + secret
                lines = ([unexpected, known, success] if location == "before" else
                         [known, unexpected, success] if location == "between" else
                         [known, success, unexpected])
                output = "\n".join(lines)
                observed = observe_official_validation(0, output)
                result = compare_official_validation(source, 0, output)
                self.assertEqual(observed["status"], "unclassified")
                self.assertEqual(result["status"], "unclassified")
                self.assertTrue(observed["has_unrecognized_diagnostics"])
                self.assertFalse(result["complete_diagnostic_agreement"])
                self.assertFalse(observed["authenticates_log"])
                for sanitized in (str(observed), str(result)):
                    self.assertNotIn(secret, sanitized)
                    self.assertNotIn("/private/", sanitized)
                    self.assertNotIn("Unknown validator note", sanitized)

        # An error description may carry the fixture's private value even
        # when the *field identifier* is recognized. Never copy it to a report.
        bad_tagline = {**fields(), "tagline": "Invalid tagline!"}
        reason = 'key "tagline" invalid: ' + secret
        rejected = compare_official_validation(bad_tagline, 1, 'Error parsing TOML "fixture"\n' + reason)
        self.assertEqual(rejected["status"], "agreement")
        self.assertTrue(rejected["complete_diagnostic_agreement"])
        self.assertNotIn(secret, str(rejected))
        # This is classification, not log authentication or a license decision.
        self.assertFalse(rejected["official_observation"]["authenticates_log"])
        self.assertFalse(rejected["license_compatibility_verified"])

    def test_r6_bounded_official_log_stays_sanitized(self):
        """Bounded synthetic text must not override the known official verdict."""
        from cbdk.extension_manifest import observe_official_validation
        success = 'Success parsing TOML in "/private/synthetic-r6-fixture"'
        for length in (199_999, 200_000):
            with self.subTest(length=length):
                clean = success + "\n" + " " * (length - len(success) - 1)
                self.assertEqual(len(clean), length)
                matched = compare_official_validation(fields(), 0, clean)
                self.assertTrue(matched["complete_diagnostic_agreement"])
                self.assertNotIn("/private/", str(matched))
                self.assertFalse(matched["official_observation"]["authenticates_log"])
        warning = "WARNING: synthetic-r6-secret"
        unknown = (success + "\n" +
                   " " * (200_000 - len(success) - len(warning) - 2) +
                   "\n" + warning)
        self.assertEqual(len(unknown), 200_000)
        result = compare_official_validation(fields(), 0, unknown)
        self.assertEqual(result["status"], "unclassified")
        self.assertFalse(result["complete_diagnostic_agreement"])
        self.assertNotIn("synthetic-r6-secret", str(result))
        with self.assertRaises(ValueError):
            observe_official_validation(0, clean + "X" * 3)

    def test_official_fields_must_match_not_just_nonzero_exit(self):
        data = {**fields(), "license": None}
        matched = compare_official_validation(data, 1, 'Error parsing TOML "/private/source"\nmissing "license"')
        self.assertEqual(matched['status'], 'agreement')
        self.assertNotIn('/private', str(matched))
        wrong = compare_official_validation(data, 1, 'missing "version"')
        self.assertEqual(wrong['status'], 'disagreement')
        unknown = compare_official_validation(data, 1, 'Permission denied: /private/source')
        self.assertEqual(unknown['status'], 'unclassified')

    def test_success_requires_marker_and_failures_cannot_be_promoted(self):
        self.assertEqual(compare_official_validation(fields(), 0, 'Success parsing TOML in "fixture"')['status'], 'agreement')
        for code, text in ((0, ''), (0, 'missing "license"'), (-9, 'missing "license"'),
                           (1, 'Success parsing TOML in "fixture"')):
            with self.subTest(code=code, text=text):
                self.assertFalse(compare_official_validation(fields(), code, text)['complete_diagnostic_agreement'])
        with self.assertRaises(ValueError):
            compare_official_validation(fields(), True, '')

    def test_partial_and_unsupported_diagnostics_remain_distinct(self):
        result = compare_official_validation({**fields(), 'license': None, 'version': None}, 1, 'missing "license"')
        self.assertEqual(result['status'], 'partial_diagnostic_agreement')
        self.assertFalse(result['complete_diagnostic_agreement'])
        result = compare_official_validation({**fields(), 'permissions': {}}, 0, 'Success parsing TOML in "fixture"')
        self.assertEqual(result['status'], 'outside_supported_subset')
        self.assertFalse(result['complete_diagnostic_agreement'])


    def test_unknown_diagnostics_do_not_appear_to_agree(self):
        from cbdk.extension_manifest import observe_official_validation
        missing_license = {**fields(), "license": None}
        logs = (
            'missing "license"\nmissing "unknown_private"',
            'missing "license"\nkey "unreviewed_field" invalid: unexpected',
            'missing "license"\nmissing "license"',
            'missing "license"\nError: other validator problem',
            'missing "license"\nTraceback (most recent call last):',
        )
        for log in logs:
            with self.subTest(log=log):
                report = compare_official_validation(missing_license, 1, log)
                self.assertEqual(report["status"], "unclassified")
                self.assertTrue(report["official_observation"]["has_unrecognized_diagnostics"])
                self.assertFalse(report["complete_diagnostic_agreement"])
                self.assertNotIn("unknown_private", str(report))

        malformed_success = 'Success parsing TOML in "fixture" unexpected suffix'
        observed = observe_official_validation(0, malformed_success)
        self.assertEqual(observed["status"], "unclassified")
        self.assertTrue(observed["has_unrecognized_diagnostics"])
        self.assertEqual(observe_official_validation(0, 'Success parsing TOML in "fixture"')["status"], "accepted")


    def test_r3_unexpected_or_contradictory_validator_output_is_unclassified(self):
        """Unknown or inconsistent logs must not be mistaken for agreement."""
        from cbdk.extension_manifest import observe_official_validation
        incomplete = {**fields(), "license": None}
        cases = (
            ("unknown_rejection_line", incomplete, 1,
             'Error parsing TOML "synthetic"\nmissing "license"\nNew diagnostic: hidden private value'),
            ("unknown_rejection_footer", incomplete, 1,
             'missing "license"\nvalidation status unavailable'),
            ("conflicting_field_diagnostics", incomplete, 1,
             'missing "license"\nkey "license" invalid: synthetic contradiction'),
            ("success_plus_error_header", fields(), 0,
             'Success parsing TOML in "synthetic"\nError parsing TOML "synthetic"'),
            ("error_header_then_success", fields(), 0,
             'Error parsing TOML "synthetic"\nSuccess parsing TOML in "synthetic"'),
            ("success_plus_warning", fields(), 0,
             'Success parsing TOML in "synthetic"\nWARNING: hidden private value'),
            ("success_plus_unknown_line", fields(), 0,
             'Success parsing TOML in "synthetic"\nunexpected private line'),
            ("duplicate_generic_error_header", incomplete, 1,
             'Error parsing TOML "synthetic"\nError parsing TOML "synthetic"\nmissing "license"'),
        )
        for label, source, exitcode, output in cases:
            with self.subTest(case=label):
                report = compare_official_validation(source, exitcode, output)
                self.assertEqual(report["status"], "unclassified")
                self.assertFalse(report["complete_diagnostic_agreement"])
                self.assertEqual(report["official_observation"]["status"], "unclassified")
                self.assertTrue(report["official_observation"]["has_unrecognized_diagnostics"])
                self.assertNotIn("hidden private value", str(report))
                self.assertNotIn("private line", str(report))

        # Harmless known Blender startup and shutdown lines may accompany
        # real official-validator results. Synthetic test, no Blender executed.
        for version, suffix in (
            ("4.4.3", ""),
            ("4.5.15", " LTS"),
            ("5.2.1", " LTS"),
        ):
            with self.subTest(version=version):
                output = ('Blender ' + version + suffix
                          + ' (hash deadbeef1234 built 2026-01-01 00:00:00)\n'
                          + 'Success parsing TOML in "synthetic"\nBlender quit')
                report = compare_official_validation(fields(), 0, output)
                self.assertEqual(report["status"], "agreement")
                self.assertTrue(report["complete_diagnostic_agreement"])
                observed = observe_official_validation(0, output)
                self.assertFalse(observed["has_unrecognized_diagnostics"])

    def test_guidance_never_copies_owner_values(self):
        data = {**fields(), 'maintainer': 'Private Person email@example.invalid', 'version': None}
        rows = manifest_field_diagnostics(data)
        self.assertEqual(next(r['status'] for r in rows if r['field']=='version'), 'missing')
        self.assertNotIn('Private Person', str(rows))

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
