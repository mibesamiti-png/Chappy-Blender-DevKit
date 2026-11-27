"""R29 fixed rotary panel read-only projection.

Consumes summaries from current RUNS and checks their agreement with the
existing serialized result. Never imports Blender/providers or re-evaluates
geometry. Display flags are not operator authorization.
"""
from __future__ import annotations

import json
import math

from .joint_integration import POLICIES, number

FIXTURE_ID = "joint_rotary_fixture_v1"
PART_IDS = ("rotary_outer", "rotary_axle")
RECIPE_LABEL = "固定人工回転関節"
TRIAL_IDS = ("negative_control", "midpoint", "declared_target")
DECISIONS = frozenset(("protected_part_regression", "axial_dimension_regression",
                       "target_reached", "observed_improvement", "regression", "uncertain"))
ACCEPTED = frozenset(("target_reached", "observed_improvement"))
STATUSES = frozenset(("IDLE", "RUNNING", "BLOCKED", "READY", "NO_CANDIDATE",
                      "FAILED", "CANCELLED", "REJECTED", "ADOPTED_DIMENSION_ONLY", "RESTORED"))
ACTIONS = ("RUN", "RETRY", "CANCEL", "REJECT", "ADOPT", "RESTORE")
REASONS = frozenset(("", "provider_configuration_failed", "local_providers_missing",
    "local_provider_hash_mismatch", "provider_paths_changed_restart_required",
    "external_provider_already_loaded", "external_geometry_already_loaded",
    "provider_size", "provider_path", "object_mode_required", "synthetic_origin_required",
    "synthetic_unit_scale_required", "numeric_constraints_unsatisfied", "face_budget_exceeded",
    "gl_unknown_or_intersecting", "cleanup_or_source_changed", "restoration_blocked",
    "cancelled_between_trials", "cancellation_requested", "context_scene_changed",
    "history_changed_rerun_required", "provider_or_geometry_failure", "stale_inputs",
    "no_current_candidate", "rejected_candidate", "fresh_measurement_changed",
    "rna_readback_mismatch", "post_write_changed", "rollback_failed",
    "injected_generation_failure", "injected_boolean_failure", "injected_interruption",
    "dimension_invalid", "policy_invalid", "measurement_invalid", "parts_missing",
    "dimensions_invalid", "protected_digest_invalid", "closed_flag_invalid",
    "gl_missing", "geometry_unknown_or_intersecting", "geometry_not_closed", "score_invalid"))
ROW_FIELDS = {"id", "diameter", "decision", "score", "accepted_for_review"}
RESULT_FIELDS = {"original", "target", "policy", "signature", "baseline", "rows", "best"}
MAX_RESULT_CHARS = 1024 * 1024


def _unique_object(pairs):
    data = {}
    for k, v in pairs:
        if k in data:
            raise ValueError("duplicate_json_key")
        data[k] = v
    return data


def _reject_constant(_):
    raise ValueError("nonfinite_json")


