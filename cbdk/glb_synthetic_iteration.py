"""GLB-022 stage 1: FIXED, bounded CBDK synthetic generate/compare trials.

This pure decision module operates on aggregate GLB-020 reports only; the
separate CI-only driver regenerates allowlisted synthetic meshes each step.
It is not an arbitrary addon runner, optimizer, or verified full-mesh solver.
"""
from __future__ import annotations

import json
from pathlib import Path

from .glb_synthetic_trial_history import _part_observations

BASELINE = "narrow"
CANDIDATES = ("narrow_placebo", "identical")
FIXTURE_CONTROLS = {
    "narrow": {"socket_opening_diameter": 0.78, "ball_shifted": False},
    "narrow_placebo": {"socket_opening_diameter": 0.78, "ball_shifted": True},
    "identical": {"socket_opening_diameter": 1.70, "ball_shifted": False},
}
MAX_ATTEMPTS = 2
OUTPUT_JSON = "synthetic_iteration_history.json"
OUTPUT_MD = "synthetic_iteration_history.md"


def _safe_rows(report):
    rows = _part_observations(report)  # Validated GLB-020 aggregate + safety flags.
    if any(row["observed_boundary_edges"] != 0 for row in rows):
        raise ValueError("Closed synthetic fixture unexpectedly has boundary edges")
    return rows


def _score(rows):
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("Unexpected synthetic part count")
    return {
        "socket_sampled_affected_faces": rows[2]["affected_faces"],
        "other_parts_sampled_affected_faces":
            rows[0]["affected_faces"] + rows[1]["affected_faces"],
    }


def _decision(before, after):
    """A strict *observed* improvement without new errors in other parts."""
    if after["socket_sampled_affected_faces"] >= before["socket_sampled_affected_faces"]:
        return False, "socket_not_improved"
    if (after["other_parts_sampled_affected_faces"] >
            before["other_parts_sampled_affected_faces"]):
        return False, "unrelated_part_regression"
    return True, "strict_sampled_socket_improvement_no_observed_regression"


def build_synthetic_iteration_history(reports):
    if not isinstance(reports, dict) or set(reports) != set(FIXTURE_CONTROLS):
        raise ValueError("Exactly three CBDK-owned synthetic conditions required")
    rows = {name: _safe_rows(reports[name]) for name in FIXTURE_CONTROLS}
    score = {name: _score(r) for name, r in rows.items()}
    if score[BASELINE]["socket_sampled_affected_faces"] <= 0:
        raise ValueError("Initial synthetic defect not observed")
    if score[BASELINE]["other_parts_sampled_affected_faces"] != 0:
        raise ValueError("Synthetic baseline must change only socket")
    attempts = []
    current = BASELINE
    reason = "attempt_budget_exhausted"
    for candidate in CANDIDATES[:MAX_ATTEMPTS]:
        before = score[current]
        after = score[candidate]
        accepted, decision = _decision(before, after)
        attempts.append({
            "attempt_number": len(attempts) + 1,
            "candidate_id": candidate,
            "control": dict(FIXTURE_CONTROLS[candidate]),
            "baseline_id_before": current,
            "before_sampled": dict(before),
            "candidate_sampled": dict(after),
            "accepted": accepted,
            "decision": decision,
            "baseline_id_after": candidate if accepted else current,
            "real_addon_parameter_inferred": False,
        })
        if accepted:
            current = candidate
        if (score[current]["socket_sampled_affected_faces"] == 0 and
                score[current]["other_parts_sampled_affected_faces"] == 0):
            reason = "observed_zero_and_no_other_part_regression"
            break
    if (len(attempts) != 2 or attempts[0]["accepted"]
            or attempts[1]["accepted"] is not True or current != "identical"
            or reason != "observed_zero_and_no_other_part_regression"):
        # This stage is deliberately a fixed synthetic positive/negative test,
        # NOT an unconstrained search that might silently accept a bad edit.
        raise ValueError("CBDK synthetic accept/reject gate not met")
    return {
        "kind": "cbdk_glb022_allowlisted_iteration_v1",
        "schema_version": 1,
        "status": "synthetic_test_only",
        "baseline": BASELINE,
        "max_attempts": MAX_ATTEMPTS,
        "attempts_executed": len(attempts),
        "attempts": attempts,
        "accepted_candidate_id": current,
        "stop_reason": reason,
        "final_observations": score[current],
        "input_report_scope": "glb020_aggregate_only_cbdk_owned_joint_fixture",
        "safety": {
            "runs_user_addons": False,
            "executes_private_source": False,
            "changes_user_source_or_glbs": False,
            "auto_approves_real_change": False,
            "recommends_user_parameter_values": False,
            "proves_real_addon_causality": False,
            "proves_complete_surface_equivalence": False,
            "proves_part_identity_across_glbs": False,
        },
    }


