"""Read-only, fail-closed preflight for CBDK's B/C/D specialist PRs.

This is a review aid, NEVER an authorization to merge, publish or approve code.
Do not fetch or execute PR code. GitHub API data is treated as untrusted input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.ci_cycle_metrics import REPO, SHA_RE, fetch_runs, summarize

BASE_BRANCH = "feature/v0.18-shape-diagnostics"

# Narrow, positive path allowlists. Shared files are owned by team A.
OWNED = {
    "B": ("cbdk/glb_", "tests/test_glb_", "docs/GLB_"),
    "C": ("templates/modular_preview/", "tests/test_ui_", "tests/blender_ui_", "docs/UI_"),
    "D": ("cbdk/extension_", "tests/test_extension_", "docs/EXTENSION_"),
}


def _api(path: str):
    """A fixed repository URL assembled only from numeric PRs or fixed refs."""
    from urllib.request import Request, urlopen
    import os
    url = f"https://api.github.com/repos/{REPO}/{path}"
    headers = {"User-Agent": "CBDK-read-only-PR-preflight/1.0",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=25) as response:
        return json.load(response)


def fetch_team(number: int) -> dict:
    if type(number) is not int or not 1 <= number <= 100000:
        raise ValueError("Invalid PR number")
    pr = _api(f"pulls/{number}")
    if not isinstance(pr, dict):
        raise ValueError("Malformed PR data")
    files = []
    for page in range(1, 5):
        batch = _api(f"pulls/{number}/files?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("Malformed PR file list")
        files.extend(item["filename"] for item in batch if isinstance(item, dict)
                     and isinstance(item.get("filename"), str))
        if len(batch) < 100:
            break
    else:
        raise ValueError("PR diff exceeds bounded preflight size")
    sha = pr.get("head", {}).get("sha")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("Missing PR head SHA")
    return {
        "number": number,
        "head_sha": sha,
        "base_branch": pr.get("base", {}).get("ref"),
        "state": pr.get("state"),
        "merged": bool(pr.get("merged")),
        "files": files,
        "runs": fetch_runs(sha),
    }


def assess(records: dict[str, dict], dev_sha: str) -> dict:
    if not SHA_RE.fullmatch(dev_sha):
        raise ValueError("Expected exact development SHA")
    blockers = []
    seen: dict[str, str] = {}
    teams = []
    for team in ("B", "C", "D"):
        p = records.get(team)
        if not isinstance(p, dict):
            blockers.append(f"{team}:missing_record")
            continue
        head = p.get("head_sha")
        name = f"{team}:#{p.get('number', '?')}"
        errors = []
        if not isinstance(head, str) or not SHA_RE.fullmatch(head):
            errors.append("invalid_head")
        if p.get("base_branch") != BASE_BRANCH:
            errors.append("wrong_base_branch")
        if p.get("state") != "open" or p.get("merged"):
            errors.append("not_open_unmerged")
        filenames = p.get("files")
        if not isinstance(filenames, list) or not filenames:
            errors.append("missing_files")
            filenames = []
        for path in filenames[:400]:
            if not isinstance(path, str) or not any(path.startswith(prefix) for prefix in OWNED[team]):
                errors.append("outside_team_scope")
                continue
            if path in seen:
                errors.append("filename_overlap")
            else:
                seen[path] = team
        if len(filenames) > 400:
            errors.append("too_many_files")
        gate = None
        if "invalid_head" not in errors:
            try:
                gate = summarize(p.get("runs"), head, gate=5)
                if gate["gate_result"] != "success":
                    errors.append("specialist_ci_not_all_green")
            except (ValueError, TypeError, AttributeError):
                errors.append("invalid_ci_evidence")
        errors = sorted(set(errors))
        blockers.extend(f"{name}:{e}" for e in errors)
        teams.append({
            "team": team,
            "pr_number": p.get("number"),
            "head_sha": head,
            "changed_files": len(filenames),
            "independent_workflow_successes": gate["workflow_successes"] if gate else 0,
            "independent_required_workflows": 5,
            "review_blockers": errors,
        })
    return {
        "schema_version": 1,
        "kind": "cbdk_specialist_preflight",
        "development_sha": dev_sha,
        "team_count": len(teams),
        "ready_for_manual_integration_review": not blockers and len(teams) == 3,
        "blockers": blockers,
        "teams": teams,
        "manual_review_required": [
            "Confirm PR commit ancestry and immutable source blobs against latest dev SHA",
            "Review cross-team API/behavioral dependencies even with no overlapping paths",
            "Run combined-head five-family CI before any development-branch merge",
            "Run new dev merged-head seven-family CI; never infer release approval",
        ],
        "note": "No merge, commit, dispatch, private source read or release action performed.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only ABCD PR preflight; never merges")
    parser.add_argument("--pr", action="append", required=True,
                        help="Exactly three assignments, e.g. --pr B=107 --pr C=108 --pr D=106")
    parser.add_argument("--dev-sha", help="Expected current development SHA; fetched when omitted")
    parser.add_argument("--snapshot-json", type=Path, help="Offline records for deterministic verification")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    assignments = {}
    for item in args.pr:
        match = re.fullmatch(r"([BCD])=([1-9][0-9]{0,5})", item)
        if not match or match[1] in assignments:
            parser.error("Use B=<pr>, C=<pr>, D=<pr> exactly once")
        assignments[match[1]] = int(match[2])
    if set(assignments) != set(OWNED):
        parser.error("Exactly B, C and D are required")
    if args.snapshot_json:
        payload = json.loads(args.snapshot_json.read_text(encoding="utf-8"))
        records = payload["records"]
        dev_sha = args.dev_sha or payload["dev_sha"]
    else:
        ref = _api("git/ref/heads/" + BASE_BRANCH)
        dev_sha = args.dev_sha or ref["object"]["sha"]
        if args.dev_sha and args.dev_sha != ref["object"]["sha"]:
            parser.error("Development SHA changed. Re-fetch before reviewing")
        records = {team: fetch_team(number) for team, number in assignments.items()}
    for team, number in assignments.items():
        if records.get(team, {}).get("number") != number:
            parser.error("Snapshot PR numbers differ from requested assignments")
    result = assess(records, dev_sha)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if result["ready_for_manual_integration_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