def _digest(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _summary(row):
    if type(row) is not dict or set(row) != ROW_FIELDS:
        raise ValueError("candidate_unavailable")
    if (type(row["id"]) is not str or row["id"] not in TRIAL_IDS
            or type(row["decision"]) is not str or row["decision"] not in DECISIONS
            or type(row["accepted_for_review"]) is not bool
            or row["accepted_for_review"] != (row["decision"] in ACCEPTED)):
        raise ValueError("candidate_unavailable")
    diameter = row["diameter"]
    score = row["score"]
    if (type(diameter) not in (int, float) or not 3.6 <= diameter <= 10
            or type(score) not in (int, float) or not 0 <= score <= 100
            or not math.isfinite(score)):
        raise ValueError("candidate_unavailable")
    return dict(id=row["id"], diameter=number(diameter), decision=row["decision"],
                score=float(score), accepted_for_review=row["accepted_for_review"])


def _rows(rows):
    if type(rows) is not list or len(rows) > len(TRIAL_IDS):
        raise ValueError("candidate_unavailable")
    out = [_summary(row) for row in rows]
    if tuple(row["id"] for row in out) != TRIAL_IDS[:len(out)]:
        raise ValueError("candidate_unavailable")
    if any(row["decision"] == "target_reached" for row in out[:-1]):
        raise ValueError("candidate_unavailable")
    return out


def _result_rows(result_json):
    if type(result_json) is not str or not 0 < len(result_json) <= MAX_RESULT_CHARS:
        raise ValueError("result_unavailable")
    data = json.loads(result_json, object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)
    if type(data) is not dict or set(data) != RESULT_FIELDS:
        raise ValueError("result_unavailable")
    if (number(data["original"]) != 5.0 or number(data["target"]) != 4.0
            or type(data["policy"]) is not str or data["policy"] not in POLICIES
            or not _digest(data["signature"])
            or type(data["baseline"]) is not dict
            or type(data["rows"]) is not list or len(data["rows"]) > 3):
        raise ValueError("result_unavailable")
    summaries = []
    for row in data["rows"]:
        if type(row) is not dict or set(row) != {"id", "diameter", "measurement", "review"}:
            raise ValueError("result_unavailable")
        review = row["review"]
        if (type(row["measurement"]) is not dict or type(review) is not dict
                or set(review) != {"decision", "score", "accepted_for_review", "auto_apply",
                                   "approved", "printable", "continuous_collision_checked"}
                or any(review[k] is not False for k in
                       ("auto_apply", "approved", "printable", "continuous_collision_checked"))):
            raise ValueError("result_unavailable")
        summaries.append(dict(id=row["id"], diameter=row["diameter"],
                              decision=review["decision"], score=review["score"],
                              accepted_for_review=review["accepted_for_review"]))
    rows = _rows(summaries)
    # The existing producer emits a complete fixed sequence, or stops at a
    # target, or emits no rows for LOCKED. Check completeness, not scores.
    if data["policy"] == "LOCKED":
        if rows:
            raise ValueError("result_unavailable")
    elif not rows or (len(rows) < 3 and rows[-1]["decision"] != "target_reached"):
        raise ValueError("result_unavailable")
    accepted = [i for i, row in enumerate(rows) if row["accepted_for_review"]]
    best = data["best"]
    if accepted:
        if type(best) is not int or best != accepted[-1]:
            raise ValueError("result_unavailable")
    elif best is not None:
        raise ValueError("result_unavailable")
    return rows, best


def project_joint_panel(status, reason, result_json, current_rows, *,
                        current_inputs_match, selected_index=0):
    """Return display-only fixed fixture dict.

    current_rows is a list of {id, diameter, decision, score, accepted_for_review}
    extracted by the caller from current scene RUNS, or None if absent.
    current_inputs_match must be the adapter's actual bool for the full current
    inputs/scene/provider/history guard and fixed fixture. Never derive it from
    saved result_json. selected_index is the current RNA candidate index.
    Only existing operators may authorize an action, including restoration.
    """
    known = type(status) is str and status in STATUSES
    known_reason = type(reason) is str and reason in REASONS
    view = {
        "fixture_id": FIXTURE_ID, "part_ids": list(PART_IDS), "recipe_label": RECIPE_LABEL,
        "status": status if known else "UNAVAILABLE",
        "reason": reason if known_reason else "reason_unavailable",
        "availability": "unavailable", "candidates": [], "selected_index": None,
        "actions": dict.fromkeys(ACTIONS, False),
    }
    actions = view["actions"]
    # Busy and blocked override every candidate, reason and freshness input.
    if known and status == "BLOCKED":
        view["reason"] = "restoration_blocked"
        return view
    if known and status == "RUNNING":
        actions["CANCEL"] = True
        return view
    if not known or not known_reason or type(current_inputs_match) is not bool:
        return view
    if status in ("READY", "NO_CANDIDATE"):
        # Stale/missing/contradictory history cannot authorize adoption.
        actions["RETRY"] = True
        actions["REJECT"] = True
        actions["RESTORE"] = True
        if not current_inputs_match:
            view["reason"] = "stale_inputs"
            return view
        try:
            saved, best = _result_rows(result_json)
            current = _rows(current_rows)
            if (saved != current or (best is not None) != (status == "READY")
                    or type(selected_index) is not int
                    or not 0 <= selected_index < 3):
                raise ValueError("candidate_unavailable")
        except (ValueError, TypeError, OverflowError, RecursionError):
            view["reason"] = "candidate_unavailable"
            return view
        view["availability"] = "available"
        view["candidates"] = current
        if selected_index < len(current):
            view["selected_index"] = selected_index
            actions["ADOPT"] = status == "READY" and current[selected_index]["accepted_for_review"]
        return view
    # Stale serialized results are never candidates outside READY/NO_CANDIDATE.
    view["availability"] = "available"
    if status in ("FAILED", "CANCELLED", "REJECTED"):
        actions["RETRY"] = True
        actions["RESTORE"] = True
    elif status == "ADOPTED_DIMENSION_ONLY":
        actions["RESTORE"] = True
    elif status in ("IDLE", "RESTORED"):
        actions["RUN"] = True
    return view
