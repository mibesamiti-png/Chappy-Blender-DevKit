"""GLB-022 phase 3: bounded observed-distance progress, CBDK SYNTHETIC ONLY.

Global directional sampled maxima provide a finer numerical signal than
low/medium/high face counts. They do NOT measure every surface point, do not
localize a difference to one part, and must never rank arbitrary user GLBs.
A strict other-part classification guard prevents accepting a moved ball.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .glb_synthetic_iteration import _score, _safe_rows

BASELINE = "narrow"
CANDIDATES = ("narrow_mid_shifted", "narrow_mid", "identical")
CONTROLS = {
    "narrow": (0.78, False),
    "narrow_mid_shifted": (1.24, True),
    "narrow_mid": (1.24, False),
    "identical": (1.70, False),
}
MAX_ATTEMPTS = 3
MIN_DELTA = 0.000001
OUTPUT_JSON = "synthetic_progress_history.json"
OUTPUT_MD = "synthetic_progress_history.md"
SAFETY = {
    "runs_user_addons": False,
    "reads_private_user_glbs": False,
    "executes_private_source": False,
    "edits_user_source_or_glbs": False,
    "recommends_real_parameter_values": False,
    "proves_real_addon_causality": False,
    "proves_complete_surface_equivalence": False,
    "proves_part_identity_across_glbs": False,
}


def _metric(report):
    """Read only validated aggregate directional maxima, not any raw geometry."""
    _safe_rows(report)
    if not isinstance(report, dict):
        raise ValueError("Invalid GLB-020 synthetic review")
    directions = ("reference_sampled_max", "candidate_sampled_max")
    vals = []
    for key in directions:
        x = report.get(key)
        if type(x) not in (float, int) or not math.isfinite(x) or not 0 <= x <= 1e5:
            raise ValueError("Invalid directional sampled surface maximum")
        vals.append(float(x))
    thresholds = report.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("Missing synthetic coordinate scale")
    scale = thresholds.get("combined_aabb_diagonal")
    if (type(scale) not in (float, int) or not math.isfinite(scale)
            or not 0 < scale <= 1e6):
        raise ValueError("Invalid synthetic AABB scale")
    return {
        "sampled_max_distance": round(max(vals), 7),
        "combined_aabb_diagonal": round(float(scale), 7),
        **_score(_safe_rows(report)),
    }


def _decision(before, after):
    """Accept only meaningful numeric progress and no sampled part regressions."""
    if after["other_parts_sampled_affected_faces"] > before["other_parts_sampled_affected_faces"]:
        return False, "other_part_regression"
    if after["socket_sampled_affected_faces"] > before["socket_sampled_affected_faces"]:
        return False, "socket_classification_regression"
    if (before["sampled_max_distance"] - after["sampled_max_distance"]
            <= MIN_DELTA):
        return False, "no_meaningful_sampled_max_improvement"
    return True, "strict_sampled_max_improvement_without_observed_regression"


def build_synthetic_progress(reports, *, attempt_budget=MAX_ATTEMPTS):
    if type(attempt_budget) is not int or not 1 <= attempt_budget <= MAX_ATTEMPTS:
        raise ValueError("Allowlisted attempt budget must be 1, 2 or 3")
    expected = (BASELINE, *CANDIDATES[:attempt_budget])
    if not isinstance(reports, dict) or set(reports) != set(expected):
        raise ValueError("Unknown or missing synthetic progress condition")
    scores = {k: _metric(reports[k]) for k in expected}
    starting = scores[BASELINE]
    if (starting["socket_sampled_affected_faces"] < 1
            or starting["other_parts_sampled_affected_faces"] != 0
            or starting["sampled_max_distance"] <= MIN_DELTA):
        raise ValueError("Expected measurable CBDK synthetic socket baseline defect")
    # The unshifted candidate fixture holds the entire scene scale constant.
    # The shifted trial is never used as an accepted metric baseline.
    for name in ("narrow_mid", "identical"):
        if name in scores and (scores[name]["combined_aabb_diagonal"]
                              != starting["combined_aabb_diagonal"]):
            raise ValueError("Different synthetic coordinate scale")
    if ("narrow_mid" in scores and
            not (MIN_DELTA < scores["narrow_mid"]["sampled_max_distance"]
                 < starting["sampled_max_distance"] - MIN_DELTA)):
        raise ValueError("Intermediate fixture has no measurable strict progress")
    if "identical" in scores and (scores["identical"]["sampled_max_distance"] > MIN_DELTA
                                 or scores["identical"]["socket_sampled_affected_faces"]
                                 or scores["identical"]["other_parts_sampled_affected_faces"]):
        raise ValueError("Restored fixture must have sampled zero observations")

    steps = []
    current = BASELINE
    for idx, candidate in enumerate(CANDIDATES[:attempt_budget], start=1):
        before, after = scores[current], scores[candidate]
        accepted, reason = _decision(before, after)
        should_accept = (idx != 1)
        if accepted is not should_accept:
            raise ValueError("Controlled synthetic candidate violated acceptance expectation")
        if idx == 1 and reason != "other_part_regression":
            raise ValueError("Moved synthetic ball must fail the cross-part regression gate")
        step = {
            "attempt_number": idx,
            "trial_id": candidate,
            "controls": {
                "synthetic_socket_diameter": CONTROLS[candidate][0],
                "synthetic_ball_shifted": CONTROLS[candidate][1],
            },
            "baseline_before": current,
            "sampled_max_before": before["sampled_max_distance"],
            "sampled_max_candidate": after["sampled_max_distance"],
            "socket_faces_before": before["socket_sampled_affected_faces"],
            "socket_faces_candidate": after["socket_sampled_affected_faces"],
            "other_faces_before": before["other_parts_sampled_affected_faces"],
            "other_faces_candidate": after["other_parts_sampled_affected_faces"],
            "accepted": accepted,
            "decision": reason,
            "baseline_after": candidate if accepted else current,
        }
        steps.append(step)
        if accepted:
            current = candidate
        if (scores[current]["sampled_max_distance"] <= MIN_DELTA
                and scores[current]["socket_sampled_affected_faces"] == 0
                and scores[current]["other_parts_sampled_affected_faces"] == 0):
            break
    if len(steps) != attempt_budget:
        raise ValueError("Unexpected synthetic early stop or budget inconsistency")
    expected_final = ("identical" if attempt_budget == 3 else
                      "narrow_mid" if attempt_budget == 2 else BASELINE)
    if current != expected_final:
        raise ValueError("Unsafe synthetic accepted baseline")
    stop_reason = ("observed_sampled_zero" if current == "identical"
                   else "attempt_budget_exhausted")
    return {
        "kind": "cbdk_glb022_synthetic_progress_v1",
        "schema_version": 1,
        "status": "synthetic_test_only",
        "metric": "global_bidirectional_sampled_max_distance_input_units",
        "metric_is_part_specific": False,
        "metric_is_exact_hausdorff": False,
        "max_attempts": MAX_ATTEMPTS,
        "attempt_budget": attempt_budget,
        "attempts": steps,
        "accepted_trial_id": current,
        "stop_reason": stop_reason,
        "final_sampled_max": scores[current]["sampled_max_distance"],
        "safety": dict(SAFETY),
    }


def render_synthetic_progress(history):
    if (not isinstance(history, dict)
            or set(history) != {
                "kind", "schema_version", "status", "metric",
                "metric_is_part_specific", "metric_is_exact_hausdorff",
                "max_attempts", "attempt_budget", "attempts",
                "accepted_trial_id", "stop_reason", "final_sampled_max", "safety"
            }
            or history["kind"] != "cbdk_glb022_synthetic_progress_v1"
            or type(history["schema_version"]) is not int or history["schema_version"] != 1
            or history["status"] != "synthetic_test_only"
            or history["metric"] != "global_bidirectional_sampled_max_distance_input_units"
            or history["metric_is_part_specific"] is not False
            or history["metric_is_exact_hausdorff"] is not False
            or history["max_attempts"] != MAX_ATTEMPTS
            or history["safety"] != SAFETY):
        raise ValueError("Forged or unsupported synthetic progress history")
    budget = history["attempt_budget"]
    if (type(budget) is not int or not 1 <= budget <= MAX_ATTEMPTS
            or not isinstance(history["attempts"], list)
            or len(history["attempts"]) != budget):
        raise ValueError("Invalid synthetic attempt budget")
    lines = [
        "# GLB-022 CBDK合成モデルの段階的改善",
        "",
        "**合成モデル専用・実アドオンの修正値ではありません。** "
        "0.78 / 1.24 / 1.70はテスト専用の直径です。",
        "",
        "| 試行 | 合成条件 | 最大サンプル距離（前→候補） | 他部品の黄赤（前→候補） | 判定 |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    current = BASELINE
    last_max = None
    for index, (row, name) in enumerate(zip(history["attempts"], CANDIDATES), 1):
        if (not isinstance(row, dict) or set(row) != {
                "attempt_number", "trial_id", "controls", "baseline_before",
                "sampled_max_before", "sampled_max_candidate",
                "socket_faces_before", "socket_faces_candidate",
                "other_faces_before", "other_faces_candidate", "accepted",
                "decision", "baseline_after"
            }
            or type(row["attempt_number"]) is not int or row["attempt_number"] != index
            or row["trial_id"] != name
            or row["controls"] != {
                "synthetic_socket_diameter": CONTROLS[name][0],
                "synthetic_ball_shifted": CONTROLS[name][1],
            }
            or row["baseline_before"] != current
            or any(type(row[k]) not in (int, float) or
                   not math.isfinite(row[k]) or not 0 <= row[k] <= 1e5
                   for k in ("sampled_max_before", "sampled_max_candidate"))
            or any(type(row[k]) is not int or not 0 <= row[k] <= upper for k, upper in (
                ("socket_faces_before", 96), ("socket_faces_candidate", 96),
                ("other_faces_before", 56), ("other_faces_candidate", 56)
            ))):
            raise ValueError("Malformed synthetic progress step")
        if last_max is not None and row["sampled_max_before"] != last_max:
            raise ValueError("Rejected trial unexpectedly replaced accepted maximum")
        before = {
            "sampled_max_distance": row["sampled_max_before"],
            "socket_sampled_affected_faces": row["socket_faces_before"],
            "other_parts_sampled_affected_faces": row["other_faces_before"],
        }
        after = {
            "sampled_max_distance": row["sampled_max_candidate"],
            "socket_sampled_affected_faces": row["socket_faces_candidate"],
            "other_parts_sampled_affected_faces": row["other_faces_candidate"],
        }
        accepted, reason = _decision(before, after)
        if (row["accepted"] is not accepted or
                row["decision"] != reason or accepted is not (index != 1)):
            raise ValueError("Forged sampled improvement or regression decision")
        current = name if accepted else current
        if row["baseline_after"] != current:
            raise ValueError("Invalid accepted baseline transition")
        last_max = after["sampled_max_distance"] if accepted else before["sampled_max_distance"]
        verdict = ("棄却（他部品悪化）" if index == 1
                   else "採用（合成実験のみ・段階的改善）")
        lines.append(
            f'| {index} | \`{name}\` | '
            f'{before["sampled_max_distance"]:.7f}→{after["sampled_max_distance"]:.7f} | '
            f'{before["other_parts_sampled_affected_faces"]}→'
            f'{after["other_parts_sampled_affected_faces"]} | {verdict} |'
        )
    expected_final = "identical" if budget == 3 else "narrow_mid" if budget == 2 else BASELINE
    expected_stop = ("observed_sampled_zero" if budget == 3 else "attempt_budget_exhausted")
    if (current != expected_final or history["accepted_trial_id"] != expected_final
            or history["stop_reason"] != expected_stop
            or type(history["final_sampled_max"]) not in (float, int)
            or not math.isfinite(history["final_sampled_max"])
            or history["final_sampled_max"] != last_max
            or (budget == 3 and history["final_sampled_max"] > MIN_DELTA)):
        raise ValueError("Unsafe final synthetic progress claim")
    lines.extend([
        "",
        f"**停止理由**：\`{expected_stop}\`。観測した最大サンプル距離は入力座標単位。",
        "**注意**：距離は2方向の全体最大値で、部品別距離でも、厳密な"
        "Hausdorff距離でもありません。差分0は全形状一致の証明ではありません。",
        "",
    ])
    return "\n".join(lines)


def write_synthetic_progress(history, directory):
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Expected an existing private synthetic folder")
    md = render_synthetic_progress(history)
    p_json, p_md = root / OUTPUT_JSON, root / OUTPUT_MD
    if any(p.exists() or p.is_symlink() for p in (p_json, p_md)):
        raise FileExistsError("Synthetic progress history cannot be overwritten")
    encoded = json.dumps(history, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with p_json.open("x", encoding="utf-8") as f:
        f.write(encoded)
    with p_md.open("x", encoding="utf-8") as f:
        f.write(md)
    return p_json, p_md