def render_iteration_markdown(history):
    if (not isinstance(history, dict)
            or history.get("kind") != "cbdk_glb022_allowlisted_iteration_v1"
            or history.get("schema_version") != 1
            or history.get("status") != "synthetic_test_only"
            or history.get("baseline") != BASELINE
            or history.get("max_attempts") != MAX_ATTEMPTS
            or history.get("attempts_executed") != 2
            or history.get("accepted_candidate_id") != "identical"
            or history.get("stop_reason") != "observed_zero_and_no_other_part_regression"
            or not isinstance(history.get("attempts"), list)
            or len(history["attempts"]) != 2):
        raise ValueError("Invalid synthetic iteration schema")
    safety = history.get("safety")
    if (not isinstance(safety, dict) or len(safety) != 8
            or any(type(v) is not bool or v for v in safety.values())):
        raise ValueError("Iteration history contains unsafe assertion")
    attempts = history["attempts"]
    for i, (attempt, candidate) in enumerate(zip(attempts, CANDIDATES)):
        if (not isinstance(attempt, dict)
                or attempt.get("attempt_number") != i + 1
                or attempt.get("candidate_id") != candidate
                or attempt.get("control") != FIXTURE_CONTROLS[candidate]
                or attempt.get("baseline_id_before") !=
                    (BASELINE if i == 0 else BASELINE)
                or attempt.get("baseline_id_after") !=
                    (BASELINE if i == 0 else "identical")
                or attempt.get("accepted") is not (i == 1)
                or attempt.get("real_addon_parameter_inferred") is not False
                or attempt.get("decision") !=
                    ("socket_not_improved" if i == 0 else
                     "strict_sampled_socket_improvement_no_observed_regression")):
            raise ValueError("Unexpected synthetic trial history")
        before, after = attempt.get("before_sampled"), attempt.get("candidate_sampled")
        for item in (before, after):
            if (not isinstance(item, dict) or set(item) != {
                    "socket_sampled_affected_faces",
                    "other_parts_sampled_affected_faces"}
                    or any(type(x) is not int or not 0 <= x <= 152
                           for x in item.values())):
                raise ValueError("Invalid sampled counters")
        if _decision(before, after) != (attempt["accepted"], attempt["decision"]):
            raise ValueError("Forged accept/reject decision")
        if i == 1 and (after != history.get("final_observations")
                       or after != {"socket_sampled_affected_faces": 0,
                                   "other_parts_sampled_affected_faces": 0}):
            raise ValueError("Synthetic termination not supported by observations")
        if i == 0 and before != attempts[1]["before_sampled"]:
            raise ValueError("Rejected placebo must not change accepted baseline")
    lines = [
        "# GLB-022 自作合成モデルだけの反復試験（自動適用なし）",
        "",
        "**これは実アドオンの最適化ではありません。** "
        "CBDK固定モデルで観測したサンプル面数の比較です。",
        "",
        "| 試行 | テスト操作 | ソケット黄＋赤（前→候補） | その他部品（前→候補） | 判断 |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in attempts:
        before, after = row["before_sampled"], row["candidate_sampled"]
        lines.append(
            f'| {row["attempt_number"]} | `{row["candidate_id"]}` | '
            f'{before["socket_sampled_affected_faces"]} → '
            f'{after["socket_sampled_affected_faces"]} | '
            f'{before["other_parts_sampled_affected_faces"]} → '
            f'{after["other_parts_sampled_affected_faces"]} | '
            f'{"採用（合成実験のみ）" if row["accepted"] else "不採用"} |'
        )
    lines.extend([
        "",
        "**停止理由**：合成モデルでソケットの観測差分0、他部品の観測悪化なし。",
        "**注意**：実ユーザーGLB・ソースを実行/書換せず、実際の設定値・因果関係・"
        "幾何の完全一致・真の部品同一性は未証明。",
        "",
    ])
    return "\n".join(lines)


def write_iteration_history(history, directory):
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected existing local synthetic CI directory")
    rendered = render_iteration_markdown(history)
    result_json = root / OUTPUT_JSON
    result_md = root / OUTPUT_MD
    if any(p.exists() or p.is_symlink() for p in (result_json, result_md)):
        raise FileExistsError("Synthetic iteration report already exists")
    serialized = json.dumps(history, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with result_json.open("x", encoding="utf-8") as fh:
        fh.write(serialized)
    with result_md.open("x", encoding="utf-8") as fh:
        fh.write(rendered)
    return result_json, result_md
