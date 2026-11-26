"""R28 bounded candidate evidence and independent history replay (internal CI).

Reuse R27 strict measurement/identity primitives and GLB-022's replay principle:
derive each decision from observations, never from a claimed best or stop.
No I/O, imports of candidate code, execution, or dependency on B's evaluator.
"""
from __future__ import annotations

import hashlib

from .extension_stage_evidence import VERSIONS, _is_digest
from .parameter_fixture_evidence import _HEX32
from .parameter_source_evidence_r27 import (
    SOURCE_SHA256, BYTE_OFFSET, STAGES, SPHERE, CUBE, MEASUREMENT_FIELDS, RUN_FLAGS,
    _record, _bound, _flags, _number, _measurement, _fail,
)

CASE = "parameter_source_r28"
TRIALS = ("wrong_direction", "cross_part", "intermediate", "target")
VALUES = ((0.55, 0.08), (1.15, 0.20), (0.95, 0.08), (1.15, 0.08))
REFERENCE_PAIRS = (
    ("sphere_probe_down", "sphere_probe_down"),
    ("sphere_radius_changed", "bevel_probe_up"),
    ("sphere_probe_up", "sphere_probe_up"),
    ("sphere_radius_changed", "sphere_radius_changed"),
)
REFERENCES = ("baseline", "sphere_radius_changed", "bevel_width_changed",
              "sphere_probe_up", "sphere_probe_down", "bevel_probe_up", "bevel_probe_down")
PHASES = ("generated_mesh", "imported_glb_mesh")
PROPERTIES = ("sphere_radius", "bevel_width")
MARGIN = 1e-5
EXPECTED_DECISIONS = ("target_regression", "protected_part_regression",
                      "observed_improvement", "observed_target_reached")
IDENTITY = {"case_id", "run_id", "blender_version", "source_sha256", "reference_run_id"}
TRIAL_IDENTITY = IDENTITY | {"trial_id", "candidate_sha256"}
STAGE_FIELDS = TRIAL_IDENTITY | MEASUREMENT_FIELDS | {
    "stage", "actual_source_sha256", "rna_defaults", "rna_after_build",
    "registered", "cleanup_verified"}
DIFF_FIELDS = {"tokens", "ast_diff_verified", "exact_diff_verified", "restored_sha256"}
TRIAL_FIELDS = TRIAL_IDENTITY | RUN_FLAGS | {
    "diff", "stages", "restored_copy_sha256", "reference_glb_sha256"}
HISTORY_FIELDS = {"budget", "rows", "best_id", "stop_reason", "target_reached"}
ROW_FIELDS = {"trial_id", "generated_score", "imported_score", "decision",
              "best_before", "best_after"}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _identity(run_id, version, reference_run_id):
    if (type(version) is not str or version not in VERSIONS
            or any(type(v) is not str or _HEX32.fullmatch(v) is None
                   for v in (run_id, reference_run_id))
            or run_id == reference_run_id):
        _fail("identity_mismatch")
    return dict(case_id=CASE, run_id=run_id, blender_version=version,
                source_sha256=SOURCE_SHA256, reference_run_id=reference_run_id)


def _summary(status, reasons, identity=None, history=None):
    verified = status == "verified_fixed_history"
    return {"schema_version": 1, "suite": "fixed_parameter_candidate_evidence_r28",
            "status": status, "reason_codes": list(dict.fromkeys(reasons)),
            **(identity if identity is not None else dict.fromkeys(sorted(IDENTITY))),
            "history": history, "same_fixture_selection_verified": verified,
            "safety": {key: False for key in (
                "authenticates_observations", "causality_proven", "optimal_value_verified",
                "general_geometry_equivalence_verified", "generalizes_to_user_addons",
                "source_execution_authorized", "user_addon_executed", "edits_user_code",
                "auto_apply", "auto_adopt", "auto_approve", "redistribution_authorized")}}


