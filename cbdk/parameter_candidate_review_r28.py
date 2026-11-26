"""R28 fixed candidate review: pure measurement evaluation, no execution.

The parent/D independently bind actual source, run, version and GLB evidence.
R27 measurement validation and GLB-022 bounded-review principles are reused;
GLB-022's unrelated sampled-distance metric/threshold is NOT reused.
"""
from __future__ import annotations

from .parameter_source_evidence_r27 import (
    CUBE, SPHERE, MEASUREMENT_FIELDS, _measurement,
)
from .glb_synthetic_adaptive import MAX_TRIALS

TRIAL_IDS = ("wrong_direction", "cross_part", "intermediate", "target")
PHASES = ("generated_mesh", "imported_glb_mesh")
MARGIN = 1e-5
SAFETY = {
    "auto_apply": False, "auto_adopt": False, "auto_approve": False,
    "authenticates_observations": False, "general_geometry_equivalence_verified": False,
    "optimal_value_verified": False, "source_executed": False,
}


def _checked_measurement(row):
    if type(row) is not dict or set(row) != MEASUREMENT_FIELDS:
        raise ValueError("measurement_invalid")
    _measurement(row)


def _scores(row, target):
    return {
        phase: max(abs(a - b) for a, b in zip(
            row[phase][SPHERE]["world_dimensions"],
            target[phase][SPHERE]["world_dimensions"]))
        for phase in PHASES
    }


def _summary(status, stop, budget, baseline_scores=None, history=None,
             best_id=None, best_scores=None, reasons=()):
    history = [] if history is None else history
    return {
        "case_id": "parameter_source_r28",
        "status": status, "stop_reason": stop, "reason_codes": list(reasons),
        "budget": budget, "validated_attempts": len(history),
        "margin": MARGIN, "baseline_scores": baseline_scores,
        "trials": history, "best_trial_id": best_id, "best_scores": best_scores,
        "observed_target_reached": status == "completed" and stop == "observed_target_reached",
        "safety": dict(SAFETY),
    }


def review_fixed_candidates(baseline, target, trials, *, budget=MAX_TRIALS):
    """Review ordered, already measured prefix, not a candidate generator.

    baseline/target: R27 MEASUREMENT_FIELDS dictionaries (actual GLB SHA,
    generated_mesh and imported_glb_mesh, exactly the fixed two part rows).
    trials: list of {trial_id, measurement} in fixed order, length <= budget.
    None or a missing suffix is incomplete; invalid/extra/out-of-order data
    is rejected. Scores are unrounded max absolute dimension differences.
    Parent/D must verify provenance and all stage/restoration evidence before
    treating even a completed review as valid. No caller-supplied best/status.
    """
    if type(budget) is not int or not 1 <= budget <= MAX_TRIALS:
        return _summary("rejected", "rejected", None, reasons=("invalid_budget",))
    if baseline is None or target is None or trials is None:
        return _summary("incomplete", "incomplete", budget, reasons=("measurement_missing",))
    try:
        _checked_measurement(baseline)
        _checked_measurement(target)
        base_scores = _scores(baseline, target)
        if (any(baseline[p][CUBE] != target[p][CUBE] for p in PHASES)
                or any(base_scores[p] <= MARGIN for p in PHASES)):
            raise ValueError("reference_mismatch")
        if type(trials) is not list or len(trials) > budget:
            raise ValueError("trial_count_invalid")
        # Validate the entire supplied prefix before making any claims.
        for index, row in enumerate(trials):
            if type(row) is not dict or set(row) != {"trial_id", "measurement"}:
                raise ValueError("trial_record_invalid")
            if type(row["trial_id"]) is not str or row["trial_id"] != TRIAL_IDS[index]:
                raise ValueError("trial_order_invalid")
            if row["measurement"] is None:
                if index != len(trials) - 1:
                    raise ValueError("trial_after_missing")
            else:
                _checked_measurement(row["measurement"])
    except ValueError as exc:
        return _summary("rejected", "rejected", budget, reasons=(str(exc),))

    best_id, best_scores, history = "baseline", base_scores, []
    for row in trials:
        trial_id, measurement = row["trial_id"], row["measurement"]
        if measurement is None:
            break
        scores = _scores(measurement, target)
        protected = {p: measurement[p][CUBE] == baseline[p][CUBE] for p in PHASES}
        exact_target = {p: measurement[p][SPHERE] == target[p][SPHERE] for p in PHASES}
        close = all(scores[p] <= MARGIN for p in PHASES)
        better = all(best_scores[p] - scores[p] > MARGIN for p in PHASES)
        worse = all(scores[p] - best_scores[p] > MARGIN for p in PHASES)
        previous_id = best_id
        if not all(protected.values()):
            decision = "protected_part_regression"
        elif close:
            # Dimensional equality alone, or an early apparent target, cannot
            # satisfy the fixed four-trial contract. Do not adopt either.
            if trial_id == "target" and all(exact_target.values()) and better:
                decision = "observed_target_reached"
            else:
                decision = "uncertain_no_strict_improvement"
        elif worse:
            decision = "target_regression"
        elif better:
            decision = "observed_improvement"
        else:
            decision = "uncertain_no_strict_improvement"
        accepted = decision in ("observed_improvement", "observed_target_reached")
        if accepted:
            best_id, best_scores = trial_id, scores
        history.append({
            "trial_id": trial_id, "decision": decision, "scores": scores,
            "protected_unchanged": protected, "target_measurement_match": exact_target,
            "accepted_as_measured_progress": accepted,
            "best_trial_before": previous_id, "best_trial_after": best_id,
        })
        if decision == "observed_target_reached":
            return _summary("completed", decision, budget, base_scores, history, best_id, best_scores)

    stop = "budget_exhausted" if len(history) == budget else "incomplete"
    return _summary(stop, stop, budget, base_scores, history, best_id, best_scores,
                    reasons=("measurement_missing",) if stop == "incomplete" else ())
