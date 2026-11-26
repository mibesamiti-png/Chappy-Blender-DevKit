"""R26 synthetic controls for normalized observations, not Blender evidence."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from cbdk.parameter_fixture_evidence import (
    CASE, PROPERTIES, STATIC_COUNTS, NATIVE_FLAGS, reduce_parameter_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/cbdk_parameter_experiment.py"
PRIVATE = "private/source/never-copy"
RUN = "1" * 32
DIGEST = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def identity(version="4.4.3"):
    return dict(case=CASE, blender=version, run_id=RUN, source_sha256=DIGEST)


def observations(version="4.4.3"):
    key = identity(version)
    static = {**key, "properties": [
        {"property": prop, "declaration_count": 1, "same_class_self_count": 1,
         "geometry_path_count": 1, "expected_api_observed": True}
        for prop in PROPERTIES]}
    native = {**key, "properties": [
        {"property": prop, **dict.fromkeys(NATIVE_FLAGS, True)} for prop in PROPERTIES],
        "cleanup_verified": True, "source_unchanged": True}
    return static, native


def reduce(static, native, version="4.4.3", **overrides):
    return reduce_parameter_evidence(static, native, **{**identity(version), **overrides})


class ParameterEvidenceTests(unittest.TestCase):
    def assert_unverified(self, report):
        self.assertFalse(report["same_fixture_observations_verified"])
        self.assertFalse(any(report["safety"].values()))
        self.assertNotIn(PRIVATE, json.dumps(report))

    def test_fixed_three_version_matrix_and_order_independence(self):
        for version in ("4.4.3", "4.5.15", "5.2.1"):
            a, n = observations(version)
            n["properties"].reverse()
            before = copy.deepcopy((a, n))
            report = reduce(a, n, version)
            self.assertEqual(report["status"], "verified_fixed_observations")
            self.assertTrue(report["same_fixture_observations_verified"])
            self.assertEqual(report["reason_codes"], [])
            self.assertEqual([x["property"] for x in report["properties"]], list(PROPERTIES))
            self.assertTrue(all(x["status"] == "matched" for x in report["properties"]))
            self.assertFalse(any(report["safety"].values()))
            self.assertEqual((a, n), before)

    def test_missing_static_native_or_property_never_passes(self):
        a, n = observations()
        for first, second, reason in (
            (a, None, "native_observation_missing"),
            (None, n, "static_observation_missing"),
            (None, None, "static_observation_missing"),
            ({**a, "properties": a["properties"][:1]}, n, "static_observation_missing"),
            (a, {**n, "properties": []}, "native_observation_missing"),
        ):
            with self.subTest(reason=reason):
                result = reduce(first, second)
                self.assertEqual(result["status"], "incomplete")
                self.assertIn(reason, result["reason_codes"])
                self.assert_unverified(result)

    def test_static_ambiguity_and_missing_paths(self):
        for updates, reason in (
            ({"declaration_count": 0}, "static_declaration_missing"),
            ({"declaration_count": 2}, "static_declaration_ambiguous"),
            ({"same_class_self_count": 0}, "same_class_reference_missing"),
            ({"geometry_path_count": 0, "expected_api_observed": False}, "geometry_path_missing"),
            ({"expected_api_observed": False}, "expected_api_missing"),
        ):
            a, n = observations()
            a["properties"][0].update(updates)
            result = reduce(a, n)
            self.assertEqual(result["status"], "unverified")
            self.assertIn(reason, result["properties"][0]["reason_codes"])
            self.assert_unverified(result)

    def test_registration_only_and_each_negative_runtime_observation(self):
        reasons = (
            "registration_unverified", "readback_unverified",
            "generated_target_effect_unverified", "imported_target_effect_unverified",
            "generated_unrelated_changed_or_unverified", "imported_unrelated_changed_or_unverified",
        )
        for flag, reason in zip(NATIVE_FLAGS, reasons):
            a, n = observations()
            row = n["properties"][1]
            row[flag] = False
            if flag == "registered_on_expected_instance":
                row["value_readback_verified"] = False
            report = reduce(a, n)
            self.assertEqual(report["status"], "unverified")
            self.assertIn(reason, report["properties"][1]["reason_codes"])
            self.assert_unverified(report)
        a, n = observations()
        for row in n["properties"]:
            for flag in NATIVE_FLAGS[2:]:
                row[flag] = False
        self.assert_unverified(reduce(a, n))

    def test_cleanup_and_source_unchanged_are_required(self):
        for flag, reason in (("cleanup_verified", "cleanup_unverified"),
                             ("source_unchanged", "source_unchanged_unverified")):
            a, n = observations()
            n[flag] = False
            report = reduce(a, n)
            self.assertEqual(report["status"], "unverified")
            self.assertIn(reason, report["reason_codes"])
            self.assert_unverified(report)

    def test_identity_from_parent_not_from_observations(self):
        for key, value in (("case", PRIVATE), ("blender", "5.2.1"),
                           ("run_id", "2"*32), ("source_sha256", "b"*64)):
            for side in (0, 1, 2):
                a, n = observations()
                for envelope in (a, n) if side == 2 else ((a,) if side == 0 else (n,)):
                    envelope[key] = value
                report = reduce(a, n)
                self.assertEqual(report["status"], "rejected")
                self.assert_unverified(report)
        a, n = observations()
        self.assert_unverified(reduce(a, n, run_id="2"*32))

    def test_duplicate_unknown_malformed_and_overclaim(self):
        changes = (
            lambda a, n: a["properties"].append(a["properties"][0]),
            lambda a, n: n["properties"].__setitem__(1, n["properties"][0]),
            lambda a, n: a["properties"][0].update(property=PRIVATE),
            lambda a, n: n["properties"][0].update(property=[]),
            lambda a, n: a.update(approved=True),
            lambda a, n: n["properties"][0].update(causality_proven=True),
            lambda a, n: n["properties"][0].pop("target_changed_imported"),
            lambda a, n: a["properties"][0].update(declaration_count=True),
            lambda a, n: a["properties"][0].update(same_class_self_count=-1),
            lambda a, n: a["properties"][0].update(geometry_path_count=1.0),
            lambda a, n: n["properties"][0].update(value_readback_verified=1),
            lambda a, n: n.update(cleanup_verified=1),
            lambda a, n: n.update(source_unchanged=None),
            lambda a, n: a.update(properties="not rows"),
            lambda a, n: n.update(source_sha256="A"*64),
        )
        for change in changes:
            a, n = observations()
            change(a, n)
            report = reduce(a, n)
            self.assertEqual(report["status"], "rejected")
            self.assert_unverified(report)

    def test_contradictory_observations(self):
        a, n = observations()
        a["properties"][0]["geometry_path_count"] = 0
        self.assertEqual(reduce(a, n)["reason_codes"], ["contradictory_observation"])
        a, n = observations()
        n["properties"][0]["registered_on_expected_instance"] = False
        result = reduce(a, n)
        self.assertEqual(result["reason_codes"], ["contradictory_observation"])
        self.assert_unverified(result)


if __name__ == "__main__":
    unittest.main()
