"""DIL-08 frozen, read-only real-public-source field evaluator.

Needs a local CBDK git checkout containing DIL-07's exact pinned dev commit.
No writes to that source checkout, Github calls, model generation or execution grants.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT.parent
sys.path.insert(0, str(RESEARCH / "dil07"))
sys.path.insert(0, str(RESEARCH / "dil04"))
from snapshot import git_blob_sha, load_corpus  # noqa: E402
from retrieval import all_context, hybrid, input_bytes  # noqa: E402
from selector import ACTION_INTENTS, select, validate_catalog  # noqa: E402


def jsonfile(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_freeze():
    freeze = jsonfile(ROOT / "FREEZE.json")
    if freeze.get("schema") != "dil08-freeze-v1":
        raise ValueError("unknown freeze schema")
    for rel, digest in freeze.get("sha256", {}).items():
        target = (RESEARCH / rel).resolve()
        if not target.is_relative_to(RESEARCH):
            raise ValueError("unsafe frozen path")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("frozen content hash mismatch: " + rel)
    if git_blob_sha((RESEARCH / "dil04/retrieval.py").read_bytes()) != "6d2ab052ff3ba40a16fb99288e82a0a646624c58":
        raise ValueError("DIL04 engine changed from recorded source")
    return freeze


def normalized_case(case):
    if "gold_required" in case:
        return {**case, "project": "CBDK"}
    # Previously-seen DIL07 questions: they are development-only.
    return {
        "id": case["id"], "question": case["query"],
        "project": "CBDK", "intent": "read_only_qa",
        "topic_hints": case["topics"], "gold_required": case["gold_ids"],
        "historical_gold": False,
    }


def score(cases, docs, catalog_by_id):
    by_id = {d["id"]: d for d in docs}
    if len(by_id) != len(docs):
        raise ValueError("duplicate source document IDs")
    measurements = {name: {"found": 0, "total": 0, "exact": 0,
                            "historical_as_current": 0, "bytes": 0,
                            "unsafe_flag": 0, "missing_authority": 0,
                            "cases": []}
                    for name in ("full_context", "dil04_hybrid", "authority_first")}
    for case in cases:
        gold = set(case["gold_required"])
        if not gold or not gold <= set(by_id):
            raise ValueError("invalid gold evidence for " + case["id"])
        q = {"project": "CBDK", "topics": case.get("topic_hints", []),
             "query": case["question"], "max_docs": len(docs)}
        baselines = {
            "full_context": all_context(docs, q),
            "dil04_hybrid": hybrid(docs, q),
        }
        candidate = select(case, by_id, catalog_by_id)
        baselines["authority_first"] = [by_id[i] for i in candidate["selected"]]
        if any(candidate[k] for k in ("may_execute", "may_merge", "may_skip_ci")):
            raise AssertionError("action privilege exposed")
        for name, matched_docs in baselines.items():
            result = measurements[name]
            ids = {d["id"] for d in matched_docs}
            wrong_current = int("r15" in ids and case.get("intent") in ACTION_INTENTS)
            missing = sorted(gold - ids)
            # Equal serialization for each arm; metadata provenance reported outside byte tally.
            bytes_sent = input_bytes(matched_docs)
            result["found"] += len(gold & ids)
            result["total"] += len(gold)
            result["exact"] += int(ids == gold)
            result["historical_as_current"] += wrong_current
            result["bytes"] += bytes_sent
            result["missing_authority"] += int(bool(missing) and case.get("intent") in ACTION_INTENTS)
            result["cases"].append({
                "id": case["id"], "gold": sorted(gold), "selected": sorted(ids),
                "missing": missing, "historical_as_current": bool(wrong_current),
                "bytes": bytes_sent,
                "status": candidate["status"] if name == "authority_first" else "retrieval_only_not_authorized",
                "claims_runtime_authorization": False,
                "source_identity": [
                    {"id": d["id"], "source": d["source"],
                     "source_commit": d["source"].split("/blob/")[1].split("/")[0] if "/blob/" in d["source"] else "test_fixture",
                     "blob_sha": catalog_by_id[d["id"]].get("blob_sha", "unknown"),
                     "authority": catalog_by_id[d["id"]].get("authority", "unknown"),
                     "lifecycle": catalog_by_id[d["id"]].get("lifecycle", "unknown")}
                    for d in matched_docs
                ] if name == "authority_first" else [],
            })
    return measurements


def run(repo):
    freeze = verify_freeze()
    manifest = jsonfile(RESEARCH / "dil07/manifest.json")
    catalog = jsonfile(ROOT / "TAG_CATALOG.json")
    by_id = validate_catalog(catalog, manifest)
    docs = load_corpus(repo, manifest)
    # Load source blobs at the fixed commit; loader rejects a mismatched Git blob SHA.
    if any(d["id"] not in by_id for d in docs):
        raise ValueError("unrecognized source ID")
    cases = [normalized_case(c) for c in jsonfile(ROOT / "SCENARIOS.json")]
    dev = [normalized_case(c) for c in jsonfile(RESEARCH / "dil07/cases.json")]
    result = {"experiment": "DIL-08", "source_commit": manifest["source_commit"],
              "freeze": freeze, "dataset": {"public_documents": len(docs),
              "new_preregistered_cases": len(cases), "previously_seen_development_cases": len(dev)},
              "runtime": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
              "operations": score(cases, docs, by_id),
              "development_seen": score(dev, docs, by_id),
              "no_real_ai_or_human_blind_gold": True, "may_execute": False,
              "may_merge": False, "may_skip_ci": False,
              "automatic_production_adoption": False}
    arm = result["operations"]["authority_first"]
    all_bytes = result["operations"]["full_context"]["bytes"]
    result["operations_ratio"] = arm["bytes"] / all_bytes if all_bytes else None
    mandatory_total = mandatory_found = optional_total = optional_found = 0
    for original, observed in zip(cases, arm["cases"]):
        action = original["intent"] in ACTION_INTENTS
        required = set(original["gold_required"])
        if action and original.get("official_round") == "R16":
            mandatory = {"agents", "r16", "state", "parallel"}
            if original["intent"] == "continue":
                mandatory.add("roles")
        elif action:
            mandatory = {"agents"}
        else:
            mandatory = set()
        mandatory &= required
        optional = required - mandatory
        found = set(observed["selected"])
        mandatory_total += len(mandatory)
        mandatory_found += len(mandatory & found)
        optional_total += len(optional)
        optional_found += len(optional & found)
    result["coverage"] = {
        "mandatory_action_sources": [mandatory_found, mandatory_total],
        "additional_sources": [optional_found, optional_total],
    }
    result["gates"] = {
        "no_unsafe_automation": True,  # no action is reachable in this read-only evaluator
        "zero_current_r15": arm["historical_as_current"] == 0,
        "all_mandatory_action_sources": mandatory_found == mandatory_total,
        "additional_coverage_at_least_95_percent": optional_total == 0 or optional_found/optional_total >= .95,
        "bytes_at_most_half": bool(all_bytes and arm["bytes"] <= all_bytes * 0.5),
    }
    result["gates"]["limited_field_pass"] = all(result["gates"].values())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True,
                        help="CBDK checkout with exact source commit already fetched")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.repo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    print(json.dumps({"gates": result["gates"], "operations_ratio": result["operations_ratio"],
                      "operations": {k: {n: v for n, v in x.items() if n != "cases"}
                                     for k, x in result["operations"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
