"""Research-only context binding and checkpoint; never an authorization engine."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

REPO = "mibesamiti-png/Chappy-Blender-DevKit"
BRANCH = "feature/v0.18-shape-diagnostics"
CHECKER_BLOB = "1eac925e9483eb3cbe24a2cb26e2159760475768"
CHECKER_COMMIT = "5dc20802ddc8f8f7e1ec6df2ed8d05d9ab4362c4"

def wire(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def sha(x):
    return isinstance(x, str) and re.fullmatch(r"[0-9a-f]{40}", x) is not None

def load_checker(path):
    raw = Path(path).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if actual != CHECKER_BLOB:
        raise ValueError("checker blob mismatch")
    spec = importlib.util.spec_from_file_location("pinned_ci_metrics", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def route(s, checker):
    out = dict(state="blocked", reason="invalid_context", detail_requests=[],
               may_execute=False, may_merge=False, may_skip_ci=False)
    try:
        h = s["dev_start"]
        p = s["pr_start"]
        i = s["issue_start"]
        d = i["dispatch"]
        rnd = s["round"]
        if s["repository"] != REPO or not sha(h) or h != s["dev_end"]:
            raise ValueError("dev_head_changed")
        if p != s["pr_end"] or i != s["issue_end"]:
            raise ValueError("pr_or_dispatch_changed")
        if (p["number"] != 25 or p["state"] != "open" or p["head"] != BRANCH
            or p["head_sha"] != h or p["base"] != "main" or not sha(p["base_sha"])
            or p["head_repo_full_name"] != REPO or p["head_repo_id"] != 1444729344):
            raise ValueError("pr_context_mismatch")
        if (not re.fullmatch(r"R[1-9][0-9]*", rnd) or s["assignment"] != f"docs/{rnd}_ABCD_START.md"
            or s["team"] not in ("A","B","C","D")
            or d["schema"] != "cbdk-role-dispatch-v1" or d["state"] != "active"
            or d["round"] != rnd or d["official_assignment"] != s["assignment"]
            or d["development_branch"] != BRANCH or d["phase"] != "normal"
            or d["team_roles"] != {"B":"B","C":"C","D":"D"}
            or type(d["revision"]) is not int or type(s["minimum_revision"]) is not int
            or d["revision"] < max(0,s["minimum_revision"])):
            raise ValueError("dispatch_context_mismatch")
        refs=s["source_refs"]
        if (len(refs)!=3 or {x["path"] for x in refs} != {"AGENTS.md",s["assignment"],"docs/PARALLEL_DEVELOPMENT.md"}
            or not all(sha(x["blob_sha"]) for x in refs)):
            raise ValueError("source_refs_missing")
        runs=s["workflow_runs"]
        if type(s["total_count"]) is not int or s["total_count"] != len(runs) or len(runs)>100:
            raise ValueError("incomplete_run_page")
        selected=[]
        seen=set()
        for row in runs:
            if row["name"] not in checker.SEVEN or row["head_sha"] != h or row["event"] != "pull_request" or row["head_branch"] != BRANCH:
                continue
            matches=[x for x in row["pull_requests"] if x["number"] == p["number"]
                and x["head"]["ref"] == p["head"] and x["head"]["sha"] == h
                and x["head"]["repo"]["id"] == p["head_repo_id"]
                and x["base"]["ref"] == p["base"] and x["base"]["sha"] == p["base_sha"]
                and x["base"]["repo"]["id"] == p["head_repo_id"]]
            if len(matches)!=1:
                continue
            if type(row["id"]) is not int or row["id"]<=0 or row["id"] in seen:
                raise ValueError("duplicate_or_invalid_run_id")
            if type(row["run_attempt"]) is not int or row["run_attempt"]<1 or not isinstance(row["created_at"],str):
                raise ValueError("invalid_attempt")
            if row["status"] not in ("completed","queued","in_progress","requested","waiting","pending"):
                raise ValueError("invalid_status")
            if row["status"]=="completed" and not isinstance(row["conclusion"],str):
                raise ValueError("invalid_conclusion")
            seen.add(row["id"])
            selected.append(row)
        report=checker.summarize({"workflow_runs":selected},h,7)
        out["summary"]={"success":report["workflow_successes"],"required":report["workflows_required"]}
        out["detail_requests"]=[{"run_id":x["run_id"],"request":"failed_job_summary_first"}
            for x in report["workflows"] if x["state"] in ("failure","timed_out")]
        out["reason"]="family_summary_only" if report["gate_result"]=="success" else "ci_not_all_verified"
        out["state"]="summary_ready" if report["gate_result"]=="success" else "blocked"
        out["checkpoint"]={"schema":"dil09-read-only-checkpoint-v1","repository":REPO,
            "dev_head":h,"pr":p["number"],"base_sha":p["base_sha"],"round":rnd,"team":s["team"],
            "assignment":s["assignment"],"revision":d["revision"],"phase":d["phase"],
            "source_refs":refs,"family_runs":[[x["name"],x["run_id"],x["state"]] for x in report["workflows"]],
            "state":out["state"],"next":"refresh HEAD, PR, Issue and exact-head CI; read formal rules and assigned sources; verify required jobs independently",
            "permissions":"none; historical observation only"}
        out["sizes"]={"stored_workflow_metadata_bytes":len(wire(runs)),
            "checkpoint_bytes":len(wire(out["checkpoint"]))}
        return out
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        out["reason"]=str(exc)
        return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--checker",required=True)
    ap.add_argument("--fixture",required=True)
    a=ap.parse_args()
    result=route(json.loads(Path(a.fixture).read_text()),load_checker(a.checker))
    print("DIL09_RESULT="+json.dumps(result,ensure_ascii=False,separators=(",",":")))
if __name__=="__main__":
    main()
