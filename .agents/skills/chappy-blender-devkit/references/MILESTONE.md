# CBDK milestone delivery — safe batched Codex workflow

Follow this procedure when the user says "continue", "develop more",
"resume from GitHub", or requests a v0.18 development milestone.
This reference describes the **process**, not a fixed set of tasks.

## A. Inspect and choose a coherent batch

1. Read live `docs/project/STATE.json`, `docs/PROJECT_HANDOFF.md`,
   `docs/V018_COMPLETION_GATES.md`, `docs/DEVELOPMENT_PLAN.md` and
   `docs/future/CBDK-FUTURE-019-022.md`. Check `AGENTS.md`,
   current code, PR draft state and workflow runs.
2. Separate (a) safely automatable work, (b) tested but partially
   integrated functionality, and (c) work requiring permission,
   private data, GUI manual testing, licensing or release approval.
3. Select a **coherent unit** of implementation (for example, UI
   registration + schema checks + Blender smoke), not unrelated
   feature churn. Never close an issue just by changing status text.
4. If a branch/PR is changing concurrently, reconcile before editing.
   Preserve existing changes; commit only intended files.

## B. Implement then verify with minimal redundant runs

1. Add code and focused regression tests together. Prefer current
   allowlisted self-authored fixtures. Fix evidence-backed errors rather
   than adding tests that don't exercise the feature.
2. Run focused tests locally. Then use a **single** required CI matrix
   for the coherent batch where possible; rerun only failed / affected
   checks as appropriate. Skipped, canceled, stale-SHA and queued
   jobs do not count as success.
3. Inspect each required workflow separately. For GUI/Blender/GLB
   results, record the environment and what was genuinely verified.
   Real Chromium screenshots and Blender renders are distinct.
4. If tests cannot be executed in the available environment, leave
   them pending with exact commands rather than inventing passes.

## C. Update durable GitHub records

1. Record feature/requirement IDs in `docs/project/STATE.json` with
   accurate status (implemented/partial/not_implemented/deferred),
   verification and known limitations. Do not inflate requirement or
   task totals and do not use historical `last_verified` evidence as
   proof for a different code SHA.
2. Update `docs/PROJECT_SPEC.md`, `docs/DEVELOPMENT_PLAN.md`,
   `docs/V018_COMPLETION_GATES.md`, `docs/PROGRESS.md` and any
   focused module documentation only where facts changed.
3. Regenerate with `python scripts/project_handoff.py --write` and
   verify with `python scripts/project_handoff.py --check`.
   The generated handoff should not be hand-edited.
4. Commit the change and preserve the current draft PR unless
   explicitly authorized to merge/release. Recheck the final HEAD
   before citing code/test results. If documentation-only commits
   do not rerun CI, identify the earlier tested code SHA clearly.

## D. Mirror only established public-safe summaries to Notion

The existing [CBDK project page](https://app.notion.com/p/410948b7493781449462ca76e9567e75)
is a readable mirror; technical state remains in GitHub.

- Update an existing project/task page, preserving prior milestones.
  Do **not** create duplicate pages or imply an always-on sync service.
- Sync only verified task states, code SHA, CI URLs and public-safe
  limitations. No user source, private GLB, GLB-derived HTML, raw
  reports, paths or credentials.
- Fetch the destination and use its supported edit tools, respecting
  connector permissions and tool-specific formatting rules.
- After a successful response, record a GitHub sync receipt.
  Otherwise mark pending and explain; never claim success.
- No Notion connection? Finish the GitHub work and report that the
  mirror was not updated, without requesting unrelated access.

## E. Phase and approval gate

The v0.19–v0.22 plans may be preapproved for **starting after v0.18
completion gates**, but approved future scope is not active scope by
default. Do not artificially complete or defer v0.18 requirements.
Verify human blockers are documented and automatable gates are met
before activating a future plan under the existing transition policy.

A phase transition is separate from `main` merge, formal release,
unknown-code adoption, private source access, license decisions and
the expressly deferred direct GitHub-to-Blender installation.

## F. Compact report

Report: (1) shipped implementation / exact status, (2) code SHA,
PR, files, (3) actual test and CI evidence, (4) unchanged safety and
privacy boundaries, (5) Notion sync result, (6) next practical batch.
Say what was not verified rather than giving a percentage without a
stable denominator.