def _fixed_candidate(source, index):
    """Independently derive exact permitted bytes from the pinned original."""
    if type(source) is not bytes or _sha(source) != SOURCE_SHA256:
        _fail("source_digest_mismatch")
    radius, bevel = VALUES[index]
    tokens = []
    for prop, old, new in (("sphere_radius", "0.75", f"{radius:.2f}"),
                           ("bevel_width", "0.08", f"{bevel:.2f}")):
        needle = b"default=" + old.encode("ascii")
        if source.count(needle) != 1:
            _fail("fixed_diff_mismatch")
        offset = source.index(needle) + len(b"default=")
        if prop == "sphere_radius" and offset != BYTE_OFFSET:
            _fail("fixed_diff_mismatch")
        if old != new:
            tokens.append(dict(property=prop, byte_offset=offset, old_token=old, new_token=new))
    candidate = source
    for row in tokens:
        offset = row["byte_offset"]
        candidate = candidate[:offset] + row["new_token"].encode("ascii") + candidate[offset+4:]
    restored = candidate
    for row in reversed(tokens):
        offset = row["byte_offset"]
        restored = restored[:offset] + row["old_token"].encode("ascii") + restored[offset+4:]
    if restored != source or len(tokens) != (2 if index == 1 else 1):
        _fail("restoration_mismatch")
    return candidate, tokens


def _reference_rows(references, identity):
    _record(references, {"case_id", "run_id", "blender_version", "source_sha256", "variants"})
    _bound(references, dict(case_id="parameter_fixture_r26", run_id=identity["reference_run_id"],
                            blender_version=identity["blender_version"], source_sha256=SOURCE_SHA256))
    variants = references["variants"]
    if type(variants) is not dict or not set(variants) <= set(REFERENCES):
        _fail("measurement_invalid")
    for row in variants.values():
        _record(row, MEASUREMENT_FIELDS)
        _measurement(row)
    return variants


def _trial_rows(record, identity, index, source, allowed, refs):
    """Validate complete or partial normalized evidence; no self-attested pass."""
    candidate, tokens = _fixed_candidate(source, index)
    trial_id = TRIALS[index]
    if type(allowed) is not bytes or allowed != candidate:
        _fail("fixed_candidate_mismatch")
    trial_identity = dict(**identity, trial_id=trial_id, candidate_sha256=_sha(candidate))
    _record(record, TRIAL_FIELDS)
    _bound(record, trial_identity)
    _flags(record, RUN_FLAGS)
    if not all(record[k] for k in RUN_FLAGS):
        _fail("copy_integrity_unverified")
    if type(record["restored_copy_sha256"]) is not str or record["restored_copy_sha256"] != SOURCE_SHA256:
        _fail("restoration_mismatch")
    diff = record["diff"]
    _record(diff, DIFF_FIELDS)
    _flags(diff, {"ast_diff_verified", "exact_diff_verified"})
    if not all(diff[k] for k in ("ast_diff_verified", "exact_diff_verified")):
        _fail("fixed_diff_mismatch")
    if type(diff["restored_sha256"]) is not str or diff["restored_sha256"] != SOURCE_SHA256:
        _fail("restoration_mismatch")
    actual_tokens = diff["tokens"]
    if type(actual_tokens) is not list or len(actual_tokens) != len(tokens):
        _fail("fixed_diff_mismatch")
    for actual, expected in zip(actual_tokens, tokens):
        _record(actual, set(expected))
        if any(type(actual[k]) is not type(v) or actual[k] != v for k, v in expected.items()):
            _fail("fixed_diff_mismatch")
    hashes = record["reference_glb_sha256"]
    _record(hashes, set(REFERENCES))
    if not all(_is_digest(v) for v in hashes.values()):
        _fail("measurement_invalid")
    if any(hashes[k] != v["glb_sha256"] for k, v in refs.items()):
        _fail("reference_digest_mismatch")
    rows = record["stages"]
    if type(rows) is not list or len(rows) > len(STAGES):
        _fail("evidence_mismatch")
    for pos, row in enumerate(rows):
        _record(row, STAGE_FIELDS)
        _bound(row, trial_identity)
        stage = STAGES[pos]
        if type(row["stage"]) is not str or row["stage"] != stage:
            _fail("stage_order_mismatch")
        expected_sha = _sha(candidate) if stage == "candidate" else SOURCE_SHA256
        if type(row["actual_source_sha256"]) is not str or row["actual_source_sha256"] != expected_sha:
            _fail("stage_source_mismatch")
        _flags(row, {"registered", "cleanup_verified"})
        if not row["registered"] or not row["cleanup_verified"]:
            _fail("stage_lifecycle_unverified")
        expected_values = VALUES[index] if stage == "candidate" else (0.75, 0.08)
        for name in ("rna_defaults", "rna_after_build"):
            _record(row[name], set(PROPERTIES))
            for prop, expected in zip(PROPERTIES, expected_values):
                value = row[name][prop]
                if not _number(value) or abs(value - expected) > 1e-6:
                    _fail("rna_default_mismatch")
        if row["rna_defaults"] != row["rna_after_build"]:
            _fail("rna_readback_mismatch")
        _measurement(row)
        for phase in PHASES:
            pair = REFERENCE_PAIRS[index] if stage == "candidate" else ("baseline", "baseline")
            for part, ref in zip((SPHERE, CUBE), pair):
                if ref in refs and row[phase][part] != refs[ref][phase][part]:
                    _fail("fixed_reference_geometry_mismatch")
    return rows


