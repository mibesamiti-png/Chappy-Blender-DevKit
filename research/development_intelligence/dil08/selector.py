"""DIL-08 read-only authority-first evidence selector. NOT a permission engine."""
from __future__ import annotations

ALLOWED_INTENTS = frozenset({"continue", "modify", "integrate", "release", "read_only_qa"})
ACTION_INTENTS = ALLOWED_INTENTS - {"read_only_qa"}
MANDATORY = ("agents", "r16", "state", "parallel")
ACTION_RESULTS = {
    "continue": "blocked_pending_live_issue_and_ci",
    "modify": "blocked_pending_permission_and_review",
    "integrate": "blocked_pending_exact_head_ci_and_a_review",
    "release": "blocked_release_needs_approval",
}
ACTIVE = "current_at_pinned_commit"


def validate_catalog(catalog, manifest):
    if catalog.get("schema") != "dil08-tag-catalog-v1":
        raise ValueError("unsupported tag catalog")
    if catalog.get("source_commit") != manifest.get("source_commit"):
        raise ValueError("catalog/source commit mismatch")
    manifest_by_id = {x["id"]: x for x in manifest["documents"]}
    rows = catalog.get("documents", [])
    if len(rows) != len(manifest_by_id):
        raise ValueError("catalog has missing or additional documents")
    seen = set()
    for x in rows:
        doc_id = x.get("id")
        if doc_id in seen or doc_id not in manifest_by_id:
            raise ValueError("duplicate or unknown document")
        seen.add(doc_id)
        if x["lifecycle"] == "historical" and manifest_by_id[doc_id]["current"]:
            raise ValueError("catalog historical status contradicts manifest")
        if x["lifecycle"] == ACTIVE and not manifest_by_id[doc_id]["current"]:
            raise ValueError("catalog current status contradicts manifest")
        if not isinstance(x.get("topic"), list) or not all(isinstance(t, str) and t for t in x["topic"]):
            raise ValueError("invalid topic labels")
        if doc_id == "r15" and x["authority"] != "historical":
            raise ValueError("R15 must be historical")
        if doc_id == "r16" and x["authority"] != "official_assignment":
            raise ValueError("R16 must be official assignment")
    return {x["id"]: x for x in rows}


def select(case, source_docs, catalog_by_id):
    """Select candidate evidence. Never return execution permission.

    source_docs is a blob-SHA-verified map keyed by id, as loaded by DIL-07.
    A caller must independently fetch live GitHub issue, current dev HEAD and CI.
    """
    intent = case.get("intent")
    out = {"status": "blocked_invalid_request", "selected": [], "may_execute": False,
           "may_merge": False, "may_skip_ci": False, "live_github_verified": False}
    if intent not in ALLOWED_INTENTS or case.get("project", "CBDK") != "CBDK":
        return out
    hints = case.get("topic_hints", [])
    if not isinstance(hints, list) or any(not isinstance(t, str) for t in hints):
        return out
    ids = []
    if intent in ACTION_INTENTS:
        ids.append("agents")
        # Round mismatch stops before selecting any stale instruction.
        if case.get("official_round") != "R16":
            out["status"] = "blocked_wrong_round"
            required = ids
        else:
            required = list(MANDATORY)
            if intent == "continue":
                # Role docs needed; live Issue #125 is not part of pinned corpus.
                if case.get("team") not in ("B", "C", "D"):
                    return out
                required.append("roles")
            elif case.get("team") not in ("A", None):
                return out
            ids.extend(x for x in required if x not in ids)
            out["status"] = ACTION_RESULTS[intent]
    else:
        required = []
        if not hints:
            out["status"] = "needs_review_unclassified_query"
            return out
        out["status"] = "evidence_candidate_only"
    matched = [id_ for id_, tag in catalog_by_id.items()
               if tag["lifecycle"] == ACTIVE or tag["lifecycle"] == "future_inactive"
               if set(hints).intersection(tag["topic"])]
    for id_ in matched:
        if id_ not in ids:
            ids.append(id_)
    # Action/reference path may not use historical evidence as current.
    ids = [id_ for id_ in ids if catalog_by_id.get(id_, {}).get("lifecycle") != "historical"]
    if any(id_ not in source_docs or id_ not in catalog_by_id for id_ in required):
        out.update(status="blocked_missing_authority", selected=[])
        return out
    for id_ in ids:
        if id_ in source_docs and id_ in catalog_by_id:
            out["selected"].append(id_)
    if intent == "read_only_qa" and not out["selected"]:
        out["status"] = "needs_review_no_source"
    return out
