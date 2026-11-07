"""Local, bounded review of completed or interrupted synthetic adaptive runs.

No exception messages, paths, source, GLB geometry or arbitrary labels are saved.
A checkpoint proves neither process liveness nor successful completion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .glb_surface_pipeline import _strict_json
from .glb_synthetic_adaptive import (
    MAX_TRIALS, SAFETY, next_candidate, render_adaptive_checkpoint, trial_id,
)
from .glb_synthetic_conditions import validate_conditions

KIND = "cbdk_glb022_synthetic_run_review_v1"
MAX_CHECKPOINTS = 16
STAGES = {
    "reference_generation", "baseline_generation", "baseline_comparison",
    "candidate_generation", "candidate_comparison", "measurement_validated",
    "input_integrity", "history_output", "completed",
}
ACTIONS = {
    "generation_failed": "合成生成器の実行環境と終了状態をローカルで確認する。",
    "generation_timeout": "Blenderの起動・負荷を確認する。自動再試行はしない。",
    "comparison_failed": "ローカルの比較出力を確認し、未検証出力を採用しない。",
    "comparison_timeout": "比較処理の負荷を確認し、未測定候補を採用しない。",
    "invalid_measurement": "測定JSONの安全フラグ・面数・値を確認する。",
    "cross_part_regression": "他部品の観測悪化を確認し、この候補を採用しない。",
    "coordinate_scale_changed": "合成モデルの座標スケールが変わった理由を確認する。",
    "input_integrity_changed": "入力または生成器が変更されたため、観測を採用せず隔離する。",
    "io_failure": "出力先の容量・権限を確認し、既存証拠を上書きしない。",
    "interrupted": "処理が中断された。最後の検証済み測定を人が確認する。",
    "unexpected_error": "未分類の失敗。ローカルで原因を確認し、完了扱いしない。",
}


def build_run_review(checkpoint, *, budget, stage, status="incomplete",
                     active_trial=None, failure_code=None, integrity="not_checked",
                     conditions=None):
    if type(budget) is not int or not 1 <= budget <= MAX_TRIALS:
        raise ValueError("Invalid review budget")
    if stage not in STAGES or status not in ("incomplete", "failed", "completed"):
        raise ValueError("Invalid run state")
    if integrity not in ("not_checked", "verified", "failed"):
        raise ValueError("Invalid input integrity")
    if checkpoint is not None:
        render_adaptive_checkpoint(checkpoint)
        if checkpoint["attempt_budget"] != budget:
            raise ValueError("Checkpoint budget disagrees")
    attempts = 0 if checkpoint is None else checkpoint["attempts_executed"]
    if active_trial is not None:
        if checkpoint is None or attempts >= budget or stage not in (
            "candidate_generation", "candidate_comparison",
        ):
            raise ValueError("Invalid active candidate")
        lo, hi = (round(x * 100) for x in checkpoint["final_bracket"])
        value = next_candidate(lo, hi)
        if value is None or active_trial != trial_id(value):
            raise ValueError("Active trial does not follow measured feedback")
    elif stage in ("candidate_generation", "candidate_comparison"):
        raise ValueError("Candidate stage requires its trial")
    if checkpoint is None and stage not in (
        "reference_generation", "baseline_generation", "baseline_comparison",
    ):
        raise ValueError("This stage requires validated baseline evidence")
    if checkpoint is not None and stage in (
        "reference_generation", "baseline_generation", "baseline_comparison",
    ):
        raise ValueError("Baseline preparation cannot contain trial evidence")
    if status == "failed":
        if failure_code not in ACTIONS or stage == "completed":
            raise ValueError("Failure requires a fixed diagnostic code")
        if failure_code.startswith("generation_") and stage not in (
            "reference_generation", "baseline_generation", "candidate_generation",
        ):
            raise ValueError("Generation failure disagrees with stage")
        if failure_code.startswith("comparison_") and stage not in (
            "baseline_comparison", "candidate_comparison",
        ):
            raise ValueError("Comparison failure disagrees with stage")
        if failure_code in ("cross_part_regression", "coordinate_scale_changed") and stage != "candidate_comparison":
            raise ValueError("Candidate failure disagrees with stage")
    elif failure_code is not None:
        raise ValueError("Only failed runs may contain failure codes")
    if (integrity == "failed") != (failure_code == "input_integrity_changed"):
        raise ValueError("Inconsistent integrity failure")
    if status == "completed":
        if (stage != "completed" or checkpoint is None or attempts != budget
                or integrity != "verified"):
            raise ValueError("Unfinished run cannot be marked completed")
    elif stage == "completed":
        raise ValueError("Completed stage requires completed status")
    feasible = None if checkpoint is None else checkpoint["measured_feasible_trial_id"]
    output = {
        "kind": KIND, "schema_version": 1, "status": status, "stage": stage,
        "attempt_budget": budget, "validated_attempts": attempts,
        "unvalidated_attempts": budget - attempts, "active_trial_id": active_trial,
        "failure_code": failure_code, "input_integrity": integrity,
        "run_completed": status == "completed",
        "sampled_goal_observed": feasible is not None,
        "checkpoint": checkpoint, "safety": dict(SAFETY),
        "automatic_retry": False, "automatic_resume": False,
    }
    if conditions is not None:
        conditions = validate_conditions(conditions)
        if (checkpoint is None
                or conditions["initial_sampled_max"] != checkpoint["initial_sampled_max"]
                or conditions["initial_socket_affected_faces"] != checkpoint["initial_socket_affected_faces"]):
            raise ValueError("Conditions contradict validated baseline")
        output.update(kind="cbdk_glb022_synthetic_run_review_v2", schema_version=2,
                      conditions=conditions)
    return output


def render_run_review(report):
    if not isinstance(report, dict):
        raise ValueError("Expected run review")
    try:
        expected = build_run_review(
            report["checkpoint"], budget=report["attempt_budget"],
            stage=report["stage"], status=report["status"],
            active_trial=report["active_trial_id"], failure_code=report["failure_code"],
            integrity=report["input_integrity"],
            conditions=report.get("conditions"),
        )
        if json.dumps(report, sort_keys=True, allow_nan=False) != json.dumps(
            expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError("Forged run review")
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("Malformed run review") from exc
    states = {"incomplete": "実行中または未完了（終了証拠なし）",
              "failed": "失敗・停止", "completed": "試行予算を完了（最適性は未証明）"}
    action = ACTIONS.get(report["failure_code"],
                         "目標内の観測候補と打切り条件を人が確認する。")
    if report["status"] == "incomplete":
        action = "この記録からプロセスの稼働や正常終了は判定できない。終了証拠を確認する。"
    checkpoint = report["checkpoint"]
    best = "未測定" if checkpoint is None else checkpoint["best_observed_trial_id"]
    feasible = None if checkpoint is None else checkpoint["measured_feasible_trial_id"]
    lines = [
        "# GLB-022 合成反復の実行レビュー", "",
        f"**状態**：{states[report['status']]}。工程：{report['stage']}。",
        f"検証済み試行：{report['validated_attempts']}/{report['attempt_budget']}。"
        f"未検証枠（処理中・失敗した候補を含む）：{report['unvalidated_attempts']}。",
        f"処理対象：{report['active_trial_id'] or 'なし'}。"
        f"失敗区分：{report['failure_code'] or 'なし'}。",
        f"入力SHA-256照合：{report['input_integrity']}。", "",
        f"観測上の最良：{best}。合成目標内の観測：{feasible or '未確認'}。",
        "入力整合性がverifiedでなければ、この観測を採用しない。"
        "目標内候補があっても実行完了・最適値・完全一致を意味しない。", "",
        "## 人が確認すること", "", f"- {action}",
        "- 自動再試行・自動再開は行わない。再実行する場合は新しい出力先を使用する。",
        "- CBDK自作の合成試験限定。実ユーザー設定の推薦・実アドオン因果・"
        "厳密Hausdorff距離・内部空洞の一致は未検証。", "",
    ]
    if checkpoint is not None:
        lines.extend(["## 最後の検証済み観測履歴", "", render_adaptive_checkpoint(checkpoint)])
    return "\n".join(lines)


def write_run_review(report, directory, *, sequence=None):
    """Write immutable checkpoint pairs or a single new terminal review pair."""
    markdown = render_run_review(report)
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected local review directory")
    if sequence is not None:
        if type(sequence) is not int or not 0 <= sequence < MAX_CHECKPOINTS:
            raise ValueError("Excessive checkpoint sequence")
        if report["status"] != "incomplete":
            raise ValueError("Checkpoints cannot certify a terminal state")
        stem = f"checkpoint_{sequence:03d}"
    else:
        if report["status"] == "incomplete":
            raise ValueError("Terminal review requires a terminal state")
        stem = "synthetic_run_review"
    paths = (root / (stem + ".json"), root / (stem + ".md"))
    if any(p.exists() or p.is_symlink() for p in paths):
        raise FileExistsError("Run review must not overwrite")
    # Publish the machine-readable receipt last. An incomplete Markdown write
    # must not leave a valid JSON success receipt behind.
    with paths[1].open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    with paths[0].open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    return paths


def read_run_review(path):
    source = Path(path)
    if (source.is_symlink() or not source.is_file()
            or source.stat().st_size > 128 * 1024):
        raise ValueError("Missing or oversized run review")
    report = _strict_json(source.read_text(encoding="utf-8"))
    render_run_review(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read local synthetic run evidence only")
    parser.add_argument("report", help="Terminal or checkpoint JSON; does not resume execution")
    args = parser.parse_args(argv)
    try:
        print(render_run_review(read_run_review(args.report)))
    except (OSError, ValueError, RecursionError):
        parser.exit(2, "Invalid local synthetic run review; no evidence accepted\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
