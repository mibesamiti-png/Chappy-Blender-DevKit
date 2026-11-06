"""GLB-022 phase 5: feedback-driven bounded synthetic socket search.

Only CBDK-owned synthetic meshes, with a deliberately fixed target score and
known original reference endpoint. No arbitrary addon runs, parameter
recommendations, or guarantees of complete mesh equivalence.
"""
from __future__ import annotations

import json
from pathlib import Path

from .glb_synthetic_progress import MIN_DELTA, _decision, _metric

LOW_CENTI = 78
HIGH_CENTI = 170
MAX_TRIALS = 4
TARGET_SAMPLED_MAX = 0.12   # test-only scene-input units, NOT engineering tolerance
KIND = "cbdk_glb022_adaptive_synthetic_v1"
SAFETY = {
    "only_cbdk_owned_synthetic_generator": True,
    "user_addon_executed": False,
    "private_glb_loaded": False,
    "source_modified": False,
    "auto_applies_user_property": False,
    "recommends_real_joint_diameter": False,
    "exact_hausdorff_proven": False,
    "complete_geometry_equivalence_proven": False,
    "true_part_identity_proven": False,
}


def trial_id(centi: int) -> str:
    if type(centi) is not int or not LOW_CENTI < centi <= HIGH_CENTI:
        raise ValueError("Out-of-range synthetic test diameter")
    return f"adaptive_{centi:03d}"


def next_candidate(failed_lower: int, feasible_upper: int) -> int | None:
    """Compute a new midpoint of the observed fail/feasible bracket."""
    if (type(failed_lower) is not int or type(feasible_upper) is not int
            or not LOW_CENTI <= failed_lower < feasible_upper <= HIGH_CENTI):
        raise ValueError("Unsafe adaptive search bracket")
    if feasible_upper - failed_lower <= 1:
        return None
    return (failed_lower + feasible_upper) // 2


def _replay(baseline: dict, trials: dict, *, budget=MAX_TRIALS) -> dict:
    if type(budget) is not int or not 1 <= budget <= MAX_TRIALS:
        raise ValueError("Allowed synthetic search budget is 1..4")
    if not isinstance(trials, dict) or len(trials) > budget:
        raise ValueError("Unknown or excessive synthetic results")
    initial = _metric(baseline)
    if (initial["socket_sampled_affected_faces"] < 1
            or initial["other_parts_sampled_affected_faces"] != 0
            or initial["sampled_max_distance"] <= TARGET_SAMPLED_MAX):
        raise ValueError("Expected deliberately faulty baseline outside target")
    lo, hi = LOW_CENTI, HIGH_CENTI
    current_best = initial
    current_best_id = "narrow"
    measured_feasible = None
    steps = []
    for index, (key, report) in enumerate(trials.items(), start=1):
        midpoint = next_candidate(lo, hi)
        if midpoint is None or key != trial_id(midpoint):
            raise ValueError("Trial ID/order does not follow measured adaptive bracket")
        metric = _metric(report)
        if metric["combined_aabb_diagonal"] != initial["combined_aabb_diagonal"]:
            raise ValueError("Synthetic part comparison changed scene scale")
        if metric["other_parts_sampled_affected_faces"] != 0:
            raise ValueError("Synthetic socket-only trial regressed another part")
        improved, why = _decision(current_best, metric)
        if improved:
            current_best = metric
            current_best_id = key
        meets = (metric["sampled_max_distance"] <= TARGET_SAMPLED_MAX
                 and metric["other_parts_sampled_affected_faces"] == 0)
        old_lo, old_hi = lo, hi
        if meets:
            hi = midpoint
            measured_feasible = key
        else:
            lo = midpoint
        steps.append({
            "attempt": index,
            "trial_id": key,
            "generated_socket_diameter": midpoint / 100,
            "bracket_before": [old_lo / 100, old_hi / 100],
            "bracket_after": [lo / 100, hi / 100],
            "sampled_max": metric["sampled_max_distance"],
            "socket_affected_faces": metric["socket_sampled_affected_faces"],
            "other_affected_faces": metric["other_parts_sampled_affected_faces"],
            "target_met": meets,
            "accepted_as_measured_progress": improved,
            "progress_reason": why,
            "best_observed_trial_after": current_best_id,
            "best_feasible_trial_after": measured_feasible,
        })
    if len(steps) != len(trials):
        raise ValueError("Unexpected synthetic search step count")
    status = ("target_feasible_in_sampled_test"
              if measured_feasible else "no_measured_feasible_candidate")
    stop = ("attempt_budget_exhausted" if len(steps) == budget
            else "incomplete_trace")
    if next_candidate(lo, hi) is None:
        stop = "centi_unit_bracket_converged"
    return {
        "kind": KIND,
        "schema_version": 1,
        "status": "synthetic_test_only",
        "target_sampled_max": TARGET_SAMPLED_MAX,
        "target_is_real_tolerance": False,
        "max_trials": MAX_TRIALS,
        "attempt_budget": budget,
        "attempts_executed": len(steps),
        "steps": steps,
        "initial_bracket": [LOW_CENTI / 100, HIGH_CENTI / 100],
        "initial_sampled_max": initial["sampled_max_distance"],
        "initial_socket_affected_faces": initial["socket_sampled_affected_faces"],
        "final_bracket": [lo / 100, hi / 100],
        "best_observed_trial_id": current_best_id,
        "measured_feasible_trial_id": measured_feasible,
        "sampled_target_status": status,
        "stop_reason": stop,
        "metric": "global_bidirectional_sampled_max_not_exact_hausdorff",
        "safety": dict(SAFETY),
    }


