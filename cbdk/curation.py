"""Human curation of static candidates. Does not execute or merge inspected code."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PART_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-[0-9]{3,6}$")
DECISIONS = {"selected", "rejected", "blocked", "hold"}
ORIGINS = {"self_owned", "third_party"}


def _load(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


def _write_json_atomic(path: str | Path, data: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=".cbdk-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _symbol_map(catalog: dict) -> dict[str, dict]:
    result = {}
    for symbol in catalog.get("symbols", []):
        sid = symbol["id"]
        if sid in result:
            raise ValueError(f"Duplicate candidate ID in catalog: {sid}")
        result[sid] = symbol
    return result


def build_review_queue(catalog: dict, duplicates_report: dict) -> dict:
    """Rank AST, shape and near-match evidence for human review only."""
    symbols = _symbol_map(catalog)
    findings = []
    for group_type, confidence in (("exact_groups", "ast"), ("shape_groups", "shape")):
        for group in duplicates_report.get(group_type, []):
            ids = sorted({x["id"] for x in group["symbols"] if x["id"] in symbols})
            if len(ids) < 2:
                continue
            digest = hashlib.sha256((confidence + "|" + "|".join(ids)).encode()).hexdigest()[:12].upper()
            findings.append({"id": "REV-" + digest, "category": confidence,
                             "candidate_ids": ids, "members": [
                                 {"candidate_id": cid, "qualname": symbols[cid]["qualname"],
                                  "source_name": symbols[cid]["source_name"],
                                  "kind": symbols[cid]["kind"],
                                  "line": symbols[cid]["line"]} for cid in ids],
                             "score": 1.0 if confidence == "ast" else None,
                             "risk": "Context, globals, licensing and Blender version must be reviewed",
                             "decision": "unreviewed"})
    for pair in duplicates_report.get("near_candidates", []):
        ids = sorted([pair["left_id"], pair["right_id"]])
        if any(cid not in symbols for cid in ids) or ids[0] == ids[1]:
            continue
        digest = hashlib.sha256(("near|" + "|".join(ids)).encode()).hexdigest()[:12].upper()
        findings.append({"id": "REV-" + digest, "category": "near",
                         "candidate_ids": ids,
                         "members": [{"candidate_id": cid, "qualname": symbols[cid]["qualname"],
                                      "source_name": symbols[cid]["source_name"],
                                      "kind": symbols[cid]["kind"],
                                      "line": symbols[cid]["line"]} for cid in ids],
                         "score": pair["score"], "risk": "Heuristic similarity is not behavioral equivalence",
                         "decision": "unreviewed"})
    weight = {"ast": 0, "shape": 1, "near": 2}
    findings.sort(key=lambda x: (weight[x["category"]], -(x["score"] or 0), x["id"]))
    return {"schema_version": 1, "finding_count": len(findings), "findings": findings,
            "warning": "Review only. No code was executed, merged or marked approved."}


def render_review_markdown(queue: dict, limit: int = 100) -> str:
    lines = ["# CBDK 重複レビュー候補", "", "自動一致は動作同等性・再配布権限の証明ではありません。", ""]
    for entry in queue["findings"][:limit]:
        members = ", ".join(f"{m['source_name']}::{m['qualname']} ({m['candidate_id']})" for m in entry["members"])
        lines.append(f"- **{entry['id']}** [{entry['category']}] {members}")
    lines.append("")
    return "\n".join(lines)


def empty_registry() -> dict:
    return {"schema_version": 2, "parts": [],
            "warning": "Selected entries are NOT runtime-verified or license-cleared; review required."}


def read_registry(path: str | Path) -> dict:
    file = Path(path)
    reg = _load(file) if file.exists() else empty_registry()
    if reg.get("schema_version") != 2 or not isinstance(reg.get("parts"), list):
        raise ValueError("Unsupported registry format; refusing to overwrite")
    ids = [p.get("part_id") for p in reg["parts"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Registry contains duplicate stable IDs")
    return reg


def register_candidate(
    catalog: dict, registry: dict, *, candidate_id: str, part_id: str, name: str,
    purpose: str, origin: str, license_id: str, license_evidence: str,
    reviewer: str, variant_of: str | None = None,
) -> dict:
    """Manually attribute a candidate; registration does not approve it."""
    if not PART_ID_RE.fullmatch(part_id):
        raise ValueError("Invalid stable ID (example: MESH-001)")
    if origin not in ORIGINS:
        raise ValueError(f"origin must be one of: {sorted(ORIGINS)}")
    for label, value in (("name", name), ("purpose", purpose),
                         ("license_id", license_id), ("license_evidence", license_evidence),
                         ("reviewer", reviewer)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if license_id.lower() in {"unknown", "unverified", "none"}:
        raise ValueError("Unknown license cannot be registered as reviewed")
    symbols = _symbol_map(catalog)
    if candidate_id not in symbols:
        raise ValueError("Candidate not present in this catalog snapshot")
    symbol = symbols[candidate_id]
    parts = registry["parts"]
    if any(p["part_id"] == part_id for p in parts):
        raise ValueError("Stable part ID already exists; reuse or revise the existing entry")
    if any(p["candidate_id"] == candidate_id for p in parts):
        raise ValueError("Candidate already registered")
    same_ast = [p for p in parts if p.get("exact_ast_sha256") == symbol["exact_ast_sha256"]
                and p.get("kind") == symbol["kind"]]
    if same_ast and not variant_of:
        ids = ", ".join(p["part_id"] for p in same_ast)
        raise ValueError(f"Same AST is already registered ({ids}); use --variant-of with justification")
    if variant_of and not any(p["part_id"] == variant_of for p in parts):
        raise ValueError("variant_of must reference an existing stable part ID")
    entry = {
        "part_id": part_id, "name": name.strip(), "purpose": purpose.strip(),
        "candidate_id": candidate_id, "source_name": symbol["source_name"],
        "qualname": symbol["qualname"], "kind": symbol["kind"],
        "exact_ast_sha256": symbol["exact_ast_sha256"],
        "source_sha256": next((f["sha256"] for f in catalog["files"] if f["path"] == symbol["source"]), "unknown"),
        "signature": symbol["signature"],
        "origin": origin, "license_id": license_id.strip(),
        "license_evidence": license_evidence.strip(), "reviewer": reviewer.strip(),
        "status": "proposed", "verification": "static_parse_only",
        "variant_of": variant_of, "history": [{"decision": "proposed", "reviewer": reviewer.strip(),
                                           "reason": "Manual registration (not approval)",
                                           "at": datetime.now(timezone.utc).isoformat()}],
    }
    parts.append(entry)
    return entry


def decide(registry: dict, *, part_id: str, decision: str, reviewer: str, reason: str) -> dict:
    if decision not in DECISIONS:
        raise ValueError(f"Decision must be one of {sorted(DECISIONS)}")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("Reviewer and reason are required")
    entry = next((p for p in registry["parts"] if p["part_id"] == part_id), None)
    if entry is None:
        raise ValueError(f"Unknown stable ID: {part_id}")
    entry["status"] = decision
    entry.setdefault("history", []).append({"decision": decision, "reviewer": reviewer.strip(),
                                            "reason": reason.strip(), "at": datetime.now(timezone.utc).isoformat()})
    return entry


def write_registry(path: str | Path, registry: dict) -> None:
    if registry.get("schema_version") != 2:
        raise ValueError("Unsupported registry format")
    _write_json_atomic(path, registry)


def write_queue(path: str | Path, queue: dict) -> None:
    _write_json_atomic(path, queue)
