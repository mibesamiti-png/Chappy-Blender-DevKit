"""Conservative one-parameter direction decision for CBDK-owned GLB experiments.

Scores come from trusted identical-topology synthetic meshes. No optimization,
source execution, automatic edits, or inference about arbitrary user addons.
"""
from __future__ import annotations

import math

MEASUREMENT_MARGIN = 1e-5


class DirectionEvidenceError(ValueError):
    pass


def _score(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DirectionEvidenceError(label + " must be a numeric distance")
    try:
        score = float(value)
    except (OverflowError, ValueError) as exc:
        raise DirectionEvidenceError(label + " is unrepresentable") from exc
    if not math.isfinite(score) or score < 0:
        raise DirectionEvidenceError(label + " must be finite and nonnegative")
    return score


def choose_review_direction(
    baseline_error: float, increase_error: float, decrease_error: float,
    *, margin: float = MEASUREMENT_MARGIN,
) -> dict:
    """Return a *review-only* direction, or inconclusive on ambiguous evidence.

    The margin must be strictly positive. Error scores should be measured
    against the SAME trusted reference using the SAME distance metric.
    """
    base = _score(baseline_error, "baseline_error")
    up = _score(increase_error, "increase_error")
    down = _score(decrease_error, "decrease_error")
    tolerance = _score(margin, "margin")
    if tolerance <= 0:
        raise DirectionEvidenceError("margin must be positive")

    up_better = up + tolerance < base and up + tolerance < down
    down_better = down + tolerance < base and down + tolerance < up
    if up_better:
        direction = "increase"
        winner = up
    elif down_better:
        direction = "decrease"
        winner = down
    else:
        direction = "inconclusive"
        winner = min(base, up, down)

    return {
        "decision": direction,
        "reference_error": {
            "baseline": base, "increase_probe": up, "decrease_probe": down,
        },
        "best_observed_error": winner,
        "absolute_error_reduction_from_baseline": (
            round(base - winner, 7) if direction != "inconclusive" else 0.0
        ),
        "margin": tolerance,
        "status": "review_only_synthetic_fixture",
        "suggested_numeric_value": None,
        "auto_apply": False,
        "verified_for_arbitrary_user_addons": False,
    }
