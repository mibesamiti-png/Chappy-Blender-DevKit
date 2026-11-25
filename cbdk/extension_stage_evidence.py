"""R25 fixed CI stage consistency reducer; never an execution authority.

Only normalized observations from the trusted CI fixture are in scope.
No paths, free-form exceptions, raw logs, public CLI or code execution.
A matching hash/run token is a consistency check, not authentication.
"""
from __future__ import annotations

import re

from .extension_preflight import PreviewArchiveError
from .extension_manifest import compare_official_validation

CASES = frozenset({"read", "edit", "grouped"})
VERSIONS = frozenset({"4.4.3", "4.5.15", "5.2.1"})
STAGES = ("generation", "validate", "enable", "operation", "cleanup", "sha_unchanged")
FAILURES = dict(zip(STAGES, ("generation_rejected", "validate_failed", "enable_failed",
                            "operation_failed", "cleanup_failed", "evidence_mismatch")))
_FIELDS = frozenset({"case", "blender", "run_id", "artifact_sha256", "stage", "status",
                     "reason", "diagnostic"})
_PREFLIGHT = frozenset({"archive_structure", "archive_identity", "provenance",
                        "archive_integrity", "dependency_closure"})
_DIAGNOSTICS = {
    "generation": _PREFLIGHT | {"invalid_input", "unclassified_generation"},
    "validate": frozenset({"official_rejected", "official_unclassified", "official_disagreement"}),
}
_DIGEST = re.compile(r"[0-9a-f]{64}")
_RUN = re.compile(r"[0-9a-f]{32}")


def generation_diagnostic(error):
    """Use existing controlled preflight categories, never exception text."""
    if isinstance(error, PreviewArchiveError):
        category = error.category
        if type(category) is str and category in _PREFLIGHT:
            return category
    if isinstance(error, ValueError):
        return "invalid_input"
    return "unclassified_generation"


def official_validate_observation(fields, returncode, output):
    """Reuse existing bounded official CLI comparison, return fixed vocabulary.

    The caller must observe the actual process for the same artifact; this
    comparison alone does not prove the supplied output came from Blender.
    """
    try:
        compared = compare_official_validation(fields, returncode, output)
    except (ValueError, TypeError):
        return "failed", "official_unclassified"
    observed = compared["official_observation"]["status"]
    if (returncode == 0 and observed == "accepted"
            and compared["complete_diagnostic_agreement"] is True
            and compared["local_status"] == "structurally_valid_subset"):
        return "passed", None
    if observed == "unclassified":
        return "failed", "official_unclassified"
    if observed == "rejected":
        return "failed", "official_rejected"
    return "failed", "official_disagreement"


def _is_identity(case, blender, run_id):
    return (type(case) is str and case in CASES
            and type(blender) is str and blender in VERSIONS
            and type(run_id) is str and _RUN.fullmatch(run_id) is not None)


def _is_digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _summary(status, reason, *, case=None, blender=None, run_id=None,
             digest=None, stages=(), failure_stage=None, diagnostic=None):
    # All values here are either constants or already validated fixed IDs.
    return {"schema_version": 1, "suite": "fixed_extension_stage_evidence",
            "status": status, "failure_reason": reason, "failure_stage": failure_stage,
            "diagnostic": diagnostic, "case": case, "blender": blender, "run_id": run_id,
            "artifact_sha256": digest, "passed_stages": list(stages),
            "same_artifact_stages_verified": status == "verified_fixed_stages",
            "approved": False, "release_authorized": False, "install_authorized": False,
            "gui_hotkey_verified": False, "official_install_exercised": False,
            "license_compatibility_verified": False, "redistribution_authorized": False,
            "authenticates_observations": False, "undo_redo_verified_by_reducer": False}


def reduce_stage_records(records, *, case, blender, run_id):
    """Require exact ordered six-stage records for one expected CI invocation.

    Every post-generation row (including not_run) carries the same digest.
    Generation failure and its not_run successors carry None. After failure,
    every later gate is not_run; physical emergency cleanup may still occur
    but cannot be counted as a successful continuation. Missing rows are
    incomplete, contradictions are mismatches, and neither is success.
    """
    def mismatch():
        return _summary("rejected", "evidence_mismatch")

    if not _is_identity(case, blender, run_id):
        return mismatch()
    if type(records) is not list or len(records) > len(STAGES):
        return mismatch()

    digest = None
    passed = []
    failure = None
    for index, row in enumerate(records):
        if (type(row) is not dict or set(row) != _FIELDS
                or not _is_identity(row["case"], row["blender"], row["run_id"])
                or (row["case"], row["blender"], row["run_id"]) != (case, blender, run_id)
                or type(row["stage"]) is not str or row["stage"] != STAGES[index]
                or type(row["status"]) is not str
                or row["status"] not in ("passed", "failed", "not_run")):
            return mismatch()
        stage, status = row["stage"], row["status"]
        sha, reason, diagnostic = row["artifact_sha256"], row["reason"], row["diagnostic"]
        if index == 0 and status == "passed":
            if not _is_digest(sha):
                return mismatch()
            digest = sha
        if digest is None:
            if sha is not None:
                return mismatch()
        elif not _is_digest(sha) or sha != digest:
            return mismatch()
        if failure is not None:
            if status != "not_run" or reason is not None or diagnostic is not None:
                return mismatch()
        elif status == "passed":
            if reason is not None or diagnostic is not None:
                return mismatch()
            passed.append(stage)
        elif status == "failed":
            if type(reason) is not str or reason != FAILURES[stage]:
                return mismatch()
            if diagnostic is not None and (type(diagnostic) is not str
                    or diagnostic not in _DIAGNOSTICS.get(stage, ())):
                return mismatch()
            failure = (stage, reason, diagnostic)
        else:
            return mismatch()

    identity = {"case": case, "blender": blender, "run_id": run_id,
                "digest": digest, "stages": passed}
    if len(records) != len(STAGES):
        return _summary("incomplete", "incomplete_evidence", **identity)
    if failure is not None:
        stage, reason, diagnostic = failure
        return _summary("failed", reason, failure_stage=stage, diagnostic=diagnostic, **identity)
    return _summary("verified_fixed_stages", None, **identity)