def _scores(row, target):
    return tuple(max(abs(a-b) for a,b in zip(row[phase][SPHERE]["world_dimensions"],
                                             target[phase][SPHERE]["world_dimensions"]))
                 for phase in PHASES)


def _replay(baseline, target, candidates, budget):
    """Independent fixed metric replay. Inputs already validated by reducer."""
    best = "baseline"
    best_scores = _scores(baseline, target)
    rows = []
    reached = False
    for trial_id, candidate in zip(TRIALS, candidates):
        scores = _scores(candidate, target)
        before = best
        if any(candidate[p][CUBE] != baseline[p][CUBE] for p in PHASES):
            decision = "protected_part_regression"
        elif all(s <= MARGIN for s in scores):
            if all(candidate[p][SPHERE] == target[p][SPHERE] for p in PHASES):
                decision = "observed_target_reached"
                best, best_scores, reached = trial_id, scores, True
            else:
                decision = "uncertain_no_strict_improvement"
        elif all(old-new > MARGIN for old,new in zip(best_scores,scores)):
            decision = "observed_improvement"
            best, best_scores = trial_id, scores
        elif all(new-old > MARGIN for old,new in zip(best_scores,scores)):
            decision = "target_regression"
        else:
            decision = "uncertain_no_strict_improvement"
        rows.append(dict(trial_id=trial_id, generated_score=scores[0], imported_score=scores[1],
                         decision=decision, best_before=before, best_after=best))
        if reached:
            if trial_id != "target":
                _fail("premature_target")
            break
    stop = ("target_reached" if reached else "budget_exhausted" if len(rows)==budget else "incomplete")
    return dict(budget=budget, rows=rows, best_id=best, stop_reason=stop, target_reached=reached)


def _verify_history(claimed, replayed):
    _record(claimed, HISTORY_FIELDS)
    if (type(claimed["budget"]) is not int or type(claimed["target_reached"]) is not bool
            or type(claimed["rows"]) is not list):
        _fail("history_mismatch")
    if len(claimed["rows"]) != len(replayed["rows"]):
        _fail("history_mismatch")
    for key in HISTORY_FIELDS - {"rows"}:
        if type(claimed[key]) is not type(replayed[key]) or claimed[key] != replayed[key]:
            _fail("history_mismatch")
    for actual, expected in zip(claimed["rows"], replayed["rows"]):
        _record(actual, ROW_FIELDS)
        for key in ROW_FIELDS:
            if key.endswith("_score"):
                if not _number(actual[key]) or abs(actual[key] - expected[key]) > 1e-9:
                    _fail("history_mismatch")
            elif type(actual[key]) is not str or actual[key] != expected[key]:
                _fail("history_mismatch")


