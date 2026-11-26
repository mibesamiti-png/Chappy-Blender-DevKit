"""DIL-06: bounded, read-only GitHub timeline evidence classifier.

This is not a merge gate, a CI preflight replacement or an AI activity monitor.
PR created_at is a *publication event*. No inference about review start, human
idle time, model usage, or actual throughput is possible from these inputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

SHA = re.compile(r"[0-9a-f]{40}\Z")
REQUIRED: dict[str, tuple[str, ...]] = {
    "Python": ("unittest (3.11)", "unittest (3.12)", "unittest (3.13)"),
    "Windows": ("powershell-unittest (3.11)", "powershell-unittest (3.13)"),
    "Blender": ("blender-parts (4.4.3)", "blender-parts (4.5.15)", "blender-parts (5.2.1)"),
    "Browser": ("chromium-offline-viewer",),
    "Handoff": ("Verify project state and publish actual test observation",),
}
UNOBSERVABLE = (
    "a_review_start_at", "a_review_minutes", "bcd_actually_idle_seconds",
    "user_instruction_wait_seconds", "ai_compute_seconds", "time_saved_seconds",
    "duplicate_ci_cost_seconds", "throughput_improvement_percent",
)


def utc(s: Any) -> datetime:
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s):
        raise ValueError("timestamp_invalid_or_unknown")
    return datetime.fromisoformat(s[:-1] + "+00:00").astimezone(timezone.utc)


def sha(s: Any) -> bool:
    return isinstance(s, str) and bool(SHA.fullmatch(s))


def check_team(team: dict[str, Any]) -> dict[str, Any]:
    """Validate a *static evidence record*, not live PR/ref state.

    Raw run+job snapshots have to originate from an external trustworthy reader.
    #109 remains the source of production exact-head preflight logic.
    """
    errors: list[str] = []
    head = team.get("head_sha")
    if not sha(head):
        errors.append("invalid_team_sha")
    flows = team.get("workflows")
    if not isinstance(flows, list):
        flows = []
    names: set[str] = set()
    end_times: list[datetime] = []
    for flow in flows:
        if not isinstance(flow, dict):
            errors.append("invalid_workflow")
            continue
        family = flow.get("family")
        if not isinstance(family, str):
            errors.append("invalid_workflow_family")
            continue
        if family in names:
            errors.append("duplicate_workflow_family")
        names.add(family)
        if family not in REQUIRED:
            errors.append("unexpected_workflow_family")
            continue
        if flow.get("head_sha") != head or not sha(flow.get("head_sha")):
            errors.append("workflow_sha_mismatch")
        if flow.get("status") != "completed" or flow.get("conclusion") != "success":
            errors.append("workflow_not_green")
        jobs = flow.get("jobs")
        if not isinstance(jobs, list):
            errors.append("missing_job_evidence")
            continue
        if type(flow.get("job_total")) is not int or flow["job_total"] != len(jobs):
            errors.append("job_listing_incomplete")
        by_name: dict[str, dict[str, Any]] = {}
        for j in jobs:
            if not isinstance(j, dict) or not isinstance(j.get("name"), str):
                errors.append("invalid_job")
                continue
            if j["name"] in by_name:
                errors.append("duplicate_job")
            by_name[j["name"]] = j
        try:
            run_updated = utc(flow.get("run_updated_at"))
            run_created = utc(flow.get("run_created_at"))
            if run_updated < run_created:
                errors.append("workflow_time_reversed")
        except ValueError:
            errors.append("workflow_timestamp_invalid")
            continue
        for need in REQUIRED[family]:
            j = by_name.get(need)
            if j is None:
                errors.append("required_job_missing")
                continue
            if j.get("head_sha") != head or not sha(j.get("head_sha")):
                errors.append("required_job_sha_mismatch")
            if j.get("status") != "completed" or j.get("conclusion") != "success":
                errors.append("required_job_not_green")
            try:
                t = utc(j.get("completed_at"))
                if not run_created <= t <= run_updated:
                    errors.append("job_outside_run_window")
                end_times.append(t)
            except ValueError:
                errors.append("required_job_timestamp_invalid")
    if set(REQUIRED) != names:
        errors.append("required_workflow_family_missing")
    return {
        "role": team.get("role"),
        "pr": team.get("pr"),
        "head_sha": head,
        "ready_at": (max(end_times).isoformat().replace("+00:00", "Z") if not errors and end_times else None),
        "required_workflow_count": len(REQUIRED) if not errors else 0,
        "required_job_count": sum(len(v) for v in REQUIRED.values()) if not errors else 0,
        "blockers": sorted(set(errors)),
    }


def analyze_round(round_record: dict[str, Any]) -> dict[str, Any]:
    teams = round_record.get("teams")
    if not isinstance(teams, list):
        teams = []
    seen = [v.get("role") for v in teams if isinstance(v, dict)]
    roles_good = len(teams) == 3 and len(seen) == 3 and all(isinstance(x, str) for x in seen) and sorted(seen) == ["B", "C", "D"]
    team_reports = [check_team(v) for v in teams if isinstance(v, dict)]
    blockers = ["team_set_invalid"] if not roles_good else []
    blockers.extend(f"{t['role']}:{err}" for t in team_reports for err in t["blockers"])
    integration = round_record.get("integration_pr")
    if not isinstance(integration, dict) or integration.get("created_at") is None:
        blockers.append("integration_pr_not_observed")
        integration_created = None
    else:
        try:
            integration_created = utc(integration["created_at"])
        except ValueError:
            blockers.append("integration_pr_timestamp_invalid")
            integration_created = None
    observed_ready = None
    gap_seconds = None
    if not blockers and integration_created is not None:
        try:
            ready = max(utc(t["ready_at"]) for t in team_reports)
            if integration_created < ready:
                blockers.append("integration_pr_created_before_complete_ci")
            else:
                observed_ready = ready.isoformat().replace("+00:00", "Z")
                gap_seconds = int((integration_created - ready).total_seconds())
        except ValueError:
            blockers.append("ready_timestamp_invalid")
    return {
        "round": round_record.get("round"),
        "report_kind": "observed_publication_interval" if not blockers else "insufficient_evidence",
        "team_evidence": team_reports,
        "blockers": sorted(set(blockers)),
        "last_required_ci_job_completed_at": observed_ready,
        "integration_pr_created_at": (integration_created.isoformat().replace("+00:00", "Z") if integration_created else None),
        "ci_to_integration_pr_publication_gap_seconds": gap_seconds,
        "unobservable": {k: None for k in UNOBSERVABLE},
        "is_proof_of_speedup": False,
        "can_authorize_merge": False,
        "can_skip_ci": False,
    }


def analyze_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    rounds = payload.get("rounds", [])
    if not isinstance(rounds, list) or not 1 <= len(rounds) <= 4:
        raise ValueError("bounded_round_count_required")
    ids = [r.get("round") for r in rounds]
    if any(not isinstance(x, str) for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid_or_duplicate_round_id")
    reports = [analyze_round(r) for r in rounds]
    return {
        "schema_version": 1,
        "research": "DIL-06",
        "rounds": reports,
        "observable_complete_rounds": sum(r["report_kind"] == "observed_publication_interval" for r in reports),
        "note": "Public GitHub publication gaps only; never infer A working minutes, AI execution, user idle, or causal speedup.",
    }
