"""Small bilingual search over static catalog entries. No external services."""
from __future__ import annotations

import re

ALIASES = {
    "選択": "select selection selected", "頂点": "vertex vert vertices", "面": "face polygon", "辺": "edge",
    "中心": "center centroid median", "法線": "normal", "回転": "rotate rotation", "座標": "coordinate transform",
    "出力": "export write", "保存": "save write", "ファイル": "file path", "メッシュ": "mesh bmesh",
    "コレクション": "collection", "複製": "duplicate copy", "統合": "merge join", "パネル": "panel layout ui",
    "設定": "settings property preset", "名前": "name sanitize", "スライサー": "slicer bambu stl",
}


def tokenize(s: str) -> set[str]:
    t = s.lower()
    for jp, en in ALIASES.items():
        if jp in t:
            t += " " + en
    return set(re.findall(r"[a-z0-9]+|[一-龯ぁ-んァ-ンー]+", t))


def search(catalog: dict, query: str, *, limit: int = 20) -> list[dict]:
    q = tokenize(query)
    if not q:
        return []
    results = []
    for part in catalog.get("symbols", []):
        name = tokenize(part["qualname"].replace("_", " "))
        text = tokenize(part.get("doc", "") + " " + part.get("category", "") + " " + " ".join(part.get("calls", [])))
        n_hit = len(name & q)
        t_hit = len(text & q)
        score = 4*n_hit + t_hit
        if score:
            results.append({"score": score, "id": part["id"], "name": part["qualname"],
                            "source": part["source_name"], "category": part["category"],
                            "line": part["line"], "status": part["verification"]})
    return sorted(results, key=lambda x: (-x["score"], x["name"], x["source"]))[:limit]
