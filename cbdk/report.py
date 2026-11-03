"""Machine-readable and Markdown research reports."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def write_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: str | Path, catalog: dict, results: dict) -> dict:
    counts = Counter(x["category"] for x in catalog["symbols"])
    parsed = sum(f["status"] == "parsed" for f in catalog["files"])
    metrics = {"files": len(catalog["files"]), "parsed": parsed, "parse_errors": len(catalog["files"])-parsed,
               "symbols": len(catalog["symbols"]), "by_category": dict(counts),
               "exact_groups": len(results["exact_groups"]),
               "exact_redundant_occurrences": sum(len(g["symbols"])-1 for g in results["exact_groups"]),
               "shape_groups": len(results["shape_groups"]),
               "near_candidate_pairs": results["near_total"]}
    lines = ["# CBDK: 初期ソース解析レポート", "", "> 静的解析のみ。動作・権利・品質の検証を意味しません。", "",
             "## 件数", "", f"- ソースファイル: {metrics['files']} (解析成功 {parsed} / 失敗 {metrics['parse_errors']})",
             f"- 関数・クラス・メソッドの候補: {metrics['symbols']}", f"- AST一致の重複グループ: {metrics['exact_groups']}（余剰出現 {metrics['exact_redundant_occurrences']}件。削除可能数ではない）",
             f"- 構造のみ一致のグループ: {metrics['shape_groups']}", f"- 近似重複候補ペア: {metrics['near_candidate_pairs']}", "",
             "## 分類", "", "| 分類 | 数 |", "|---|---:|"]
    lines += [f"| {category} | {count} |" for category, count in counts.most_common()]
    lines += ["", "## 取り込んだソース", "", "| ファイル | 解析 | 関数・クラス・メソッド |", "|---|---|---:|"]
    filecounts = Counter(x["source"] for x in catalog["symbols"])
    lines += [f"| {x['name']} | {x['status']} | {filecounts[x['path']]} |" for x in catalog["files"]]
    lines += ["", "## AST一致の重複グループ (最大20件)", ""]
    if results["exact_groups"]:
        for idx, group in enumerate(results["exact_groups"][:20], 1):
            names = ", ".join(f"`{s['source']}::{s['qualname']}`" for s in group["symbols"])
            lines.append(f"{idx}. {names}")
    else:
        lines.append("現時点で検出なし")
    lines += ["", "## 近似重複候補 (最大20件)", "", "> スコアは構造上の類似度であり、同じ動作である確率ではありません。", ""]
    if results["near_candidates"]:
        for idx, cand in enumerate(results["near_candidates"][:20], 1):
            lines.append(f"{idx}. {cand['left']} ⇔ {cand['right']} (スコア {cand['score']:.3f})")
    else:
        lines.append("閾値を超える候補なし")
    lines += ["", "## 次の検証", "", "1. 重複候補の意味・引数・副作用を人間とAIで精査",
             "2. 候補を独立モジュール化し、依存関係を明示",
             "3. Blender本体でのテストと対応バージョン判定",
             "4. 採用が確定した部品に固定IDを割り当てる", ""]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return metrics
