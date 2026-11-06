"""GLB-021 human-readable review sheet; private local Markdown only.

The Markdown contains candidate property names/line numbers and is never
public-safe. It does not run or modify addon code and does not prove causes.
"""
from __future__ import annotations

from pathlib import Path
import re

from .glb_property_map import PropertyMappingError, ROOT

_PART = re.compile(r"part_0[0-6][0-9]\Z")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]{0,127}\Z")
_LABEL = re.compile(r"source_[1-9][0-9]{0,2}\.py\Z")


def markdown_destination(output: str | Path, *, root: Path = ROOT) -> Path:
    relative = Path(output)
    if (relative.is_absolute() or relative.suffix != ".md"
            or len(relative.parts) < 3
            or relative.parts[:2] != ("reports", "latest")
            or ".." in relative.parts):
        raise PropertyMappingError("Review Markdown must stay in reports/latest/")
    root = root.resolve()
    target = root / relative
    if not target.resolve().is_relative_to(root / "reports" / "latest"):
        raise PropertyMappingError("Review path escapes ignored local directory")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Review Markdown already exists; choose another filename")
    return target


def _number(value):
    if type(value) is not int or value < 0:
        raise PropertyMappingError("Invalid observed count in review")
    return value


def render_review_markdown(report: dict) -> str:
    """Only present bounded, validated fields, never source code or default values."""
    if (not isinstance(report, dict)
            or report.get("kind") != "cbdk_glb_property_mapping"
            or report.get("status") != "review_only"
            or report.get("link_kind") != "glb020_visual_diff_to_ast_property_candidates_v1"
            or report.get("cause_and_effect_proven") is not False
            or report.get("parameter_values_inferred") is not False
            or report.get("cross_file_part_identity_proven") is not False
            or report.get("input_glb_or_addon_executed") is not False):
        raise PropertyMappingError("Only unapproved GLB-021 review results are renderable")
    safety = report.get("safety")
    if (not isinstance(safety, dict)
            or any(safety.get(k) is not False
                   for k in ("source_executed", "source_modified", "applies_parameters"))):
        raise PropertyMappingError("Unsafe review flags")
    rows = report.get("recommendations")
    if (not isinstance(rows, list) or len(rows) > 64
            or type(report.get("recommendation_count")) is not int
            or len(rows) != report["recommendation_count"]):
        raise PropertyMappingError("Invalid review count")
    q = chr(96)
    lines = [
        "# GLB-021 設定候補レビュー（非公開・未承認）",
        "",
        "**観測された差分は原因の証明ではありません。宣言名の一致も修正値の証明ではありません。**",
        "",
        "- この文書はローカル専用です。設定候補・宣言位置を含むためGitHub/Notionへ公開しないでください。",
        "- 元アドオンの実行・変更・パラメータ適用・部品の本人確認は実施していません。",
        "- サンプル差分が見つからなくても全形状が正しい証明にはなりません。",
        "",
        f"**レビューが必要な生成側の部品: {len(rows)}件**",
        "",
    ]
    if not rows:
        lines.extend([
            "制限された測定ではレビュー対象の差分が観測されませんでした。",
            "小穴や内部形状など未測定の問題が存在しないという意味ではありません。",
            "",
        ])
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PropertyMappingError("Invalid review row")
        part = row.get("target")
        obs = row.get("visual_observation")
        if (not isinstance(part, str) or not _PART.fullmatch(part)
                or not 1 <= int(part[5:]) <= 64 or part in seen
                or not isinstance(obs, dict)
                or obs.get("candidate_part_id") != part
                or obs.get("reference_candidate_identity_proven") is not False
                or obs.get("geometry_effect_verified") is not False
                or obs.get("recommended_parameter_value") is not None
                or obs.get("requires_human_review") is not True
                or row.get("candidate_cause_verified") is not False):
            raise PropertyMappingError("Unverified observation cannot be presented")
        seen.add(part)
        yellow = _number(obs.get("observed_medium_faces"))
        red = _number(obs.get("observed_high_faces"))
        edges = _number(obs.get("observed_boundary_edges"))
        if yellow + red + edges == 0:
            raise PropertyMappingError("Cannot present observation without a difference")
        role = obs.get("manual_role_label")
        if role not in (None, "socket", "ball", "shaft", "hinge"):
            raise PropertyMappingError("Invalid manual role")
        matched = obs.get("tentative_reference_part_id")
        if matched is not None and (not isinstance(matched, str)
                                    or not _PART.fullmatch(matched) or matched == "part_000"):
            raise PropertyMappingError("Invalid tentative part match")
        hints = row.get("exact_name_matches")
        if not isinstance(hints, list) or len(hints) > 64:
            raise PropertyMappingError("Invalid AST hint list")
        lines.extend([
            f"## 生成側 {q}{part}{q}",
            "",
            f"- **観測**: 黄 {yellow}面／赤 {red}面／境界辺 {edges}本",
            f"- **役割**: {role}（人の未確認ラベル）" if role else
                "- **役割**: 未指定・汎用設定名で照合",
            f"- **参照側候補**: {q}{matched}{q}（本人確認なし）" if matched else
                "- **参照側候補**: 未確定",
            "",
            "### AST上の候補",
            "",
        ])
        if not hints:
            lines.extend([
                "一致した宣言がありません。未実装や修復不能の証拠ではありません。",
                "別名・別ファイル・動的登録・計算で導出される設定を人が確認してください。",
                "",
            ])
        for hint in hints:
            if not isinstance(hint, dict):
                raise PropertyMappingError("Invalid AST match")
            name = hint.get("candidate_family")
            decls = hint.get("declarations")
            uses = hint.get("possible_code_references")
            flows = hint.get("possible_geometry_dataflow")
            if (not isinstance(name, str) or not _IDENTIFIER.fullmatch(name)
                    or hint.get("match") != "exact_declaration_name_only"
                    or hint.get("requires_human_review") is not True
                    or not isinstance(decls, list) or not 1 <= len(decls) <= 16
                    or not isinstance(uses, dict) or not isinstance(flows, dict)
                    or uses.get("receiver_binding_verified") is not False
                    or flows.get("geometry_effect_verified") is not False):
                raise PropertyMappingError("Unsafe AST mapping fields")
            use_count = _number(uses.get("possible_reference_count"))
            flow_count = _number(flows.get("possible_path_count"))
            lines.extend([
                f"**{q}{name}{q} — 宣言名の一致のみ**",
                "",
                f"- 静的な属性参照 {use_count}件、構文上の形状処理経路 {flow_count}件",
                "- 実行時の登録・受け手・因果関係・形状への実際の効果は未確認",
            ])
            for decl in decls:
                if not isinstance(decl, dict):
                    raise PropertyMappingError("Invalid declaration")
                label, cls, line = (decl.get("source_label"),
                                    decl.get("class_name"), decl.get("line"))
                if (not isinstance(label, str) or not _LABEL.fullmatch(label)
                        or not isinstance(cls, str) or not cls.isidentifier()
                        or len(cls) > 128
                        or type(line) is not int or not 1 <= line <= 1000000
                        or decl.get("registered_in_blender") != "not_checked"
                        or decl.get("controls_geometry") != "not_checked"):
                    raise PropertyMappingError("Invalid declaration location")
                lines.append(f"- 宣言候補: {q}{label}{q} / {q}{cls}{q} / {line}行")
            lines.append("")
        lines.extend([
            "### 人による確認項目",
            "",
            "- [ ] 参照側と生成側が本当に対応する部品か確認する",
            "- [ ] 設定がBlenderに登録され、生成処理で参照されているか確認する",
            "- [ ] 開口・配置・形状・ブーリアン・書き出し等の他の原因を検討する",
            "- [ ] 必要なら原本を守る許可済み合成コピーで変更を検証する",
            "- [ ] 再生成したモデルの差分を改めて計測し、改善を確認する",
            "",
            "**結論: 原因未確定・値の推奨なし・設定変更なし。**",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def write_private_review_markdown(report: dict, output: str | Path,
                                  *, root: Path = ROOT) -> Path:
    target = markdown_destination(output, root=root)
    content = render_review_markdown(report)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return target