def build_adaptive_history(baseline: dict, trials: dict, *, budget=MAX_TRIALS) -> dict:
    """Only complete budgeted traces may be published as a finished CI run.

    Shorter traces are allowed when the test explicitly uses a lower budget.
    """
    if not isinstance(trials, dict) or len(trials) != budget:
        raise ValueError("Adaptive history requires exactly the budgeted trials")
    output = _replay(baseline, trials, budget=budget)
    if output["stop_reason"] != "attempt_budget_exhausted":
        raise ValueError("Adaptive trace unexpectedly stopped before budget")
    return output


def render_adaptive_history(history: dict) -> str:
    """Validate the generated trace strictly; no arbitrary labels in Markdown."""
    if (not isinstance(history, dict)
            or set(history) != {
                "kind", "schema_version", "status", "target_sampled_max",
                "target_is_real_tolerance", "max_trials", "attempt_budget",
                "attempts_executed", "steps", "initial_bracket", "final_bracket",
                "initial_sampled_max", "initial_socket_affected_faces",
                "best_observed_trial_id", "measured_feasible_trial_id",
                "sampled_target_status", "stop_reason", "metric", "safety",
            }
            or history["kind"] != KIND
            or history["schema_version"] != 1
            or history["status"] != "synthetic_test_only"
            or history["target_sampled_max"] != TARGET_SAMPLED_MAX
            or history["target_is_real_tolerance"] is not False
            or history["max_trials"] != MAX_TRIALS
            or history["metric"] !=
            "global_bidirectional_sampled_max_not_exact_hausdorff"
            or history["safety"] != SAFETY):
        raise ValueError("Unsafe adaptive history")
    budget = history["attempt_budget"]
    if (type(budget) is not int or not 1 <= budget <= MAX_TRIALS
            or type(history["attempts_executed"]) is not int
            or history["attempts_executed"] != budget
            or not isinstance(history["steps"], list)
            or len(history["steps"]) != budget):
        raise ValueError("Invalid adaptive history budget")
    initial_max = history["initial_sampled_max"]
    initial_faces = history["initial_socket_affected_faces"]
    if (type(initial_max) not in (int, float) or not TARGET_SAMPLED_MAX < initial_max <= 1e5
            or type(initial_faces) is not int or not 1 <= initial_faces <= 96):
        raise ValueError("Invalid adaptive initial observation")
    lo, hi = LOW_CENTI, HIGH_CENTI
    best_metric = {"sampled_max_distance": initial_max,
                   "socket_sampled_affected_faces": initial_faces,
                   "other_parts_sampled_affected_faces": 0}
    best_id = "narrow"
    feasible = None
    lines = [
        "# GLB-022 自作合成ソケットの適応型探索",
        "",
        "**実アドオンの寸法提案ではありません。** 目標値0.12は"
        "CBDK合成テスト用の最大サンプル距離で、実物の公差ではありません。",
        "",
        "| 回 | 次の候補 | 観測最大距離 | 目標以内？ | 方向 |",
        "| ---: | ---: | ---: | :---: | --- |",
    ]
    for i, row in enumerate(history["steps"], 1):
        midpoint = next_candidate(lo, hi)
        if midpoint is None or not isinstance(row, dict) or set(row) != {
            "attempt", "trial_id", "generated_socket_diameter",
            "bracket_before", "bracket_after", "sampled_max",
            "socket_affected_faces", "other_affected_faces", "target_met",
            "accepted_as_measured_progress", "progress_reason",
            "best_observed_trial_after", "best_feasible_trial_after",
        }:
            raise ValueError("Invalid adaptive step")
        value = row["sampled_max"]
        if (type(row["attempt"]) is not int or row["attempt"] != i
                or row["trial_id"] != trial_id(midpoint)
                or type(row["generated_socket_diameter"]) not in (int, float)
                or row["generated_socket_diameter"] != midpoint / 100
                or row["bracket_before"] != [lo / 100, hi / 100]
                or type(value) not in (int, float) or
                not (0 <= value <= 1e5)
                or type(row["socket_affected_faces"]) is not int
                or not 0 <= row["socket_affected_faces"] <= 96
                or row["other_affected_faces"] != 0
                or type(row["other_affected_faces"]) is not int
                or type(row["target_met"]) is not bool
                or row["target_met"] != (value <= TARGET_SAMPLED_MAX)
                or type(row["accepted_as_measured_progress"]) is not bool
                or row["progress_reason"] not in (
                    "strict_sampled_max_improvement_without_observed_regression",
                    "no_meaningful_sampled_max_improvement",
                    "socket_classification_regression")):
            raise ValueError("Forged adaptive observation or score")
        candidate_metric = {
            "sampled_max_distance": value,
            "socket_sampled_affected_faces": row["socket_affected_faces"],
            "other_parts_sampled_affected_faces": 0,
        }
        valid_improvement, valid_reason = _decision(best_metric, candidate_metric)
        if (row["accepted_as_measured_progress"] is not valid_improvement
                or row["progress_reason"] != valid_reason):
            raise ValueError("Forged sampled improvement claim")
        if valid_improvement:
            best_metric = candidate_metric
        meets = row["target_met"]
        if meets:
            hi, feasible = midpoint, trial_id(midpoint)
        else:
            lo = midpoint
        if valid_improvement:
            best_id = trial_id(midpoint)
        if (row["bracket_after"] != [lo / 100, hi / 100]
                or row["best_feasible_trial_after"] != feasible
                or row["best_observed_trial_after"] != best_id):
            raise ValueError("Forged adaptive bracket or accepted result")
        direction = "より小さい値へ" if meets else "より大きい値へ"
        lines.append(
            f"| {i} | {midpoint / 100:.2f} | {value:.7f} | "
            f"{'はい' if meets else 'いいえ'} | {direction} |"
        )
    expected_status = ("target_feasible_in_sampled_test"
                       if feasible else "no_measured_feasible_candidate")
    expected_stop = ("attempt_budget_exhausted" if next_candidate(lo, hi) is not None
                     else "centi_unit_bracket_converged")
    if (history["initial_bracket"] != [LOW_CENTI / 100, HIGH_CENTI / 100]
            or history["final_bracket"] != [lo / 100, hi / 100]
            or history["best_observed_trial_id"] != best_id
            or history["measured_feasible_trial_id"] != feasible
            or history["sampled_target_status"] != expected_status
            or history["stop_reason"] != expected_stop):
        raise ValueError("Inconsistent adaptive conclusion")
    lines.extend([
        "",
        f"**停止**：{expected_stop}。目標内の観測候補："
        f"{feasible if feasible else 'まだ確認できず'}。",
        "**注意**：評価は全体の双方向サンプリング最大距離であり、"
        "部品別誤差・厳密Hausdorff距離・実ジョイントの最適値を証明しません。",
        "",
    ])
    return "\n".join(lines)


def write_adaptive_history(history: dict, directory) -> tuple[Path, Path]:
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected trusted local report directory")
    markdown = render_adaptive_history(history)
    paths = (root / "synthetic_adaptive_history.json",
             root / "synthetic_adaptive_history.md")
    if any(p.exists() or p.is_symlink() for p in paths):
        raise FileExistsError("Synthetic history must not overwrite")
    body = json.dumps(history, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with paths[0].open("x", encoding="utf-8") as handle:
        handle.write(body)
    with paths[1].open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    return paths
