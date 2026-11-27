"""Phase212-H: bounded design orchestration, no backend dependencies.
A failed measured stage permits the next frozen candidate. Missing evidence
or execution errors halt the run; no automatic relaxation of requirements.
"""
from phase212_design_evaluation import qualification,select_candidate
STAGES=("geometry","screen","full_motion","negative_controls")

def design(candidate_ids,budget,backend):
    ids=tuple(candidate_ids)
    select_candidate(ids,{},budget)
    history=[]
    for cid in ids:
        entry=dict(candidate=cid,stages={},evidence={})
        history.append(entry)
        for stage in STAGES:
            try:
                r=backend(cid,stage)
                if not isinstance(r,dict) or r.get("status") not in ("pass","fail","unverified") or not isinstance(r.get("evidence"),dict) or not r["evidence"]:
                    raise ValueError("missing stage evidence")
                entry["stages"][stage]=r["status"]
                entry["evidence"][stage]=r["evidence"]
            except Exception as exc:
                entry["stages"][stage]="unverified"
                entry["evidence"][stage]={"error":type(exc).__name__,"message":str(exc)}
            entry["qualification"]=qualification(entry["stages"])
            state=entry["stages"][stage]
            if state=="unverified":
                return dict(action="collect_missing_evidence",selected=None,history=history,budget=budget)
            if state=="fail":break
        if entry["qualification"]["certified"]:
            return dict(action="validated_fixture",selected=cid,history=history,budget=budget)
    return dict(action="stop_and_redesign",selected=None,history=history,budget=budget)
