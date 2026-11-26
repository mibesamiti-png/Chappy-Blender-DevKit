# DIL-09 phase 1 — actual CI event-context finding (separate follow-up)

2026-11-25 JST. Preserve the frozen first result unchanged. The synthetic tests passed 20/20, but the initial live snapshot returned blocked, 0/7 **matching the requested event**, not seven failed workflows. The researcher assumed that post-integration dev CI would use push; this assumption was wrong for the observed CBDK workflow context.

Read-only follow-up verified:
- Dev branch HEAD: 2b8220210c2475239a43354d544b5a6f176fba80.
- PR #128 is merged with that merge commit SHA.
- [PR #25](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/25) is an open draft from feature/v0.18-shape-diagnostics into main with exactly that HEAD.
- All seven observed workflows have event pull_request, head_branch feature/v0.18-shape-diagnostics, matching head_sha, completed/success, and pull_requests metadata containing #25. Run IDs: 42926775783 (Blender), 42926775790 (browser), 42926775811 (Windows kit), 42926776044 (skill), 42926775780 (handoff), 42926775882 (Python), 42926775997 (Windows regression).
- No job details/logs were fetched. This verifies family summary context only, not every required matrix job, actual checkout/merge tree, review or permission.
- Existing A-owned #109 ci_cycle_metrics.py already implements SHA-bound latest-attempt family summarization. It remains a separate unmerged candidate. The next adapter should consume an explicitly verified contract from A, not maintain a competing production CI validator. Validate expected event/PR/branch against the relevant official gate, don't infer push from "post-integration," don't simply allow every event, and don't weaken job-level requirements.

Decision: phase 1 synthetic replay PASS, live pilot gate NOT PASS. Fail-closed behavior worked, but event assumption caused an unnecessary block. Do not rewrite FIRST_RESULT.json or METHOD.md, claim a successful operational pilot, change official R16 assignments, or deploy. Next phase: bind official evidence context to existing checker output, repeat live read-only replay, and measure checkpoint size/real workload. No real efficiency measurement yet.
