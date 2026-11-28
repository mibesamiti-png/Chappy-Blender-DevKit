"""R15: privacy-safe *declared* provenance review for anonymous GLB evidence.

Input records are untrusted caller declarations. Matching digests/tokens and
triangle counts may reveal a contradiction but cannot authenticate a producer,
prove that source reports came from the same run, or authorize modifications.

Only the five R14 input types are accepted; no files, Blender, addon Python,
network calls, paths, filenames, coordinates, declaration labels or digests
are copied to the result. The review is intentionally in-memory only.
"""
from __future__ import annotations

import re

from .glb_evidence_triage import build_glb_evidence_triage

KIND = "cbdk_glb_cross_evidence_basis_review_v1"
SOURCE_KEYS = (
    "comparison", "boundary_reference", "boundary_candidate",
    "sampled_surface", "static_property_triage",
)
BASIS_KEYS = frozenset(("session_token", "trial_token",
                        "baseline_digest", "revision"))
REASONS = (
    "triangle_count_conflict", "session_conflict", "trial_conflict",
    "baseline_conflict", "stale_revision", "unexpected_revision",
    "missing_basis", "missing_expected_basis",
    "insufficient_independent_sources",
)
MAX_REVISION = 1_000_000


def _basis(value):
    """Check a small, intentionally closed schema; never echo input secrets."""
    if not isinstance(value, dict) or set(value) != BASIS_KEYS:
        raise ValueError("Invalid GLB basis declaration")
    for key, length in (("session_token", 32), ("trial_token", 16),
                        ("baseline_digest", 64)):
        token = value[key]
        if not isinstance(token, str) or len(token) != length or re.fullmatch(
                "[0-9a-f]+", token) is None:
            raise ValueError("Invalid GLB basis declaration")
    if type(value["revision"]) is not int or not 1 <= value["revision"] <= MAX_REVISION:
        raise ValueError("Invalid GLB basis declaration")
    return value


def _triangle_disagreement(reference, candidate, surface):
    """Check available aggregate face totals, without linking input identity."""
    if reference is None or candidate is None or surface is None:
        return False
    if surface.get("status") != "review_only":
        return False
    left = reference["summary"]["triangle_count"]
    right = candidate["summary"]["triangle_count"]
    return (left != surface["reference_triangles"]
            or right != surface["candidate_triangles"])


def _basis_summary(present, records, expected, ref_audit, cand_audit, surface):
    if records is None:
        records = {}
    if not isinstance(records, dict) or not set(records).issubset(present):
        raise ValueError("Basis declarations must correspond to supplied reports")
    for record in records.values():
        _basis(record)
    if expected is not None:
        _basis(expected)

    reasons = set()
    if _triangle_disagreement(ref_audit, cand_audit, surface):
        reasons.add("triangle_count_conflict")
    if len(records) != len(present):
        reasons.add("missing_basis")
    if expected is None:
        reasons.add("missing_expected_basis")
    if len(present) < 2:
        reasons.add("insufficient_independent_sources")

    # Compare only self-declared fields, never hashes of private model bytes
    # or filenames. Expected basis is *another declaration*, not authority.
    reference = expected if expected is not None else next(iter(records.values()), None)
    if reference is not None:
        for value in records.values():
            if value["session_token"] != reference["session_token"]:
                reasons.add("session_conflict")
            if value["trial_token"] != reference["trial_token"]:
                reasons.add("trial_conflict")
            if value["baseline_digest"] != reference["baseline_digest"]:
                reasons.add("baseline_conflict")
            if value["revision"] < reference["revision"]:
                reasons.add("stale_revision")
            if value["revision"] > reference["revision"]:
                reasons.add("unexpected_revision")

    ordered = [r for r in REASONS if r in reasons]
    is_conflict = any(r in reasons for r in REASONS[:6])
    return {
        "status": "conflict" if is_conflict else (
            "unknown" if reasons else "declared_consistent_unverified"),
        "reason_codes": ordered,
        "source_count": len(present),
        "declared_source_count": len(records),
        "unbound_sources": [k for k in SOURCE_KEYS
                            if k in present and k not in records],
        "reference_basis_declared": expected is not None,
        "basis_is_caller_supplied": True,
        "claimed_tokens_authentic": False,
        "claims_bound_to_report_content": False,
        "sources_verified_same_run": False,
        "same_trial_or_revision_proven": False,
        "hash_equality_proves_geometry": False,
        "hash_equality_authorizes_edits": False,
    }


def build_bound_glb_evidence_triage(
    *, comparison=None, boundary_reference=None, boundary_candidate=None,
    sampled_surface=None, static_property_triage=None,
    source_basis=None, expected_basis=None,
):
    """Give reviewer an anonymous R14 view plus a conservative R15 basis audit.

    'declared_consistent_unverified' means declarations agree with a *supplied*
    expected basis. It NEVER means independently verified same-run data.
    Missing/conflicting/stale values remain explicitly unknown or conflicting.
    """
    inputs = {
        "comparison": comparison,
        "boundary_reference": boundary_reference,
        "boundary_candidate": boundary_candidate,
        "sampled_surface": sampled_surface,
        "static_property_triage": static_property_triage,
    }
    # Validate original report content before treating any declared basis as
    # meaningful; R14 maintains R2/R3/R8/R13 safety and shape limits.
    anonymous = build_glb_evidence_triage(**inputs)
    present = {key for key, value in inputs.items() if value is not None}
    basis = _basis_summary(
        present, source_basis, expected_basis,
        boundary_reference, boundary_candidate, sampled_surface)
    return {
        "kind": KIND, "schema_version": 1, "status": "review_only",
        "anonymous_evidence": anonymous,
        "basis_review": basis,
        "safety": {
            "executes_addon_code": False,
            "reads_private_glb": False,
            "emits_private_identifiers": False,
            "auto_applies": False,
            "proves_identity": False,
            "proves_causality": False,
            "authenticates_evidence": False,
            "authorizes_distribution": False,
        },
    }
