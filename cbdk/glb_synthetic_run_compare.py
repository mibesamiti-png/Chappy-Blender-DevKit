"""Read-only, same-condition review of 2..16 CBDK synthetic experiments.

No Blender launch, addon execution, automatic ranking/adoption, or source edits.
Untrusted labels/paths and invalid report contents never enter saved output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .glb_synthetic_progress import MIN_DELTA
from .glb_synthetic_run_review import read_run_review, render_run_review

MAX_RUNS = 16
KIND = "cbdk_glb022_same_condition_comparison_v1"
REASONS = {
    "invalid_report": "不正な実行証拠",
    "run_failed": "実行が失敗",
    "run_incomplete": "正常終了の証拠なし",
    "input_integrity_unverified": "入力整合性が未確認または変更あり",
    "missing_conditions": "旧形式などで実験条件の証拠なし",
    "no_eligible_anchor": "比較基準に使える完了実行なし",
    "budget_mismatch": "試行予算が不一致",
    "conditions_mismatch": "プロトコル・版・コード・GLB・指標・初期観測などが不一致",
}
LABELS = {
    "excluded": "比較対象外", "anchor": "比較基準",
    "observed_improvement": "観測上の改善",
    "observed_regression": "観測上の悪化",
    "no_meaningful_difference": "有意な観測差なし",
    "mixed_observations": "指標が混在・人手確認",
}


def _validated_copy(report):
    try:
        render_run_review(report)
        return json.loads(json.dumps(report, allow_nan=False))
    except (ValueError, TypeError, RecursionError, OverflowError):
        return None


def _exclusion(report):
    if report is None:
        return "invalid_report"
    if report["input_integrity"] != "verified":
        return "input_integrity_unverified"
    if report["status"] == "failed":
        return "run_failed"
    if report["status"] != "completed":
        return "run_incomplete"
    if "conditions" not in report:
        return "missing_conditions"
    return None


def _best(checkpoint):
    best_id = checkpoint["best_observed_trial_id"]
    if best_id == "narrow":
        return (best_id, checkpoint["initial_sampled_max"],
                checkpoint["initial_socket_affected_faces"])
    row = next(x for x in checkpoint["steps"] if x["trial_id"] == best_id)
    return best_id, row["sampled_max"], row["socket_affected_faces"]


def compare_run_reviews(reviews):
    if not isinstance(reviews, list) or not 2 <= len(reviews) <= MAX_RUNS:
        raise ValueError("Expected 2..16 synthetic run reviews")
    normalized = [_validated_copy(value) for value in reviews]
    anchor_index = next((i for i, report in enumerate(normalized)
                         if _exclusion(report) is None), None)
    anchor = None if anchor_index is None else normalized[anchor_index]
    rows = []
    for index, report in enumerate(normalized):
        reason = _exclusion(report)
        if reason is None and anchor is not None:
            if report["attempt_budget"] != anchor["attempt_budget"]:
                reason = "budget_mismatch"
            elif report["conditions"] != anchor["conditions"]:
                reason = "conditions_mismatch"
        elif reason is None:
            reason = "no_eligible_anchor"
        row = {
            "run_id": f"run_{index + 1:03d}",
            "run_status": "invalid" if report is None else report["status"],
            "comparison_status": "excluded", "exclusion_reason": reason,
            "validated_attempts": None if report is None else report["validated_attempts"],
            "best_trial_id": None, "best_sampled_max": None,
            "socket_affected_faces": None, "observed_goal_in_prefix": False,
            "sampled_max_delta_from_anchor": None, "socket_faces_delta_from_anchor": None,
        }
        if report is not None and report["input_integrity"] == "verified" and report["checkpoint"] is not None:
            best_id, distance, faces = _best(report["checkpoint"])
            row.update(best_trial_id=best_id, best_sampled_max=distance,
                       socket_affected_faces=faces,
                       observed_goal_in_prefix=report["sampled_goal_observed"])
        if reason is None:
            _, base_distance, base_faces = _best(anchor["checkpoint"])
            delta = round(row["best_sampled_max"] - base_distance, 7)
            face_delta = row["socket_affected_faces"] - base_faces
            if index == anchor_index:
                status = "anchor"
            elif abs(delta) <= MIN_DELTA and face_delta == 0:
                status = "no_meaningful_difference"
            elif delta < -MIN_DELTA and face_delta <= 0:
                status = "observed_improvement"
            elif delta > MIN_DELTA and face_delta >= 0:
                status = "observed_regression"
            else:
                status = "mixed_observations"
            row.update(comparison_status=status, sampled_max_delta_from_anchor=delta,
                       socket_faces_delta_from_anchor=face_delta)
        rows.append(row)
    eligible = sum(row["comparison_status"] != "excluded" for row in rows)
    return {
        "kind": KIND, "schema_version": 1, "status": "review_only",
        "anchor_run_id": None if anchor_index is None else f"run_{anchor_index + 1:03d}",
        "eligible_runs": eligible, "excluded_runs": len(rows) - eligible,
        "comparison_available": eligible >= 2, "rows": rows,
        "input_reviews": normalized,
        "safety": {
            "executes_code": False, "auto_applies_settings": False,
            "recommends_optimal_run": False, "proves_causality": False,
            "proves_exact_geometry": False, "authenticates_reports": False,
        },
    }


def render_run_comparison(report):
    if not isinstance(report, dict):
        raise ValueError("Expected comparison report")
    try:
        expected = compare_run_reviews(report["input_reviews"])
        if json.dumps(report, sort_keys=True, allow_nan=False) != json.dumps(
            expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError("Forged comparison summary")
    except (KeyError, TypeError, RecursionError, OverflowError) as exc:
        raise ValueError("Malformed comparison summary") from exc
    lines = [
        "# GLB-021/022 同条件の合成実験比較レビュー", "",
        f"比較可能：{report['eligible_runs']}件。対象外：{report['excluded_runs']}件。"
        f"比較基準：{report['anchor_run_id'] or 'なし'}。",
        "比較基準は最初の条件付き・整合性確認済み完了実行であり、最良候補の推薦ではない。", "",
        "| 実行 | 実行状態 | 比較判定 | 観測最良距離 | 距離差 | ソケット異常面差 | 除外理由 |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["rows"]:
        def number(key):
            value = row[key]
            return "—" if value is None else f"{value:.7f}" if isinstance(value, float) else str(value)
        lines.append(
            f"| {row['run_id']} | {row['run_status']} | {LABELS[row['comparison_status']]} | "
            f"{number('best_sampled_max')} | {number('sampled_max_delta_from_anchor')} | "
            f"{number('socket_faces_delta_from_anchor')} | {REASONS.get(row['exclusion_reason'], '—')} |"
        )
    lines.extend([
        "", "## 人が確認すること", "",
        "- 対象外の経過は比較順位や成功の根拠に使わない。失敗前の目標内観測も実行成功ではない。",
        "- 条件不一致は、プロトコル・コードSHA・Blender版・基準/初期GLB SHA・座標スケール・初期観測・予算を確認する。",
        "- 距離差が小さくても異常面数が食い違えば混在扱いとし、全体の改善を断定しない。",
        "- 証拠は自己申告を含み、SHA一致も真正性を認証しない。ローカルの実行記録を確認する。",
        "- CBDK合成試験限定。実アドオン因果、最適設定、厳密Hausdorff距離や完全幾何一致を証明しない。",
        "- 自動採用・再実行・再開はしない。", "",
    ])
    return "\n".join(lines)


def write_run_comparison(report, directory):
    markdown = render_run_comparison(report)
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Expected local comparison directory")
    paths = (root / "synthetic_run_comparison.json", root / "synthetic_run_comparison.md")
    if any(p.exists() or p.is_symlink() for p in paths):
        raise FileExistsError("Comparison must not overwrite")
    with paths[1].open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    with paths[0].open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only synthetic run comparison")
    parser.add_argument("--run", action="append", required=True, help="Local terminal/checkpoint JSON")
    parser.add_argument("--output", required=True, help="New ignored local output directory")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).absolute()
    try:
        if not 2 <= len(args.run) <= MAX_RUNS:
            raise ValueError("Expected 2..16 reports")
        if (output.exists() or output.is_symlink() or output.parent.resolve() not in
                ((root / "reports/latest").resolve(), (root / "reports/ci").resolve())):
            raise ValueError("Expected a fresh ignored report folder")
        reviews = []
        for path in args.run:
            try:
                reviews.append(read_run_review(path))
            except (OSError, ValueError, RecursionError):
                reviews.append(None)
        report = compare_run_reviews(reviews)
        output.mkdir(parents=True, exist_ok=False)
        write_run_comparison(report, output)
    except (OSError, ValueError):
        parser.exit(2, "Synthetic comparison failed; no comparison accepted\n")
    print(f"Synthetic comparison: eligible={report['eligible_runs']}, excluded={report['excluded_runs']}")
    return 0 if report["comparison_available"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
