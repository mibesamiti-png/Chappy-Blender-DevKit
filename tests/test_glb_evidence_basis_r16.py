"""R16 negative controls for the R15 self-declared GLB evidence basis.

Synthetic evidence and fake literal tokens only; no private GLBs, real
hashes of geometry, addon execution or native source paths. The expected
status for matching self-declarations is NOT authenticated same-run proof.
The R15 implementation is intentionally left unchanged.
"""
from __future__ import annotations

import copy
import json
import unittest

from cbdk.glb_evidence_basis_r15 import build_bound_glb_evidence_triage
from test_glb_evidence_basis_r15 import BASIS, claimed_sources, reports


def review(inputs, *, records=None, expected=BASIS):
    if records is None:
        records = claimed_sources(inputs)
    return build_bound_glb_evidence_triage(
        **inputs, source_basis=records, expected_basis=expected)


class R16GLBSelfClaimLimitTests(unittest.TestCase):
    def assert_not_authoritative(self, result):
        self.assertEqual(result["status"], "review_only")
        self.assertEqual(result["anonymous_evidence"]["status"], "review_only")
        self.assertFalse(result["anonymous_evidence"]["evidence_sources_verified_same_run"])
        self.assertFalse(any(result["safety"].values()))
        basis = result["basis_review"]
        for name in (
            "claimed_tokens_authentic", "claims_bound_to_report_content",
            "sources_verified_same_run", "same_trial_or_revision_proven",
            "hash_equality_proves_geometry", "hash_equality_authorizes_edits",
        ):
            self.assertIs(basis[name], False)
        serialized = json.dumps(result, sort_keys=True, allow_nan=False)
        for fake_secret in (
            BASIS["session_token"], BASIS["trial_token"],
            BASIS["baseline_digest"], "PERSONAL_TEST_SOURCE.glb",
            "UNRELEASED_ASSET_NAME",
        ):
            self.assertNotIn(fake_secret, serialized)

    def test_identical_claims_and_replay_cannot_authenticate(self):
        original = reports("identical")
        snapshot = copy.deepcopy(original)
        first = review(original)
        replayed = review(copy.deepcopy(original))
        self.assertEqual(first, replayed)
        self.assertEqual(original, snapshot)
        self.assertEqual(first["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assertEqual(first["basis_review"]["reason_codes"], [])
        self.assert_not_authoritative(first)

    def test_old_revision_matching_itself_is_not_freshness_proof(self):
        inputs = reports("opening")
        old = dict(BASIS, revision=1)
        old_claims = {key: dict(old) for key in inputs}
        accepted = review(inputs, records=old_claims, expected=old)
        self.assertEqual(accepted["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assert_not_authoritative(accepted)
        # It is only *relative to a separately supplied new claim* that
        # the old declaration can be flagged as stale.
        newer = dict(BASIS, revision=2)
        flagged = review(inputs, records=old_claims, expected=newer)
        self.assertEqual(flagged["basis_review"]["status"], "conflict")
        self.assertIn("stale_revision", flagged["basis_review"]["reason_codes"])
        self.assert_not_authoritative(flagged)

    def test_replaced_semantically_valid_report_with_same_counts_is_undetectable(self):
        baseline = reports("identical")
        foreign = reports("opening")  # same face counts, genuinely moved opening
        for slot in ("comparison", "sampled_surface",
                     "boundary_reference", "boundary_candidate"):
            with self.subTest(slot=slot):
                changed = copy.deepcopy(baseline)
                changed[slot] = copy.deepcopy(foreign[slot])
                result = review(changed)
                # This deliberately demonstrates a LIMITATION, not a pass of
                # provenance verification: no source content is bound to token.
                self.assertEqual(result["basis_review"]["status"],
                                 "declared_consistent_unverified")
                self.assertEqual(result["basis_review"]["reason_codes"], [])
                self.assert_not_authoritative(result)

    def test_mixed_batches_at_equal_triangle_counts_are_not_detected(self):
        # Evidence from three separate synthetic runs has matching counts,
        # intentionally reused self-claims, and no trusted run manifest.
        a = reports("identical")
        b = reports("displacement")
        c = reports("opening")
        mixture = {
            "comparison": c["comparison"],
            "boundary_reference": a["boundary_reference"],
            "boundary_candidate": b["boundary_candidate"],
            "sampled_surface": b["sampled_surface"],
        }
        one = review(mixture)
        two = review(copy.deepcopy(mixture))
        self.assertEqual(one, two)
        self.assertEqual(one["basis_review"]["source_count"], 4)
        self.assertEqual(one["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assert_not_authoritative(one)

    def test_distinct_claims_at_batch_boundary_do_report_conflict(self):
        inputs = reports("identical")
        claims = claimed_sources(inputs)
        claims["sampled_surface"] = dict(
            BASIS, session_token="d" * 32, trial_token="e" * 16,
            baseline_digest="f" * 64, revision=3)
        output = review(inputs, records=claims)
        self.assertEqual(output["basis_review"]["status"], "conflict")
        self.assertEqual(output["basis_review"]["reason_codes"], [
            "session_conflict", "trial_conflict", "baseline_conflict",
            "stale_revision",
        ])
        self.assert_not_authoritative(output)

    def test_missing_or_unanchored_claims_stay_unknown(self):
        inputs = reports("identical")
        full = claimed_sources(inputs)
        unanchored = build_bound_glb_evidence_triage(
            **inputs, source_basis=full, expected_basis=None)
        self.assertEqual(unanchored["basis_review"]["status"], "unknown")
        self.assertIn("missing_expected_basis",
                      unanchored["basis_review"]["reason_codes"])
        self.assert_not_authoritative(unanchored)

        for missing in ("comparison", "sampled_surface",
                        "boundary_reference", "boundary_candidate"):
            with self.subTest(missing=missing):
                partial = copy.deepcopy(full)
                partial.pop(missing)
                report = review(inputs, records=partial)
                self.assertEqual(report["basis_review"]["status"], "unknown")
                self.assertIn("missing_basis",
                              report["basis_review"]["reason_codes"])
                self.assertIn(missing, report["basis_review"]["unbound_sources"])
                self.assert_not_authoritative(report)

    def test_missing_source_never_inherits_a_reused_basis(self):
        inputs = reports("identical")
        only = {"comparison": inputs["comparison"]}
        result = review(only)
        self.assertEqual(result["basis_review"]["status"], "unknown")
        self.assertIn("insufficient_independent_sources",
                      result["basis_review"]["reason_codes"])
        self.assertEqual(result["anonymous_evidence"]["channels"]
                         ["sampled_surface_distance"]["status"], "not_measured")
        self.assert_not_authoritative(result)

        with self.assertRaises(ValueError):
            # No basis for an absent source may be supplied as if measured.
            review(only, records={
                "comparison": dict(BASIS),
                "sampled_surface": dict(BASIS),
            })

    def test_skipped_surface_stays_unmeasured_despite_matching_claim(self):
        inputs = reports("identical")
        inputs["sampled_surface"] = {
            "kind": "cbdk_glb_surface_review", "schema_version": 1,
            "source": "local_blender_import_aggregate_only",
            "status": "skipped", "reason": "triangle_limit",
            "reference_triangles": 8, "candidate_triangles": 513,
            "surface_observation": "not_measured", "auto_apply": False,
            "complete_surface_equivalence_proven": False,
            "safety": {
                "executes_addon_code": False, "uploads_private_glb": False,
                "saves_raw_mesh_vertices": False, "changes_source_glbs": False,
            },
        }
        output = review(inputs)
        # A declared source is not necessarily a successful measurement.
        self.assertEqual(output["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assertEqual(output["anonymous_evidence"]["channels"]
                         ["sampled_surface_distance"]["status"], "not_measured")
        self.assertIn("sampled_surface_distance",
                      output["anonymous_evidence"]["unobserved_channels"])
        self.assert_not_authoritative(output)

    def test_count_conflict_is_detectable_but_matching_counts_are_not_proof(self):
        missing = reports("missing")  # reference=9, candidate=8 triangles
        identical = reports("identical")  # both=8
        # Identical self-claims but mismatched aggregate counts are evidence
        # against mixing these particular source reports.
        mixed = copy.deepcopy(missing)
        mixed["boundary_reference"] = identical["boundary_reference"]
        flagged = review(mixed)
        self.assertEqual(flagged["basis_review"]["status"], "conflict")
        self.assertIn("triangle_count_conflict",
                      flagged["basis_review"]["reason_codes"])
        self.assert_not_authoritative(flagged)
        # Equal face totals in another mixture don't prove any identity.
        matching = review(reports("opening"))
        self.assertEqual(matching["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assert_not_authoritative(matching)

    def test_no_leak_from_fake_private_labels_or_reused_tokens(self):
        inputs = reports("opening")
        marker = "PERSONAL_TEST_SOURCE.glb"
        inputs["comparison"]["reference_source"] = marker
        inputs["comparison"]["candidate_source"] = "UNRELEASED_ASSET_NAME"
        before = copy.deepcopy(inputs)
        output = review(inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(output["basis_review"]["status"],
                         "declared_consistent_unverified")
        self.assert_not_authoritative(output)


if __name__ == "__main__":
    unittest.main()
