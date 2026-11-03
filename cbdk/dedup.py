"""Conservative duplicate detection; suggestions never trigger automatic merging."""
from __future__ import annotations

import difflib
from collections import defaultdict


def _ratio_hist(a: dict, b: dict) -> float:
    keys = a.keys() | b.keys()
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    overlap = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    return overlap / union if union else 1.0


def _jaccard(a, b) -> float:
    x, y = set(a), set(b)
    return len(x & y) / len(x | y) if x or y else 1.0


def _name_tokens(s: str) -> list[str]:
    return [w for w in s.lower().replace(".", "_").split("_") if w]


def duplicates(catalog: dict, *, threshold: float = .82, limit: int = 200) -> dict:
    items = catalog.get("symbols", [])
    exact, shape = defaultdict(list), defaultdict(list)
    for item in items:
        exact[(item["kind"], item["exact_ast_sha256"])].append(item)
        shape[(item["kind"], item["shape_sha256"])].append(item)

    def summarize(groups, typ):
        return [{"kind": typ, "symbols": [{"id": x["id"], "source": x["source_name"], "qualname": x["qualname"]} for x in group]}
                for group in groups.values() if len(group) > 1]

    exact_groups = summarize(exact, "same_ast_except_name_docstring")
    shape_groups = []
    # Shape groups whose members are not already identical in exact AST.
    for group in shape.values():
        if len(group) > 1 and len({x["exact_ast_sha256"] for x in group}) > 1:
            shape_groups.append({"kind": "same_ast_shape_identifiers_constants_ignored",
                                 "symbols": [{"id": x["id"], "source": x["source_name"], "qualname": x["qualname"]} for x in group]})

    # Candidate pairs: compare only comparable-size symbols of the same kind.
    # Top results are suggestions, not evidence of behavioral equivalence.
    by_kind = defaultdict(list)
    for item in items:
        if item["node_count"] >= 10:
            by_kind[item["kind"]].append(item)
    near = []
    for kind, group in by_kind.items():
        group.sort(key=lambda x: x["node_count"])
        for i, a in enumerate(group):
            for b in group[i+1:]:
                if b["node_count"] > a["node_count"] * 1.28:
                    break
                if a["exact_ast_sha256"] == b["exact_ast_sha256"] or a["shape_sha256"] == b["shape_sha256"]:
                    continue
                if a["source"] == b["source"] and a["qualname"] == b["qualname"]:
                    continue
                s_structure = _ratio_hist(a["type_hist"], b["type_hist"])
                if s_structure < .66:
                    continue
                s_calls = _jaccard(a["calls"], b["calls"])
                s_names = max(_jaccard(_name_tokens(a["qualname"]), _name_tokens(b["qualname"])),
                              difflib.SequenceMatcher(None, a["qualname"].split(".")[-1], b["qualname"].split(".")[-1]).ratio())
                score = .60 * s_structure + .25 * s_calls + .15 * s_names
                if score >= threshold:
                    near.append({"left_id": a["id"], "right_id": b["id"], "score": round(score, 4),
                                 "reason": {"structure": round(s_structure, 3), "calls": round(s_calls, 3), "name": round(s_names, 3)},
                                 "status": "review_required",
                                 "left": f"{a['source_name']}::{a['qualname']}", "right": f"{b['source_name']}::{b['qualname']}"})
    near.sort(key=lambda x: (-x["score"], x["left"], x["right"]))
    return {"exact_groups": exact_groups, "shape_groups": shape_groups,
            "near_candidates": near[:limit], "near_total": len(near),
            "threshold": threshold,
            "warning": "Similarity is heuristic. Never merge without semantic review and tests."}