def reduce_candidate_evidence(trials, claimed_history, *, run_id, blender_version,
                              reference_run_id, source_bytes, allowed_candidates,
                              measured, references, budget=4):
    """Normalize B history and C trials against independent parent observations.

    measured is a separately captured normalized trial mapping (same fields as
    each trial). Parent must derive actual bytes, lifecycle, measurements and
    hashes independently, not copy C's claims. No arbitrary inputs executed.
    Missing prefix evidence cannot verify success. Budget replay is not proof
    that Blender physically stopped early.
    """
    try:
        identity = _identity(run_id, blender_version, reference_run_id)
        if type(budget) is not int or not 1 <= budget <= 4:
            _fail("budget_invalid")
        if type(source_bytes) is not bytes or _sha(source_bytes) != SOURCE_SHA256:
            _fail("source_digest_mismatch")
        if trials is None:
            trials = []
        if type(trials) is not list or len(trials) > budget:
            _fail("trial_order_mismatch")
        allowed_candidates = {} if allowed_candidates is None else allowed_candidates
        measured = {} if measured is None else measured
        for mapping in (allowed_candidates, measured):
            if type(mapping) is not dict or not set(mapping) <= set(TRIALS[:budget]):
                _fail("trial_order_mismatch")
        for trial_id, allowed in allowed_candidates.items():
            expected, _ = _fixed_candidate(source_bytes, TRIALS.index(trial_id))
            if type(allowed) is not bytes or allowed != expected:
                _fail("fixed_candidate_mismatch")
        refs = {} if references is None else _reference_rows(references, identity)
        missing = []
        if set(refs) != set(REFERENCES):
            missing.append("reference_missing")
        verified_candidates = []
        for index, record in enumerate(trials):
            trial_id = TRIALS[index]
            if type(record) is not dict or record.get("trial_id") != trial_id:
                _fail("trial_order_mismatch")
            if trial_id not in allowed_candidates:
                missing.append("candidate_bytes_missing")
            allowed, _ = _fixed_candidate(source_bytes, index)
            if trial_id in allowed_candidates:
                allowed = allowed_candidates[trial_id]
            rows = _trial_rows(record, identity, index, source_bytes, allowed, refs)
            parent = measured.get(trial_id)
            if parent is None:
                missing.append("parent_measurement_missing")
            else:
                parent_rows = _trial_rows(parent, identity, index, source_bytes, allowed, refs)
                if parent != record:
                    _fail("parent_measurement_mismatch")
                if len(parent_rows) != 3:
                    missing.append("stage_missing")
            if len(rows) != 3:
                missing.append("stage_missing")
            else:
                verified_candidates.append(rows[1])
        if set(measured) - set(TRIALS[:len(trials)]):
            _fail("trial_order_mismatch")
        if claimed_history is None:
            missing.append("history_missing")
        if missing:
            # An incomplete trace must not carry a target/adoption claim.
            if claimed_history is not None:
                _record(claimed_history, HISTORY_FIELDS)
                if (type(claimed_history["budget"]) is not int or claimed_history["budget"] != budget
                        or type(claimed_history["rows"]) is not list
                        or len(claimed_history["rows"]) > len(trials)):
                    _fail("history_mismatch")
                if (claimed_history["target_reached"] is not False
                        or claimed_history["stop_reason"] == "target_reached"):
                    _fail("premature_target")
                best = "baseline"
                for index, row in enumerate(claimed_history["rows"]):
                    _record(row, ROW_FIELDS)
                    decision = row["decision"]
                    if decision == "observed_target_reached":
                        _fail("premature_target")
                    if (type(decision) is not str or decision not in (
                            "target_regression", "protected_part_regression", "observed_improvement",
                            "uncertain_no_strict_improvement")
                            or row["trial_id"] != TRIALS[index] or row["best_before"] != best
                            or any(not _number(row[k]) or row[k] < 0 for k in
                                   ("generated_score", "imported_score"))):
                        _fail("history_mismatch")
                    if decision == "observed_improvement":
                        best = TRIALS[index]
                    if row["best_after"] != best:
                        _fail("history_mismatch")
                if (claimed_history["best_id"] != best or claimed_history["stop_reason"] not in
                        ("incomplete", "budget_exhausted")
                        or (claimed_history["stop_reason"] == "budget_exhausted"
                            and len(claimed_history["rows"]) != budget)):
                    _fail("history_mismatch")
            return _summary("incomplete", missing, identity)
        replayed = _replay(refs["baseline"], refs["sphere_radius_changed"], verified_candidates, budget)
        _verify_history(claimed_history, replayed)
        if replayed["stop_reason"] == "incomplete":
            return _summary("incomplete", ["trial_prefix_incomplete"], identity, replayed)
        if replayed["target_reached"]:
            if tuple(x["decision"] for x in replayed["rows"]) != EXPECTED_DECISIONS:
                _fail("fixed_decision_mismatch")
            return _summary("verified_fixed_history", [], identity, replayed)
        return _summary("verified_budget_exhausted", [], identity, replayed)
    except ValueError as exc:
        return _summary("rejected", [str(exc)])
