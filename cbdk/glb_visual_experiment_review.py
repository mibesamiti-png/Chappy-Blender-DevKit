"""Private AST-to-synthetic-experiment review, bound to the measured baseline.

Only AST parsing and validated aggregate JSON are used. A matching property
name/manual role is NOT proof that the property controlled the experiment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from .glb_property_map import PropertyMappingError, ROOT, _read_json
from .glb_synthetic_conditions import aggregate_review_digest
from .glb_synthetic_progress import _metric
from .glb_synthetic_run_review import read_run_review, render_run_review
from .glb_visual_property_review import (
    ALLOWED_ROLES, GENERIC_FAMILIES, ROLE_FAMILIES, build_visual_property_review,
    parse_role_labels,
)
from .glb_visual_review_markdown import markdown_destination, render_review_markdown

KIND = "cbdk_glb021_bound_synthetic_experiment_review_v1"
FLAGS = {
    "source_executed": False, "source_modified": False,
    "applies_parameters": False, "property_controls_generator_verified": False,
    "real_addon_causality_proven": False, "true_part_identity_proven": False,
    "recommends_parameter_values": False, "authenticates_evidence": False,
}


def _static_summary(mapped):
    render_review_markdown(mapped)
    rows = []
    for row in mapped["recommendations"]:
        obs = row["visual_observation"]
        candidates = []
        for hint in row["exact_name_matches"]:
            candidates.append({
                "family": hint["candidate_family"],
                "declarations": [{key: decl[key] for key in ("source_label", "class_name", "line")}
                                 for decl in hint["declarations"]],
                "possible_references": hint["possible_code_references"]["possible_reference_count"],
                "possible_geometry_paths": hint["possible_geometry_dataflow"]["possible_path_count"],
            })
        rows.append({
            "part_id": row["target"], "manual_role": obs["manual_role_label"],
            "medium_faces": obs["observed_medium_faces"],
            "high_faces": obs["observed_high_faces"],
            "boundary_edges": obs["observed_boundary_edges"],
            "candidates": candidates,
        })
    return rows


def _validate_static(rows):
    if not isinstance(rows, list) or len(rows) > 3:
        raise ValueError("Invalid bounded synthetic AST summary")
    parts = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {
                "part_id", "manual_role", "medium_faces", "high_faces", "boundary_edges", "candidates"}
                or row["part_id"] not in ("part_001", "part_002", "part_003")
                or row["part_id"] in parts or row["manual_role"] not in ALLOWED_ROLES | {None}):
            raise ValueError("Invalid synthetic part summary")
        parts.add(row["part_id"])
        if any(type(row[k]) is not int or not 0 <= row[k] <= 512
               for k in ("medium_faces", "high_faces", "boundary_edges")):
            raise ValueError("Invalid part observations")
        candidates = row["candidates"]
        families = ROLE_FAMILIES[row["manual_role"]] if row["manual_role"] else GENERIC_FAMILIES
        if not isinstance(candidates, list) or len(candidates) > len(families):
            raise ValueError("Invalid candidate count")
        seen = set()
        for candidate in candidates:
            if (not isinstance(candidate, dict) or set(candidate) != {
                    "family", "declarations", "possible_references", "possible_geometry_paths"}
                    or candidate["family"] not in families or candidate["family"] in seen):
                raise ValueError("Invalid candidate family")
            seen.add(candidate["family"])
            if any(type(candidate[k]) is not int or not 0 <= candidate[k] <= 1000000
                   for k in ("possible_references", "possible_geometry_paths")):
                raise ValueError("Invalid static counts")
            declarations = candidate["declarations"]
            if not isinstance(declarations, list) or not 1 <= len(declarations) <= 16:
                raise ValueError("Invalid declarations")
            for decl in declarations:
                if (not isinstance(decl, dict) or set(decl) != {"source_label", "class_name", "line"}
                        or not isinstance(decl["source_label"], str)
                        or re.fullmatch(r"source_[1-9][0-9]{0,2}\.py", decl["source_label"]) is None
                        or not isinstance(decl["class_name"], str) or not decl["class_name"].isidentifier()
                        or len(decl["class_name"]) > 128
                        or type(decl["line"]) is not int or not 1 <= decl["line"] <= 1000000):
                    raise ValueError("Invalid anonymous declaration location")


def _bound_summary(rows, metric, digest, experiment):
    _validate_static(rows)
    render_run_review(experiment)
    conditions = experiment.get("conditions")
    if (not isinstance(conditions, dict) or conditions.get("baseline_review_sha256") != digest
            or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
        raise ValueError("Experiment lacks matching aggregate baseline binding")
    if experiment["input_integrity"] != "verified" or experiment["checkpoint"] is None:
        raise ValueError("Unverified experiment inputs cannot be linked")
    if (not isinstance(metric, dict) or set(metric) != {
            "sampled_max_distance", "combined_aabb_diagonal", "socket_sampled_affected_faces",
            "other_parts_sampled_affected_faces"}
            or type(metric["sampled_max_distance"]) not in (int, float)
            or metric["sampled_max_distance"] != conditions["initial_sampled_max"]
            or type(metric["combined_aabb_diagonal"]) not in (int, float)
            or metric["combined_aabb_diagonal"] != conditions["combined_aabb_diagonal"]
            or type(metric["socket_sampled_affected_faces"]) is not int
            or metric["socket_sampled_affected_faces"] != conditions["initial_socket_affected_faces"]
            or type(metric["other_parts_sampled_affected_faces"]) is not int
            or metric["other_parts_sampled_affected_faces"] != 0):
        raise ValueError("AST review baseline disagrees with experiment observations")
    socket = next((row for row in rows if row["part_id"] == "part_003"), None)
    if (len(rows) != 1 or socket is None or socket["boundary_edges"] != 0
            or socket["medium_faces"] + socket["high_faces"] != metric["socket_sampled_affected_faces"]):
        raise ValueError("Missing or inconsistent faulty synthetic socket observation")
    for row in rows:
        if row["part_id"] != "part_003" and row["medium_faces"] + row["high_faces"] != 0:
            raise ValueError("Baseline modified an unrelated synthetic part")
    links = []
    for row in rows:
        for candidate in row["candidates"]:
            linked = (row["part_id"] == "part_003" and row["manual_role"] == "socket"
                      and candidate["family"] == "socket_opening_diameter")
            links.append({
                "part_id": row["part_id"], "candidate_family": candidate["family"],
                "synthetic_control_id": "socket_diameter" if linked else None,
                "basis": "manual_role_and_exact_name_only" if linked else "no_control_mapping",
                "property_effect_verified": False, "recommended_parameter_value": None,
            })
    return {
        "kind": KIND, "schema_version": 1, "status": "review_only",
        "baseline_review_sha256": digest, "baseline_metric": metric,
        "static_candidates": rows, "experiment_review": experiment,
        "candidate_links": links,
        "linked_candidate_count": sum(row["synthetic_control_id"] is not None for row in links),
        "private_local_only": True, "safety": dict(FLAGS),
    }


def build_visual_experiment_review(visual, sources, experiment, *, roles=None):
    """Check experiment binding BEFORE reading explicitly selected Python."""
    render_run_review(experiment)
    metric = _metric(visual)
    digest = aggregate_review_digest(visual)
    conditions = experiment.get("conditions", {})
    if (conditions.get("baseline_review_sha256") != digest
            or experiment["input_integrity"] != "verified"):
        raise PropertyMappingError("Use the matching bound synthetic baseline and verified run")
    mapped = build_visual_property_review(visual, sources, roles=roles)
    return _bound_summary(_static_summary(mapped), metric, digest, experiment)


def render_visual_experiment_review(report):
    try:
        expected = _bound_summary(report["static_candidates"], report["baseline_metric"],
                                  report["baseline_review_sha256"], report["experiment_review"])
        if json.dumps(report, sort_keys=True, allow_nan=False) != json.dumps(
            expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError("Forged linked review")
    except (KeyError, TypeError, RecursionError, OverflowError) as exc:
        raise ValueError("Invalid linked review") from exc
    lines = [
        "# GLB-021 設定候補と合成反復のレビュー（非公開）", "",
        "**観測・AST構文候補・合成操作の対応候補を分離します。実プロパティの因果は未証明です。**",
        "この文書は候補名と宣言位置を含むためローカル専用です。GitHub/Notionへ公開しないでください。", "",
        "初期GLB-020集計のSHAは実験に記録された集計と一致しています。"
        "SHA一致は証拠の真正性や実ユーザーの部品同一性を認証しません。", "",
        "## AST上の候補と合成操作の照合", "",
    ]
    links = {(row["part_id"], row["candidate_family"]): row for row in report["candidate_links"]}
    for row in report["static_candidates"]:
        lines.append(f"### {row['part_id']}（人の役割ラベル：{row['manual_role'] or '未指定'}）")
        for candidate in row["candidates"]:
            link = links[row["part_id"], candidate["family"]]
            lines += ["", f"- 候補 `{candidate['family']}`：静的参照 {candidate['possible_references']}件、"
                      f"構文上の形状経路 {candidate['possible_geometry_paths']}件。"]
            for decl in candidate["declarations"]:
                lines.append(f"- 宣言：`{decl['source_label']}` / `{decl['class_name']}` / {decl['line']}行。")
            lines.append("- 合成操作：socket_diameterとの人手確認用の名称対応候補。実プロパティの効果は未確認。"
                         if link["synthetic_control_id"] else "- 合成操作との対応は未確認。この候補の効果を実験結果から推定しない。")
    lines += ["", "## 人が確認すること", "",
              "- [ ] 候補宣言・参照が同じ実インスタンスの設定を指すか。",
              "- [ ] 合成生成器の操作と対象アドオンの設定が本当に対応するか。",
              "- [ ] 許可が必要な実データ/実行は別に確認する。値を自動適用しない。",
              "- [ ] 失敗・未完了の実験を成功と読まない。合成値は実モデルの推奨値ではない。", "",
              "## 結び付けた合成実験の観測（対象アドオンは実行していません）", "",
              render_run_review(report["experiment_review"])]
    return "\n".join(lines)


def write_linked_review(report, output, *, root=ROOT):
    markdown = render_visual_experiment_review(report)
    relative = Path(output)
    if (relative.is_absolute() or relative.suffix != ".json" or len(relative.parts) < 3
            or relative.parts[:2] != ("reports", "latest") or ".." in relative.parts):
        raise ValueError("Linked review must stay in ignored reports/latest")
    root = Path(root).resolve()
    target = root / relative
    md = markdown_destination(relative.with_suffix(".md"), root=root)
    if (not target.resolve().is_relative_to(root / "reports/latest")
            or target.exists() or target.is_symlink()):
        raise ValueError("Expected fresh private JSON output")
    body = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(body.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Linked review too large")
    target.parent.mkdir(parents=True, exist_ok=True)
    with md.open("x", encoding="utf-8") as handle:
        handle.write(markdown)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(body)
    return target, md


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private AST-only candidate and bound synthetic experiment review")
    parser.add_argument("--visual-review", required=True)
    parser.add_argument("--run-review", required=True)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--role", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = build_visual_experiment_review(
            _read_json(args.visual_review), args.source, read_run_review(args.run_review),
            roles=parse_role_labels(args.role))
        write_linked_review(report, args.output, root=ROOT)
    except (OSError, ValueError, RecursionError):
        parser.exit(2, "Linked private review failed; no evidence accepted\n")
    print(json.dumps({"kind": KIND, "status": "review_only",
                      "linked_candidate_count": report["linked_candidate_count"],
                      "source_executed": False, "cause_proven": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
