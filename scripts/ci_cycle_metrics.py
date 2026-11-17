"""Read-only, SHA-bound GitHub Actions timing report for CBDK's A coordinator.

Outputs aggregate CI telemetry only (no token, user files, model paths or code).
A workflow's success is meaningful only for the exact verified commit SHA.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

REPO = "mibesamiti-png/Chappy-Blender-DevKit"
FIVE = (
    "CBDK Python tests",
    "CBDK Windows PowerShell launcher regression",
    "CBDK Blender multi-version runtime smoke",
    "CBDK offline 3D browser interaction smoke",
    "CBDK durable handoff",
)
SEVEN = FIVE + ("CBDK Windows kit package", "CBDK Agent Skill package")
SHA_RE = re.compile(r"[0-9a-fA-F]{40}\Z")


def _datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_runs(sha: str) -> dict:
    """Fetch at most 100 workflow runs, from the fixed public repository only."""
    if not SHA_RE.fullmatch(sha):
        raise ValueError("Expected a 40-character commit SHA")
    url = f"https://api.github.com/repos/{REPO}/actions/runs?head_sha={sha}&per_page=100"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CBDK-read-only-CI-metrics/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=25) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Invalid GitHub workflow response")
    return data


def summarize(data: dict, sha: str, gate: int = 7) -> dict:
    """Select latest attempts of required workflows; fail closed on gaps."""
    if not SHA_RE.fullmatch(sha):
        raise ValueError("Expected a 40-character commit SHA")
    if gate not in (5, 7):
        raise ValueError("Gate must be 5 or 7")
    if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
        raise ValueError("Missing workflow_runs")
    expected = FIVE if gate == 5 else SEVEN
    choices: dict[str, dict] = {}
    duplicates = 0
    for run in data["workflow_runs"][:100]:
        if not isinstance(run, dict) or run.get("head_sha") != sha:
            continue
        name = run.get("name")
        if name not in expected:
            continue
        previous = choices.get(name)
        rank = (run.get("created_at") or "", int(run.get("run_attempt") or 1), int(run.get("id") or 0))
        if previous:
            duplicates += 1
            oldrank = (previous.get("created_at") or "", int(previous.get("run_attempt") or 1), int(previous.get("id") or 0))
            if rank <= oldrank:
                continue
        choices[name] = run

    workflows = []
    starts = []
    finishes = []
    for name in expected:
        run = choices.get(name)
        if run is None:
            workflows.append({"name": name, "state": "missing", "run_id": None, "duration_seconds": None})
            continue
        created = _datetime(run.get("created_at"))
        updated = _datetime(run.get("updated_at"))
        done = run.get("status") == "completed"
        state = run.get("conclusion") if done else "in_progress"
        if not isinstance(state, str) or not state:
            state = "unknown"
        seconds = round((updated - created).total_seconds()) if done and created and updated and updated >= created else None
        if created:
            starts.append(created)
        if done and updated:
            finishes.append(updated)
        workflows.append({
            "name": name,
            "state": state,
            "run_id": run.get("id"),
            "duration_seconds": seconds,
            "url": run.get("html_url"),
        })
    passed = all(x["state"] == "success" for x in workflows)
    durations = [x for x in workflows if x["duration_seconds"] is not None]
    longest = max(durations, key=lambda x: x["duration_seconds"]) if durations else None
    span = round((max(finishes) - min(starts)).total_seconds()) if passed and starts and finishes else None
    return {
        "schema_version": 1,
        "kind": "cbdk_ci_cycle_metrics",
        "repository": REPO,
        "head_sha": sha,
        "gate": gate,
        "gate_result": "success" if passed else "incomplete_or_failed",
        "workflow_successes": sum(x["state"] == "success" for x in workflows),
        "workflows_required": len(expected),
        "extra_matching_runs": duplicates,
        "observed_wall_seconds": span,
        "slowest_workflow": longest["name"] if longest else None,
        "slowest_workflow_seconds": longest["duration_seconds"] if longest else None,
        "workflows": workflows,
        "note": "Workflow times include queue and setup. This does not measure developer work or approve a release.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only CBDK GitHub Actions timing report")
    parser.add_argument("--sha", required=True, help="Exact 40-character commit SHA")
    parser.add_argument("--gate", type=int, choices=(5, 7), default=7)
    parser.add_argument("--runs-json", type=Path, help="Offline GitHub API fixture, otherwise fetch live")
    parser.add_argument("--output", type=Path, help="Optional local JSON output")
    args = parser.parse_args(argv)
    payload = json.loads(args.runs_json.read_text(encoding="utf-8")) if args.runs_json else fetch_runs(args.sha)
    report = summarize(payload, args.sha, args.gate)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if report["gate_result"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
