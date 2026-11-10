"""R15: explicitly declared GLB measurement basis is not authentication.

All inputs are CBDK-authored Python synthetic fixtures, with fixed fake
hexadecimal tokens (never a hash of a user asset or private source).
"""
from __future__ import annotations

import copy
import json
import unittest

from cbdk.glb_evidence_basis_r15 import (
    KIND, SOURCE_KEYS, build_bound_glb_evidence_triage,
)
from cbdk.glb_experiment_triage import build_experiment_triage
from test_glb_evidence_triage_r14 import authored_case
import test_glb_visual_experiment_review as linked_fixture


BASIS = {
    "session_token": "a" * 32,
    "trial_token": "c" * 16,
    "baseline_digest": "b" * 64,
    "revision": 4,
}


def changed_basis(**changes):
    return dict(BASIS, **changes)


def reports(case="identical"):
    comparison, left, right, surface = authored_case(case)
    return {
        "comparison": comparison,
        "boundary_reference": left,
        "boundary_candidate": right,
        "sampled_surface": surface,
    }


def claimed_sources(inputs):
    return {key: dict(BASIS) for key in inputs}


class R15GLBDeclaredBasisTests(unittest.TestCase):
    def review(self, inputs=None, *, records=None, expected=None):
        if inputs is None:
            inputs = reports("identical")
        if records is None:
            records = claimed_sources(inputs)
        if expected is None:
            expected = BASIS
        return build_bound_glb_evidence_triage(
            **inputs, source_basis=records, expected_basis=expected)

    def assert_review_only(self, report):
        self.assertEqual(report["kind"], KIND)
        self.assertEqual(report["status"], "review_only")
        self.assertFalse(any(report["safety"].values()))
        self.assertEqual(report["anonymous_evidence"]["status"], "review_only")
        self.assertFalse(report["anonymous_evidence"]
                         ["evidence_sources_verified_same_run"])
        basis = report["basis_review"]
        for name in ("claimed_tokens_authentic",
                     "claims_bound_to_report_content",
                     "sources_verified_same_run",
                     "same_trial_or_revision_proven",
                     "hash_equality_proves_geometry",
                     "hash_equality_authorizes_edits"):
            self.assertIs(basis[name], False)
        body = json.dumps(report, sort_keys=True, allow_nan=False)
        for secret in (BASIS["session_token"], BASIS["trial_token"],
                       BASIS["baseline_digest"], "TestBody",
                       "Missing", "private", "source_001.py"):
            self.assertNotIn(secret, body)

    def test_four_authored_conditions_consistent_declared_basis_is_not_proof(self):
        for case in ("identical", "displacement", "opening", "missing"):
            with self.subTest(case=case):
                inputs = reports(case)
                old = copy.deepcopy(inputs)
                result = self.review(inputs)
                self.assert_review_only(result)
                status = result["basis_review"]
                self.assertEqual(status["status"], "declared_consistent_unverified")
                self.assertEqual(status["reason_codes"], [])
                self.assertEqual(status["source_count"], 4)
                self.assertEqual(status["declared_source_count"], 4)
                self.assertEqual(status["unbound_sources"], [])
                self.assertEqual(inputs, old, "All evidence is read only")
                self.assertEqual(
                    result["anonymous_evidence"]["channels"]["boundary_counts"]
                    ["reference_boundary_edges"],
                    inputs["boundary_reference"]["summary"]["boundary_edges"])

    def test_mixed_trial_same_baseline_explicitly_conflicts(self):
        inputs = reports("identical")
        for mismatch in (
            {"trial_token": "d" * 16},
            {"session_token": "e" * 32},
            {"trial_token": "d" * 16, "session_token": "e" * 32},
        ):
            records = claimed_sources(inputs)
            records["sampled_surface"].update(mismatch)
            result = self.review(inputs, records=records)
            self.assert_review_only(result)
            self.assertEqual(result["basis_review"]["status"], "conflict")
            for field, code in (("trial_token", "trial_conflict"),
                                ("session_token", "session_conflict")):
                self.assertEqual(code in result["basis_review"]["reason_codes"],
                                 field in mismatch)

    def test_stale_and_new_revision_are_distinct_unverified_conflicts(self):
        inputs = reports("opening")
        for revision, reason in ((3, "stale_revision"),
                                 (5, "unexpected_revision")):
            records = claimed_sources(inputs)
            records["boundary_candidate"]["revision"] = revision
            result = self.review(inputs, records=records)
            self.assertEqual(result["basis_review"]["status"], "conflict")
            self.assertIn(reason, result["basis_review"]["reason_codes"])
            self.assert_review_only(result)
        # The same revision is not evidence of a fresh clock or trusted
        # producer. An old base matching itself remains explicitly unverified.
        earlier = changed_basis(revision=2)
        result = self.review(inputs, records={
            key: dict(earlier) for key in inputs
        }, expected=earlier)
        self.assertEqual(result["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assertFalse(result["basis_review"]["sources_verified_same_run"])

    def test_different_baseline_digest_is_conflict_not_identity(self):
        inputs = reports("displacement")
        records = claimed_sources(inputs)
        records["comparison"]["baseline_digest"] = "d" * 64
        review = self.review(inputs, records=records)
        self.assertEqual(review["basis_review"]["status"], "conflict")
        self.assertIn("baseline_conflict",
                      review["basis_review"]["reason_codes"])
        self.assert_review_only(review)

    def test_missing_expected_and_missing_source_basis_remain_unknown(self):
        inputs = reports("identical")
        records = claimed_sources(inputs)
        # Explicitly no independent expected basis: declarations agreeing
        # with one another is still an unanchored unknown.
        result = build_bound_glb_evidence_triage(
            **inputs, source_basis=records)
        self.assertEqual(result["basis_review"]["status"], "unknown")
        self.assertIn("missing_expected_basis",
                      result["basis_review"]["reason_codes"])
        records.pop("boundary_reference")
        result = self.review(inputs, records=records)
        self.assertEqual(result["basis_review"]["status"], "unknown")
        self.assertIn("missing_basis", result["basis_review"]["reason_codes"])
        self.assertEqual(result["basis_review"]["unbound_sources"],
                         ["boundary_reference"])
        self.assert_review_only(result)

    def test_single_or_zero_report_cannot_make_a_same_run_claim(self):
        self.assertEqual(set(SOURCE_KEYS), {
            "comparison", "boundary_reference", "boundary_candidate",
            "sampled_surface", "static_property_triage"})
        alone = {"comparison": reports("identical")["comparison"]}
        one = self.review(alone)
        self.assertEqual(one["basis_review"]["status"], "unknown")
        self.assertIn("insufficient_independent_sources",
                      one["basis_review"]["reason_codes"])
        empty = build_bound_glb_evidence_triage()
        self.assertEqual(empty["basis_review"]["status"], "unknown")
        self.assertEqual(empty["basis_review"]["source_count"], 0)
        self.assertEqual(
            set(empty["anonymous_evidence"]["unobserved_channels"]),
            set(empty["anonymous_evidence"]["channels"]))
        self.assert_review_only(one)
        self.assert_review_only(empty)

    def test_triangle_count_cross_check_detects_mixed_geometry(self):
        inputs = reports("missing")  # ref has 9 triangles; candidate has 8
        same = reports("identical")
        # Despite identical claimed session/trial/revision/digest, one
        # reference audit is from the wrong synthetic source.
        inputs["boundary_reference"] = same["boundary_reference"]
        output = self.review(inputs)
        self.assertEqual(output["basis_review"]["status"], "conflict")
        self.assertIn("triangle_count_conflict",
                      output["basis_review"]["reason_codes"])
        self.assertNotIn("baseline_conflict",
                         output["basis_review"]["reason_codes"])
        self.assert_review_only(output)

    def test_static_property_source_counts_are_private_and_unverified(self):
        fixture = linked_fixture.VisualExperimentTests(
            methodName="test_bound_review_separates_static_name_from_synthetic_observations")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        static = build_experiment_triage(fixture.visual, fixture.build())
        inputs = reports("identical")
        inputs["static_property_triage"] = static
        result = self.review(inputs)
        self.assertEqual(result["basis_review"]["source_count"], 5)
        self.assertEqual(result["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assertEqual(result["anonymous_evidence"]["channels"]
                         ["static_property_candidates"]["status"],
                         "unverified_syntax_candidates")
        self.assert_review_only(result)

    def test_invalid_declared_basis_and_extra_sources_fail_closed(self):
        inputs = reports("identical")
        originals = claimed_sources(inputs)
        examples = [
            {"session_token": "PRIVATE_USER_DOCUMENT.glb"},
            {"session_token": "a" * 31},
            {"trial_token": "g" * 16},
            {"baseline_digest": "f" * 63},
            {"revision": True},
            {"revision": 0},
            {"revision": 1000001},
            {"unexpected_file_path": "/private/source.glb"},
        ]
        for change in examples:
            with self.subTest(change=list(change)):
                records = copy.deepcopy(originals)
                records["comparison"].update(change)
                with self.assertRaises(ValueError):
                    build_bound_glb_evidence_triage(
                        **inputs, source_basis=records, expected_basis=BASIS)
        records = copy.deepcopy(originals)
        records["static_property_triage"] = dict(BASIS)
        with self.assertRaises(ValueError):
            self.review(inputs, records=records)
        with self.assertRaises(ValueError):
            self.review(inputs, expected=changed_basis(revision=False))

    def test_report_semantic_forgery_is_rejected_before_basis(self):
        inputs = reports("identical")
        inputs["comparison"]["passed"] = False
        with self.assertRaises(ValueError):
            self.review(inputs)
        inputs = reports("identical")
        inputs["sampled_surface"]["symmetric_sampled_max"] = float("nan")
        with self.assertRaises(ValueError):
            self.review(inputs)

    def test_output_deterministic_and_no_source_path_leakage(self):
        inputs = reports("opening")
        one = self.review(inputs)
        changed = copy.deepcopy(inputs)
        changed["comparison"]["differences"].reverse()
        changed["comparison"]["reference_source"] = "private/reference.glb"
        changed["comparison"]["candidate_source"] = "private/candidate.glb"
        second = self.review(changed)
        self.assertEqual(one, second)
        self.assert_review_only(second)


if __name__ == "__main__":
    unittest.main()
