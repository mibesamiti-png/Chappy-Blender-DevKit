"""GLB-022 phase 2: bounded multi-candidate, cross-part regression guards.

All conditions are CBDK-authored synthetic fixtures, not user code. The
function consumes only GLB-020 aggregate-only reports; it never executes an
addon, reads raw 3D coordinates, or infers a useful real-world setting.
"""
from __future__ import annotations

import json
from pathlib import Path

from .glb_synthetic_iteration import _decision, _safe_rows, _score

BASELINE = "narrow"
CANDIDATES = ("narrow_placebo", "shifted", "identical")
CONTROLS = {
    "narrow": {"socket_opening_diameter": 0.78, "ball_shifted": False},
    "narrow_placebo": {"socket_opening_diameter": 0.78, "ball_shifted": True},
    "shifted": {"socket_opening_diameter": 1.70, "ball_shifted": True},
    "identical": {"socket_opening_diameter": 1.70, "ball_shifted": False},
}
MAX_ATTEMPTS = 3
OUTPUT_JSON = "synthetic_multi_iteration_history.json"
OUTPUT_MD = "synthetic_multi_iteration_history.md"
STOP_ZERO = "sampled_zero_without_other_part_regression"
STOP_BUDGET = "attempt_budget_exhausted"
EXPECTED_DECISIONS = (
    (False, "socket_not_improved"),
    (False, "unrelated_part_regression"),
    (True, "strict_sampled_socket_improvement_no_observed_regression"),
)
SCORE_KEYS = frozenset((
    "socket_sampled_affected_faces",
    "other_parts_sampled_affected_faces",
))
SAFETY = {
    "runs_user_addons": False,
    "executes_private_source": False,
    "changes_user_source_or_glbs": False,
    "auto_approves_real_change": False,
    "recommends_user_parameter_values": False,
    "proves_real_addon_causality": False,
    "proves_complete_surface_equivalence": False,
    "proves_part_identity_across_glbs": False,
}


def _validated_score(score):
    if (not isinstance(score, dict) or set(score) != SCORE_KEYS
            or type(score["socket_sampled_affected_faces"]) is not int
            or not 0 <= score["socket_sampled_affected_faces"] <= 96
            or type(score["other_parts_sampled_affected_faces"]) is not int
            or not 0 <= score["other_parts_sampled_affected_faces"] <= 56):
        raise ValueError("Invalid fixed synthetic sampled-face counts")
    return score


def build_multi_iteration_history(reports, *, attempt_budget=MAX_ATTEMPTS):
    """Replay exactly the first N allowlisted trials, never arbitrary IDs.

    A non-improving edit and an edit improving the socket but damaging the
    ball must be rejected. A successful synthetic restoration can be accepted.
    A lower budget stops safely with a still-defective baseline.
    """
    if type(attempt_budget) is not int or not 1 <= attempt_budget <= MAX_ATTEMPTS:
        raise ValueError("Synthetic trial budget must be an integer from 1 to 3")
    expected_ids = (BASELINE, *CANDIDATES[:attempt_budget])
    if (not isinstance(reports, dict) or set(reports) != set(expected_ids)):
        raise ValueError("Unexpected, missing or unallowlisted synthetic trial")
    scores = {
        name: _validated_score(_score(_safe_rows(reports[name])))
        for name in expected_ids
    }
    start = scores[BASELINE]
    if (start["socket_sampled_affected_faces"] <= 0
            or start["other_parts_sampled_affected_faces"] != 0):
        raise ValueError("Missing controlled synthetic socket defect")

    attempts = []
    current = BASELINE
    stop_reason = STOP_BUDGET
    for index, trial_id in enumerate(CANDIDATES[:attempt_budget]):
        before, after = scores[current], scores[trial_id]
        accepted, reason = _decision(before, after)
        if (accepted, reason) != EXPECTED_DECISIONS[index]:
            raise ValueError("Unexpected multi-candidate synthetic observation")
        next_id = trial_id if accepted else current
        attempts.append({
            "attempt_number": index + 1,
            "candidate_id": trial_id,
            "synthetic_controls": dict(CONTROLS[trial_id]),
            "accepted_baseline_before": current,
            "before_sampled": dict(before),
            "candidate_sampled": dict(after),
            "accepted": accepted,
            "decision": reason,
            "accepted_baseline_after": next_id,
            "user_parameter_inferred": False,
        })
        current = next_id
        final = scores[current]
        if (final["socket_sampled_affected_faces"] == 0
                and final["other_parts_sampled_affected_faces"] == 0):
            stop_reason = STOP_ZERO
            break
    expected_final = "identical" if attempt_budget == 3 else BASELINE
    expected_stop = STOP_ZERO if attempt_budget == 3 else STOP_BUDGET
    if current != expected_final or stop_reason != expected_stop:
        raise ValueError("Synthetic iteration did not follow bounded stop protocol")
    return {
        "kind": "cbdk_glb022_multi_candidate_synthetic_v1",
        "schema_version": 1,
        "status": "synthetic_test_only",
        "baseline": BASELINE,
        "max_attempts": MAX_ATTEMPTS,
        "attempt_budget": attempt_budget,
        "attempts_executed": len(attempts),
        "attempts": attempts,
        "accepted_candidate_id": current,
        "stop_reason": stop_reason,
        "final_observations": dict(scores[current]),
        "scoring_limits": {
            "metric": "glb020_sampled_medium_plus_high_faces",
            "real_addon_causality_proven": False,
            "complete_mesh_equivalence_proven": False,
        },
        "safety": dict(SAFETY),
    }


