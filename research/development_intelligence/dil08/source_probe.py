"""Secondary DIL-08 *metadata-only* probe, NOT full-text SQLite evaluation.

Reads DIL-07's previously recorded public-source metadata/byte sizes, not live
GitHub or source bodies. Reuses the frozen DIL-08 selector unchanged. This is
an exploratory secondary analysis and cannot establish product readiness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate import jsonfile, verify_freeze, RESEARCH, ROOT
from selector import select, validate_catalog


def approximate_bytes(entries, ids):
    """DIL-07 per-source bundle byte counts plus document list punctuation."""
    index = {entry["id"]: entry for entry in entries}
    return 1 + len(ids) + sum(index[i]["bytes"] for i in ids)


def score(source, catalog, scenarios):
    source_by_id = {item["id"]: item for item in source}
    if len(source_by_id) != len(source):
        raise ValueError("duplicate source ID")
    if not all(x.get("blob_ok") is True and x.get("anchors_ok") is True for x in source):
        raise ValueError("source metadata lacks previously observed blob/anchor confirmation")
    if not scenarios:
        raise ValueError("empty scenarios are not a meaningful probe")
    details=[]
    totals={"exact_cases":0, "required_found":0,"required_total":0,
            "mandatory_found":0,"mandatory_total":0,"additional_found":0,
            "additional_total":0,"historical_r15_as_current":0,
            "candidate_approx_bytes":0,"full_context_approx_bytes":0}
    all_ids=[d["id"] for d in source]
    for case in scenarios:
        result=select(case,source_by_id,catalog)
        selected=set(result["selected"])
        gold=set(case["gold_required"])
        if not gold or not gold <= set(source_by_id):
            raise ValueError("invalid authored gold IDs")
        if case["intent"] in ("continue","modify","integrate","release"):
            mandatory={"agents","r16","state","parallel"} if case.get("official_round")=="R16" else {"agents"}
            if case["intent"]=="continue" and case.get("official_round")=="R16":
                mandatory.add("roles")
            mandatory &= gold
        else:
            mandatory=set()
        extra=gold-mandatory
        found=gold&selected
        totals["exact_cases"]+=int(selected==gold)
        totals["required_found"]+=len(found)
        totals["required_total"]+=len(gold)
        totals["mandatory_found"]+=len(mandatory&selected)
        totals["mandatory_total"]+=len(mandatory)
        totals["additional_found"]+=len(extra&selected)
        totals["additional_total"]+=len(extra)
        totals["historical_r15_as_current"]+=int("r15" in selected and case["intent"]!="read_only_qa")
        totals["candidate_approx_bytes"]+=approximate_bytes(source,result["selected"])
        totals["full_context_approx_bytes"]+=approximate_bytes(source,all_ids)
        if any(result[p] for p in ("may_execute","may_merge","may_skip_ci")):
            raise AssertionError("read-only selector returned an action permission")
        details.append({"id":case["id"],"status":result["status"],
                        "selected":result["selected"],"required":case["gold_required"],
                        "missing":sorted(gold-selected),"may_execute":False})
    totals["candidate_vs_full_byte_ratio"]=totals["candidate_approx_bytes"]/totals["full_context_approx_bytes"]
    return {"study":"DIL-08", "kind":"exploratory_secondary_metadata_probe_not_SQLite_or_AI_execution",
            "cases":len(scenarios),"figures_approximate":True,"aggregates":totals,"per_case":details,
            "source_metadata_verified_in_DIL07_not_refetched_here":True,
            "all_interpretations_and_topic_hints_manual":True,
            "product_adoption":False,"CI_or_GitHub_authorizations_measured":False,
            "full_corpus_SQLite_run_completed":False}


def run():
    verify_freeze()
    manifest=jsonfile(RESEARCH/"dil07/manifest.json")
    catalog=validate_catalog(jsonfile(ROOT/"TAG_CATALOG.json"),manifest)
    observed=jsonfile(RESEARCH/"dil07/observed_matrix.json")
    if observed["source_commit"]!=manifest["source_commit"]:
        raise ValueError("observed metadata source revision mismatch")
    res=score(observed["entries"],catalog,jsonfile(ROOT/"SCENARIOS.json"))
    res["source_commit"]=manifest["source_commit"]
    return res


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data=run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps(data["aggregates"],ensure_ascii=False,indent=2))
