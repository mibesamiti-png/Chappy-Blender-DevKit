"""GLB-022 phase 4: deterministic synthetic-only numeric candidate generation.

The grid is arithmetically derived from trusted CBDK fixture bounds, not user
supplied or source-code-derived. The measured score is an aggregate, sampled
bidirectional scene maximum, NOT exact geometry equivalence or an inferred
parameter adjustment for a real addon.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .glb_synthetic_progress import MIN_DELTA, _decision, _metric

LOW_CENTI = 78
HIGH_CENTI = 170
MAX_STEPS = 4
STEP_CENTI = (HIGH_CENTI - LOW_CENTI) // MAX_STEPS
BASELINE = "narrow"
SAFETY = {
    "only_repo_owned_synthetic_fixtures": True,
    "user_addon_executed": False,
    "private_user_glb_loaded": False,
    "original_input_modified": False,
    "automatic_user_parameter_application": False,
    "recommends_user_parameter_value": False,
    "real_addon_causality_proven": False,
    "complete_surface_equivalence_proven": False,
    "part_identity_proven": False,
}


def candidate_values():
    """Generate four safe 2-decimal settings algorithmically; no free inputs."""
    if (HIGH_CENTI - LOW_CENTI) % MAX_STEPS:
        raise ValueError("Invalid fixed synthetic lattice")
    values = tuple((LOW_CENTI + n * STEP_CENTI) / 100
                   for n in range(1, MAX_STEPS + 1))
    if len(values) != MAX_STEPS or len(set(values)) != MAX_STEPS:
        raise ValueError("Invalid bounded synthetic candidate grid")
    return values


def trial_id(value):
    if type(value) not in (float, int) or value not in candidate_values():
        raise ValueError("Only generated CBDK grid values are allowed")
    return f"grid_{round(value * 100):03d}"


def build_grid_history(baseline, trials, *, budget=MAX_STEPS):
    """Accept only strict sampled-max decrease without other-part regression.

    Fail closed on unknown trial IDs and bogus completion claims. A budget of
    1..3 produces an honestly unfinished state; 4 can reach sampled zero.
    """
    if type(budget) is not int or not 1 <= budget <= MAX_STEPS:
        raise ValueError("Synthetic attempt budget must be 1..4")
    expected = tuple(trial_id(v) for v in candidate_values()[:budget])
    if not isinstance(trials, dict) or tuple(trials) != expected:
        raise ValueError("Unapproved or out-of-order grid trial")
    initial = _metric(baseline)
    if (initial["socket_sampled_affected_faces"] <= 0
            or initial["other_parts_sampled_affected_faces"] != 0
            or initial["sampled_max_distance"] <= MIN_DELTA):
        raise ValueError("Missing original synthetic defect")
    accepted_id = BASELINE
    best = initial
    steps = []
    stopped_early = False
    for n, (value, name) in enumerate(zip(candidate_values()[:budget], expected), 1):
        candidate = _metric(trials[name])
        if (candidate["combined_aabb_diagonal"] != initial["combined_aabb_diagonal"]):
            raise ValueError("Synthetic scene scale changed")
        accepted, reason = _decision(best, candidate)
        if candidate["other_parts_sampled_affected_faces"] != 0:
            raise ValueError("Generated socket-only candidate regressed other parts")
        if n == MAX_STEPS and (candidate["sampled_max_distance"] > MIN_DELTA
                                or candidate["socket_sampled_affected_faces"] != 0):
            raise ValueError("Known synthetic reference endpoint did not recover")
        steps.append({
            "attempt": n,
            "trial_id": name,
            "generated_socket_diameter": value,
            "baseline_before": accepted_id,
            "max_sampled_before": best["sampled_max_distance"],
            "max_sampled_candidate": candidate["sampled_max_distance"],
            "socket_faces_before": best["socket_sampled_affected_faces"],
            "socket_faces_candidate": candidate["socket_sampled_affected_faces"],
            "other_faces_candidate": candidate["other_parts_sampled_affected_faces"],
            "accepted": bool(accepted),
            "decision": reason,
            "baseline_after": name if accepted else accepted_id,
        })
        if accepted:
            accepted_id = name
            best = candidate
        if (best["sampled_max_distance"] <= MIN_DELTA
                and best["socket_sampled_affected_faces"] == 0
                and best["other_parts_sampled_affected_faces"] == 0):
            stopped_early = n < budget
            break
    if (len(steps) != budget or stopped_early or
            (budget == MAX_STEPS and accepted_id != expected[-1]) or
            (budget < MAX_STEPS and best["sampled_max_distance"] <= MIN_DELTA)):
        raise ValueError("Unexpected synthetic grid stopping state")
    return {
        "kind": "cbdk_glb022_bounded_generated_grid_v1",
        "schema_version": 1,
        "status": "synthetic_test_only",
        "generated_candidate_values": list(candidate_values()),
        "max_attempts": MAX_STEPS,
        "attempt_budget": budget,
        "attempts": steps,
        "accepted_trial_id": accepted_id,
        "stop_reason": ("observed_sampled_zero" if budget == MAX_STEPS
                        else "attempt_budget_exhausted_unfinished"),
        "final_sampled_max": best["sampled_max_distance"],
        "metric": "global_bidirectional_sampled_max_distance_not_exact_hausdorff",
        "safety": dict(SAFETY),
    }


def render_grid_history(result):
    """Validate every control and decision before rendering private evidence."""
    if (not isinstance(result, dict)
            or set(result) != {
                "kind", "schema_version", "status", "generated_candidate_values",
                "max_attempts", "attempt_budget", "attempts", "accepted_trial_id",
                "stop_reason", "final_sampled_max", "metric", "safety"
            }
            or result["kind"] != "cbdk_glb022_bounded_generated_grid_v1"
            or type(result["schema_version"]) is not int
            or result["schema_version"] != 1
            or result["status"] != "synthetic_test_only"
            or result["generated_candidate_values"] != list(candidate_values())
            or result["max_attempts"] != MAX_STEPS
            or result["metric"] !=
            "global_bidirectional_sampled_max_distance_not_exact_hausdorff"
            or result["safety"] != SAFETY):
        raise ValueError("Unsafe or forged grid report")
    budget = result["attempt_budget"]
    if (type(budget) is not int or not 1 <= budget <= MAX_STEPS
            or not isinstance(result["attempts"], list)
            or len(result["attempts"]) != budget):
        raise ValueError("Invalid grid history budget")
    lines = [
        "# GLB-022 合成ソケットの自動候補生成と改善履歴",
        "",
        "**実ユーザーアドオンの設定変更・推奨値ではありません。**",
        "候補はCBDKの固定安全範囲0.78～1.70を4等分して算出しています。",
        "数値は座標単位のサンプル最大値で、厳密Hausdorff距離ではありません。",
        "",
        "| 回 | 自動生成の開口直径 | 最大サンプル距離（前→候補） | 判定 |",
        "| ---: | ---: | ---: | --- |",
    ]
    accepted_id = BASELINE
    best = None
    for i, (row, value) in enumerate(zip(result["attempts"],
                                         candidate_values()), 1):
        if (not isinstance(row, dict)
                or set(row) != {
                    "attempt", "trial_id", "generated_socket_diameter",
                    "baseline_before", "max_sampled_before",
                    "max_sampled_candidate", "socket_faces_before",
                    "socket_faces_candidate", "other_faces_candidate",
                    "accepted", "decision", "baseline_after",
                }
                or type(row["attempt"]) is not int or row["attempt"] != i
                or row["trial_id"] != trial_id(value)
                or type(row["generated_socket_diameter"]) not in (float, int)
                or row["generated_socket_diameter"] != value
                or row["baseline_before"] != accepted_id
                or any(type(row[x]) not in (int, float)
                       or not math.isfinite(row[x]) or not 0 <= row[x] <= 1e5
                       for x in ("max_sampled_before", "max_sampled_candidate"))
                or any(type(row[x]) is not int or not 0 <= row[x] <= cap
                       for x, cap in (
                           ("socket_faces_before", 96),
                           ("socket_faces_candidate", 96),
                           ("other_faces_candidate", 56)))):
            raise ValueError("Unsafe synthetic grid step")
        if best is not None and row["max_sampled_before"] != best:
            raise ValueError("Rejected candidate changed accepted baseline")
        before = {
            "sampled_max_distance": row["max_sampled_before"],
            "socket_sampled_affected_faces": row["socket_faces_before"],
            "other_parts_sampled_affected_faces": 0,
        }
        after = {
            "sampled_max_distance": row["max_sampled_candidate"],
            "socket_sampled_affected_faces": row["socket_faces_candidate"],
            "other_parts_sampled_affected_faces": row["other_faces_candidate"],
        }
        accepted, reason = _decision(before, after)
        if (row["accepted"] is not accepted or row["decision"] != reason
                or row["other_faces_candidate"] != 0):
            raise ValueError("Grid report falsified its acceptance decision")
        accepted_id = row["trial_id"] if accepted else accepted_id
        if row["baseline_after"] != accepted_id:
            raise ValueError("Unverified synthetic grid baseline")
        best = row["max_sampled_candidate"] if accepted else row["max_sampled_before"]
        verdict = "採用（合成モデル内）" if accepted else "棄却（測定改善なし）"
        lines.append(
            f'| {i} | {value:.2f} | '
            f'{row["max_sampled_before"]:.7f}→'
            f'{row["max_sampled_candidate"]:.7f} | {verdict} |'
        )
    stop = ("observed_sampled_zero" if budget == MAX_STEPS
            else "attempt_budget_exhausted_unfinished")
    if (result["accepted_trial_id"] != accepted_id
            or result["stop_reason"] != stop
            or type(result["final_sampled_max"]) not in (float, int)
            or not math.isfinite(result["final_sampled_max"])
            or result["final_sampled_max"] != best
            or (budget == MAX_STEPS and best > MIN_DELTA)
            or (budget < MAX_STEPS and best <= MIN_DELTA)):
        raise ValueError("Grid report has unsupported final state")
    lines.extend([
        "",
        f"**停止理由**：{stop}。未完了の場合は未完了として記録。",
        "**注意**：サンプリング差分0は全形状一致ではありません。",
        "任意のアドオンを実行したり、ユーザーの元データを編集したりしません。",
        "",
    ])
    return "\n".join(lines)


def write_grid_history(result, directory):
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing local synthetic grid report directory")
    markdown = render_grid_history(result)
    files = (root / "synthetic_grid_history.json",
             root / "synthetic_grid_history.md")
    if any(path.is_symlink() or path.exists() for path in files):
        raise FileExistsError("Synthetic grid history must not overwrite")
    content = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with files[0].open("x", encoding="utf-8") as stream:
        stream.write(content)
    with files[1].open("x", encoding="utf-8") as stream:
        stream.write(markdown)
    return files