def render_multi_iteration_markdown(history):
    """Fail closed rather than render an injected record as trusted evidence."""
    if (not isinstance(history, dict)
            or set(history) != {
                "kind", "schema_version", "status", "baseline", "max_attempts",
                "attempt_budget", "attempts_executed", "attempts",
                "accepted_candidate_id", "stop_reason", "final_observations",
                "scoring_limits", "safety"
            }
            or history["kind"] != "cbdk_glb022_multi_candidate_synthetic_v1"
            or type(history["schema_version"]) is not int
            or history["schema_version"] != 1
            or history["status"] != "synthetic_test_only"
            or history["baseline"] != BASELINE
            or history["max_attempts"] != MAX_ATTEMPTS
            or history["safety"] != SAFETY
            or history["scoring_limits"] != {
                "metric": "glb020_sampled_medium_plus_high_faces",
                "real_addon_causality_proven": False,
                "complete_mesh_equivalence_proven": False,
            }):
        raise ValueError("Unsafe synthetic multi-candidate history")
    budget = history["attempt_budget"]
    if (type(budget) is not int or not 1 <= budget <= MAX_ATTEMPTS
            or type(history["attempts_executed"]) is not int
            or history["attempts_executed"] != budget
            or not isinstance(history["attempts"], list)
            or len(history["attempts"]) != budget):
        raise ValueError("Invalid multi-candidate iteration budget")
    current = BASELINE
    previous = None
    lines = [
        "# GLB-022 自作合成モデルの複数候補比較",
        "",
        "**実アドオンに設定値を適用しない実験専用です。** "
        "数値0.78/1.70はCBDKの合成モデルのみに適用します。",
        "",
        "| 試行 | 設定候補 | ソケット黄＋赤（前→後） | 他部品（前→後） | 判定 |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for idx, (record, candidate) in enumerate(zip(history["attempts"],
                                                    CANDIDATES), start=1):
        if (not isinstance(record, dict) or set(record) != {
                "attempt_number", "candidate_id", "synthetic_controls",
                "accepted_baseline_before", "before_sampled",
                "candidate_sampled", "accepted", "decision",
                "accepted_baseline_after", "user_parameter_inferred",
            }
            or type(record["attempt_number"]) is not int
            or record["attempt_number"] != idx
            or record["candidate_id"] != candidate
            or record["synthetic_controls"] != CONTROLS[candidate]
            or record["accepted_baseline_before"] != current
            or record["user_parameter_inferred"] is not False):
            raise ValueError("Invalid or forged multi-candidate trial")
        before = _validated_score(record["before_sampled"])
        after = _validated_score(record["candidate_sampled"])
        if previous is None:
            if (before["socket_sampled_affected_faces"] < 1
                    or before["other_parts_sampled_affected_faces"] != 0):
                raise ValueError("Invalid synthetic initial baseline")
        elif before != previous:
            raise ValueError("Rejected trial corrupted accepted baseline")
        accepted, reason = _decision(before, after)
        if ((accepted, reason) != EXPECTED_DECISIONS[idx - 1]
                or record["accepted"] is not accepted
                or record["decision"] != reason):
            raise ValueError("Forged cross-part regression decision")
        current = candidate if accepted else current
        if record["accepted_baseline_after"] != current:
            raise ValueError("Unexpected accepted baseline transition")
        previous = after if accepted else before
        decision = ("採用（合成モデル限定）" if accepted else
                    "棄却（他部品が悪化）" if idx == 2 else
                    "棄却（ソケット改善なし）")
        lines.append(
            f'| {idx} | \`{candidate}\` | '
            f'{before["socket_sampled_affected_faces"]}→'
            f'{after["socket_sampled_affected_faces"]} | '
            f'{before["other_parts_sampled_affected_faces"]}→'
            f'{after["other_parts_sampled_affected_faces"]} | {decision} |'
        )
    expected_final = "identical" if budget == 3 else BASELINE
    expected_stop = STOP_ZERO if budget == 3 else STOP_BUDGET
    if (history["accepted_candidate_id"] != expected_final
            or history["stop_reason"] != expected_stop
            or history["final_observations"] != previous
            or (budget == 3 and previous != {
                "socket_sampled_affected_faces": 0,
                "other_parts_sampled_affected_faces": 0,
            })):
        raise ValueError("Unverified synthetic final state or stopping reason")
    lines.extend([
        "",
        f"**停止理由**：\`{expected_stop}\`。試行上限 {budget} 回。",
        "**注意**：黄/赤面の数による判断であり、小穴・内部空間・実ユーザーの"
        "アドオン設定の原因・最適値・真の同一性を証明しません。",
        "",
    ])
    return "\n".join(lines)


def write_multi_iteration_history(history, directory):
    output = Path(directory)
    if not output.is_dir() or output.is_symlink():
        raise ValueError("Private synthetic output folder must exist")
    text = render_multi_iteration_markdown(history)
    files = (output / "synthetic_multi_iteration_history.json",
             output / "synthetic_multi_iteration_history.md")
    if any(p.exists() or p.is_symlink() for p in files):
        raise FileExistsError("Synthetic reports must never overwrite")
    serialized = json.dumps(history, ensure_ascii=False, allow_nan=False,
                            indent=2) + "\n"
    with files[0].open("x", encoding="utf-8") as handle:
        handle.write(serialized)
    with files[1].open("x", encoding="utf-8") as handle:
        handle.write(text)
    return files
