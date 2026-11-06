# CBDK × Notion development sync

Last handoff: 2026-11-07 JST.

## Purpose and authority

- GitHub remains the **technical source of truth**: `docs/project/STATE.json` (canonical machine-readable state), generated `docs/PROJECT_HANDOFF.md`, `docs/PROJECT_SPEC.md`, `docs/PROGRESS.md` and `AGENTS.md`.
- Notion is the **human-friendly mirror** for project status and actionable tasks. A Notion status does not replace a GitHub code review, test result, or release.
- Updates occur **during an active development conversation / work session, at milestones**. There is currently **no always-on webhook or autonomous scheduler**; do not imply updates happen while no work is running.

## Linked Notion records

- CBDK project: https://app.notion.com/p/410948b7493781449462ca76e9567e75
- NEXT-008 — GLB comparison/diagnostics integration: https://app.notion.com/p/410948b7493781d9a266c32bc2a9f528
- NEXT-009 — static property mapping and geometry-effect verification boundary: https://app.notion.com/p/410948b74937813dab6de0fae794f85c
- v0.18 final PR/CI/release decision: https://app.notion.com/p/410948b749378174ac0bfe3633681584
- Notion project hub: https://app.notion.com/p/40a948b7493781c9901af0a55e2e5657

## Handoff snapshot

- Repository: https://github.com/mibesamiti-png/Chappy-Blender-DevKit (public)
- Formal release and `last_verified`: **v0.17.0**, unchanged.
- Ongoing work: **v0.18.0**, draft PR #25 on `feature/v0.18-shape-diagnostics`. No merge or release at this handoff.
- Current PR head inspected: `5baf36c1eee1d2b9e48bc3c2d19973365ae00ab4`.
- On that exact SHA, GitHub Actions `42258573723` (handoff), `42258572181` (Windows), `42258572080` (Python), `42258572104` (kit), and `42258572193` (Blender) each returned `completed/success`. These results do **not** validate commits made after that head.
- Draft branch's state ledger records GLB-005 through GLB-019, with GLB-010 explicitly partial/not_tested. The synthetic Blender/GLB evidence does not prove arbitrary real-world GLB equivalence or property effects.
- NEXT-008 and NEXT-009 are in progress; separate release/CI decision remains outstanding.
- Private Blender addon sources, private GLB files, secrets and local reports are not to be committed to the public repository or mirrored to Notion.

## Milestone update checklist

1. Inspect the latest PR commit and changes; execute or inspect the relevant Python/Windows/Blender CI.
2. Update `docs/project/STATE.json` and generated `docs/PROJECT_HANDOFF.md` using the existing project process. Keep requirement IDs, statuses, verification levels, known issues, decisions and next actions consistent with tested evidence.
3. Update the existing specification, progress log and PR description only as warranted; preserve draft/release boundaries and commit SHA evidence.
4. Update the **same** Notion CBDK project and task pages, rather than duplicating them. Record the task ID, actual status, exact tested SHA, CI run URLs and restrictions. Close tasks only after acceptance is evidenced.
5. Compare GitHub and Notion statuses and report any partial update / connector failure. Do not assert synchronization when one side was not written.

## Next work

Continue from PR #25 and its `docs/project/STATE.json` / generated handoff; prefer the next validated synthetic GLB geometry-diagnostics step before claiming arbitrary addon auto-repair. Confirm CI at the most recent commit prior to any release decision.
