"""DIL-05: read-only shadow scheduling of SHA-pinned specialist reviews.

Not an approval, merge, CI dispatcher, or replacement for A's abdc_preflight.
All CI/scope facts are caller-supplied snapshots, not independently authenticated.
"""
from __future__ import annotations

TEAMS = ("B", "C", "D")


def _valid(entry, dev_sha):
    return (entry is not None and entry["ci"] == "success"
            and entry["scope_ok"] is True and entry["base_sha"] == dev_sha)


def simulate(case, policy="sha_pinned"):
    """Replay timestamp-ordered synthetic PR evidence and return review opportunities.

    A review must always be manual and validated again at integration time.
    Review units are equal-cost *illustrative* work items, not measured labor time.
    """
    if policy not in {"late_only", "eager_unpinned", "sha_pinned"}:
        raise ValueError("invalid policy")
    if not isinstance(case, dict) or not isinstance(case.get("dev_sha"), str):
        raise ValueError("invalid case")
    if set(case.get("final_heads", {})) != set(TEAMS):
        raise ValueError("missing final head")
    entries, prepared = {}, {}
    last_time = -1
    review_units = 0
    for event in case.get("events", []):
        if not isinstance(event, dict) or set(event) != {"time", "team", "head", "ci", "scope_ok", "base_sha"}:
            raise ValueError("invalid event")
        t = event["time"]
        if type(t) is not int or t < last_time or t < 0 or event["team"] not in TEAMS:
            raise ValueError("invalid timeline")
        if not isinstance(event["head"], str) or not event["head"] or event["ci"] not in {"success", "failed", "pending", "missing"}:
            raise ValueError("invalid head/ci")
        if type(event["scope_ok"]) is not bool or not isinstance(event["base_sha"], str):
            raise ValueError("invalid status")
        last_time = t
        team = event["team"]
        entries[team] = event
        if policy == "late_only" or not _valid(event, case["dev_sha"]):
            continue
        if policy == "eager_unpinned":
            if team not in prepared:
                prepared[team] = (event["head"], t)
                review_units += 1
        elif team not in prepared or prepared[team][0] != event["head"]:
            prepared[team] = (event["head"], t)
            review_units += 1

    current = {team: bool(_valid(entries.get(team), case["dev_sha"])
                          and entries[team]["head"] == case["final_heads"][team])
               for team in TEAMS}
    batch = all(current.values())
    # Never use a SHA-unbound review as evidence of a *current* review.
    reused = {team: bool(current[team] and team in prepared
                         and prepared[team][0] == case["final_heads"][team])
              for team in TEAMS}
    obsolete_previews = sum(1 for team, value in prepared.items()
                            if not current[team] or value[0] != case["final_heads"][team])
    unsafe = obsolete_previews if policy == "eager_unpinned" else 0
    if policy == "late_only":
        reused = {team: False for team in TEAMS}
        unsafe = 0
        obsolete_previews = 0
        review_units = sum(current.values()) if batch else 0
    final_ready_at = max((entries[t]["time"] for t in TEAMS), default=None) if batch else None
    overlap = (sum(max(0, final_ready_at - prepared[team][1])
                   for team in TEAMS if reused[team]) if batch else None)
    # Preparing a final team at the all-green instant is NOT early work.
    # This is merely metadata-read preparation, not completed human review.
    early_prepared = (sum(1 for team in TEAMS if reused[team]
                          and prepared[team][1] < final_ready_at) if batch else 0)
    if policy == "eager_unpinned" and batch:
        # Naive reuse incorrectly counts old-SHA snapshots as if still applicable.
        early_prepared = sum(1 for _, t in prepared.values() if t < final_ready_at)
    post_ready_units = (3 - early_prepared) if batch else None
    return {
        "current_valid": sorted(t for t in TEAMS if current[t]),
        "batch_all_green": batch,
        "current_reviews_prepared": sorted(t for t in TEAMS if reused[t]),
        "unsafe_reuse_count": unsafe,
        "obsolete_prepared_snapshots": obsolete_previews,
        "review_units_total": review_units,
        "post_ready_review_units": post_ready_units,
        "overlap_window_seconds_sum": overlap,
        "required_combined_ci_still_due": True,
        "manual_review_still_due": True,
        "merge_authorized": False,
        "dispatched_ci": 0,
    }
