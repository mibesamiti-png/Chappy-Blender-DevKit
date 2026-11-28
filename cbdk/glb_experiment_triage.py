"""NEXT-008/009: private, read-only focus and ambiguity review for bound runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .glb_debug_focus import build_debug_focus, validate_debug_focus
from .glb_property_map import ROOT, _read_json
from .glb_synthetic_run_review import ACTIONS
from .glb_visual_experiment_review import render_visual_experiment_review
from .glb_visual_review_markdown import markdown_destination

KIND = "cbdk_glb_experiment_triage_v1"
FLAGS = {"source_executed": False, "selects_property": False,
         "causality_proven": False, "applies_changes": False,
         "recommends_parameter_values": False, "automatically_runs_next_trial": False}


def _derive(focus, linked):
    validate_debug_focus(focus)
    render_visual_experiment_review(linked)
    if focus["baseline_review_sha256"] != linked["baseline_review_sha256"]:
        raise ValueError("Focus and AST experiment have different baselines")
    # Also reconcile sanitized observations, rather than trusting digest equality
    # alone. Saved summaries cannot authenticate the original GLB or source.
    parts = {r["part_id"]: r for r in focus["observations"]["candidate"]}
    for row in linked["static_candidates"]:
        observed = parts.get(row["part_id"])
        if observed is None or any(observed[k] != row[v] for k, v in (
                ("medium", "medium_faces"), ("high", "high_faces"), ("boundary_edges", "boundary_edges"))):
            raise ValueError("Focus and AST observations disagree")
    candidates = []
    for row in linked["static_candidates"]:
        for hint in row["candidates"]:
            declarations = hint["declarations"]
            locations = {(d["source_label"], d["class_name"], d["line"]) for d in declarations}
            if len(locations) != len(declarations):
                raise ValueError("Repeated declaration cannot establish candidate identity")
            ambiguous = len(locations) > 1
            candidates.append({"part_id": row["part_id"], "family": hint["family"],
                               "declaration_count": len(locations),
                               "status": "multiple_static_declarations" if ambiguous else "single_unverified_declaration",
                               "action": "resolve_declaration_identity" if ambiguous else "verify_runtime_binding_separately",
                               "syntax_counts_are_family_aggregates": True,
                               "possible_references": hint["possible_references"],
                               "possible_geometry_paths": hint["possible_geometry_paths"],
                               "selected_declaration": None, "effect_verified": False})
    experiment = linked["experiment_review"]
    checkpoint = experiment["checkpoint"]
    distance = linked["baseline_metric"]["sampled_max_distance"]
    faces = linked["baseline_metric"]["socket_sampled_affected_faces"]
    trials = []
    for step in checkpoint["steps"]:
        trials.append({"trial_id": step["trial_id"],
                       "global_sampled_max_change_from_previous": round(step["sampled_max"] - distance, 7),
                       "candidate_socket_face_change_from_previous": step["socket_affected_faces"] - faces,
                       "accepted_as_measured_progress": step["accepted_as_measured_progress"],
                       "sampled_target_met": step["target_met"]})
        distance, faces = step["sampled_max"], step["socket_affected_faces"]
    return {"kind": KIND, "schema_version": 1, "status": "review_only",
            "focus_review": focus, "linked_review": linked,
            "candidate_reviews": candidates, "trial_observations": trials,
            "experiment_status": experiment["status"],
            "next_action": "review_failed_or_incomplete_prefix" if not experiment["run_completed"]
                           else "review_observations_without_assigning_property_cause",
            "distance_metric_scope": "global_bidirectional_samples_not_part_local_distance",
            "private_local_only": True, "safety": dict(FLAGS)}


def build_experiment_triage(visual, linked):
    return _derive(build_debug_focus(visual), linked)


def render_experiment_triage(report):
    try:
        expected = _derive(report["focus_review"], report["linked_review"])
        if json.dumps(report, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
            raise ValueError("Forged experiment triage")
    except (KeyError, TypeError, RecursionError, OverflowError) as exc:
        raise ValueError("Invalid experiment triage") from exc
    linked = report["linked_review"]
    run = linked["experiment_review"]
    checkpoint = run["checkpoint"]
    declarations = {(row["part_id"], hint["family"]): hint
                    for row in linked["static_candidates"] for hint in row["candidates"]}
    links = {(row["part_id"], row["candidate_family"]): row
             for row in linked["candidate_links"]}
    by_part = {}
    for row in report["candidate_reviews"]:
        by_part.setdefault(row["part_id"], []).append(row)
    lines = ["# 形状差分・設定候補・次の実験レビュー（非公開）", "",
             "測定済み三角面の割合による調査順です。面積・全域精度・部品同一性を示しません。",
             "参照側だけの差分も残します。対応候補と穴の位置は未確定です。",
             "宣言位置を含むローカル専用のレビューです。公開・実行・設定変更はしません。", "",
             "## 調査優先部品（側とIDを一緒に確認）", ""]
    for rank, row in enumerate(report["focus_review"]["focus"], 1):
        side, part = row["side"], row["part_id"]
        lines.append(f"### {rank}. {side} / {part}")
        lines.append(f"- 観測: 黄{row['medium']}・赤{row['high']} / {row['triangle_count']}面、"
                     f"観測割合{row['observed_affected_fraction']:.4f}、境界{row['boundary_edges']}本。"
                     f"根拠: {', '.join(row['reasons'])}。")
        lines.append(f"- 対応候補: {row['tentative_peer'] or '未確認'}（反対側、同一性未証明）。")
        if side == "reference":
            lines.append("- 次の確認: 参照側観測と対応候補を確認する。生成側の同名IDに設定を転用しない。")
            continue
        candidates = by_part.get(part, [])
        if not candidates:
            lines.append("- 設定候補: 一致宣言なし。設定不在・原因不存在とは限らない。")
        for candidate in candidates:
            key = (part, candidate["family"])
            hint = declarations[key]
            link = links[key]
            lines.append(f"- 設定候補 `{candidate['family']}`: 宣言{candidate['declaration_count']}件、"
                         f"{candidate['status']}。実プロパティ因果は未証明。")
            for decl in hint["declarations"]:
                lines.append(f"  - 宣言位置: `{decl['source_label']}` / `{decl['class_name']}` / {decl['line']}行。")
            lines.append(f"  - 構文上の参照{candidate['possible_references']}件、"
                         f"形状経路{candidate['possible_geometry_paths']}件（候補名全体の集計）。")
            lines.append("  - 次の確認: 同名宣言の実体を区別する。"
                         if candidate["declaration_count"] > 1 else
                         "  - 次の確認: 実行時に登録・参照される設定か別途確認する。")
            lines.append("  - 合成操作 socket_diameter: 人の役割ラベルと名称による照合候補のみ。"
                         if link["synthetic_control_id"] else
                         "  - 合成操作との対応: 未確認。試行結果をこの設定の効果に転用しない。")
        lines.append("")
    if not report["focus_review"]["focus"]:
        lines.append("- 調査対象の差分観測なし（完全一致の証明ではない）。")
    if not report["candidate_reviews"]:
        lines.append("- 一致宣言なし。名前の不一致を設定不在や原因不存在と解釈しない。")
    lines += ["", "## 合成実験の観測と停止理由", "",
              f"実行状態: {run['status']} / 工程: {run['stage']}。",
              f"検証済み試行: {run['validated_attempts']}/{run['attempt_budget']}、未検証枠: {run['unvalidated_attempts']}。",
              f"処理対象: {run['active_trial_id'] or 'なし'} / 失敗区分: {run['failure_code'] or 'なし'}。",
              f"停止理由（観測履歴）: {checkpoint['stop_reason']}。",
              f"観測上の最良: {checkpoint['best_observed_trial_id']} / 合成目標内: {checkpoint['measured_feasible_trial_id'] or '未確認'}。",
              "距離は全体の双方向サンプル最大であり、特定部品の距離ではありません。",
              "変化量は直前の検証済み試行との差。進捗判定は採用済み最良値に対する既存判定です。"]
    for row, step in zip(report["trial_observations"], checkpoint["steps"]):
        progress = "観測進捗あり" if row["accepted_as_measured_progress"] else "観測進捗として棄却"
        target = "目標内" if row["sampled_target_met"] else "目標外"
        lines.append(f"- {row['trial_id']}: 全体距離 {step['sampled_max']:.7f} "
                     f"(変化{row['global_sampled_max_change_from_previous']:+.7f})、"
                     f"生成側socket面数 {step['socket_affected_faces']} "
                     f"(変化{row['candidate_socket_face_change_from_previous']:+d})。"
                     f"{progress} / {target} / {step['progress_reason']}。")
    if not checkpoint["steps"]:
        lines.append("- 検証済み試行なし。初期観測以外は未測定。")
    lines += ["", "## 次の確認・再試行の前提", ""]
    if run["status"] == "failed":
        lines.append(f"- {ACTIONS[run['failure_code']]} 未検証の試行結果は採用しない。")
    elif not run["run_completed"]:
        lines.append("- 終了証拠を確認する。記録から稼働中か正常終了かを判定できない。")
    else:
        lines.append("- 試行予算は完了。目標内候補と棄却理由を人が確認する。")
    lines += ["- 再試行する場合は、対象・測定条件・入力整合性を確認し、新しい出力先を用意する。",
              "- 実ユーザーGLB・元アドオンの使用や実行は別の明示許可が必要。実設定値の推薦はしない。",
              "- 自動実行・自動再開・設定値適用なし。保存された集計の一致は真正性を証明しない。",
              "失敗/未完了prefixや合成目標内の観測を、実行完了・完全一致・因果証明に昇格しない。"]
    return "\n".join(lines) + "\n"


def write_experiment_triage(report, output, *, root=ROOT):
    text = render_experiment_triage(report)
    relative = Path(output)
    # Reuse the established private Markdown containment/collision preflight.
    if relative.suffix != ".json":
        raise ValueError("Expected private JSON output")
    root = Path(root).resolve()
    md = markdown_destination(relative.with_suffix(".md"), root=root)
    target = root / relative
    if (target.exists() or target.is_symlink()
            or not target.resolve().is_relative_to(root / "reports/latest")):
        raise ValueError("Expected fresh private JSON output")
    body = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(body.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Experiment triage exceeds size limit")
    target.parent.mkdir(parents=True, exist_ok=True)
    with md.open("x", encoding="utf-8") as stream:
        stream.write(text)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(body)
    return target, md


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-review", required=True)
    parser.add_argument("--linked-review", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = build_experiment_triage(_read_json(args.visual_review), _read_json(args.linked_review))
        write_experiment_triage(report, args.output)
    except (ValueError, OSError, RecursionError):
        parser.exit(2, "Private experiment triage failed; no evidence accepted\n")
    print(json.dumps({"kind": KIND, "status": "review_only",
                      "focus_count": len(report["focus_review"]["focus"]),
                      "ambiguous_family_count": sum(r["declaration_count"] > 1 for r in report["candidate_reviews"]),
                      "cause_proven": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
