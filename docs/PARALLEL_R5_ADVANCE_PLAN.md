# CBDK Rolling R5 — Coordinator A advance design (NOT authorized to implement)

Status: **design-only, provisional**. Prepared while Teams B/C/D implement R4. GitHub `feature/v0.18-shape-diagnostics` and current PR/CI are authoritative. This document is **not** a replacement for `docs/PARALLEL_ROLLING_QUEUE.md`. A will reconcile it after R4 CI and integration. Do not branch, code, or stack R5 until a fresh integrated R4 base SHA is assigned by A.

## Why this exists
Reduce idle gaps between R4 completion and R5 start. Keep three independent, small, testable backlog items ready without touching B/C/D code or shared STATE/HANDOFF/CI. Codex is optional; unavailability is never a stop condition.

## R4 integration gate — A checklist

1. Inspect exact HEAD SHA, base branch, changed paths, dependencies, draft status, and workflow jobs for each new R4 PR; an existing branch or a red TDD phase is not a finished PR.
2. Review team ownership: B only `cbdk/glb_*` and owned tests/fixtures/docs; C only `cbdk/ui_layout.py`, `cbdk/modular_builder.py`, `templates/modular_preview/` and owned tests/docs; D only `cbdk/extension_*` and owned tests/docs. Shared smoke, CI, STATE, HANDOFF, catalog and main remain A-controlled.
3. Verify cumulative changed files, possible overlapping source/API behavior, merge-base and identical old R1–R3 content. **Do not merge old PR #26–37 again**; R1–R3 code is already integrated through PR #38, code SHA `12ddcfeef935a805f7316ffb3698c141328aac88`.
4. Build an isolated new R4 integration candidate on current `feature/v0.18-shape-diagnostics` (including newer docs-only commits). Do not force-push any specialist branch. Do not assert that individual green CI proves combined green CI.
5. Require exact combined commit CI: Python 3.11/3.12/3.13, Windows Python 3.11/3.13, Blender 4.4.3/4.5.15/5.2.1, Chromium, durable handoff, and Kit/Skill if triggered or required by changed paths. Check each matrix job and test evidence. Distinguish not-run/cancelled/failure from pass.
6. Only after review and authorized v0.18 developer-branch integration update STATE, generated handoff, progress and milestone Notion. Never merge to main or release on CI alone. No real-user GLB/GUI/license/Extension verification is implied by synthetic CI.

## R5 candidate B — NEXT-008: budget boundary and deterministic uncertainty

**Precondition:** R4 B's resource-budget/ambiguous-case regression must be reviewed and integrated, not merely green on its individual branch.
**Failure-oriented scope:** Compare candidate decisions under equivalent synthetic part sets with reordered mesh/triangle input and small coordinate perturbations near the 256-boundary-edge and 512-face ceilings. Test whether cost guards are deterministic and fail closed without unstable suggested matches. Start from reproducible counterexamples, not a new heuristic.
**Allowed files:** `cbdk/glb_*`, GLB-owned tests, synthetic fixtures and GLB-owned docs.
**Acceptance:** bounded work (time/alloc observations are measurements, not performance guarantees); same input/reordering produces stable reason-code order and classification; budget or uncertainty remains `ambiguous`; prior R1–R4 negative/positive classifications preserved. If no missed failure is reproduced, tests/documentation only.
**Explicit exclusions:** real user/private GLBs, claims of true physical-hole identity, new automatic matching, common CLI, shared scripts/CI.

## R5 candidate C — UI-001/BUILD-001: generated preview lifecycle on native Blender

**Precondition:** R4 C's declarative UI plan vs operator/runtime refusal controls are green and integrated; native smoke extensions must be coordinated with A.
**Failure-oriented scope:** Synthetic authored preview repeatedly enable → execute allowed operation → switch object/edit mode → disable → re-enable after injected failure. Audit no leaked CBDK-owned registrations, no deletion of foreign Scene properties, no silently enabled invalid-context actions; measure advisory UI independently of operator's actual poll/execute. Include shared mesh/empty mesh negative states where supported by existing trusted previews.
**Allowed files:** `cbdk/ui_layout.py`, `cbdk/modular_builder.py`, `templates/modular_preview/`, UI-owned tests/docs. Changes to `scripts/blender_modular_addon_smoke.py` are A-owned requests only.
**Acceptance:** retain 5 features/6 recipes; any failure yields explicit disabled/rejected state, no foreign property mutation; three pinned Blender versions demonstrate native checks that can actually run headless. Do not mislabel mock failure injection as true native OOM/third-party conflict or Windows GUI verification.
**Explicit exclusions:** arbitrary operators, scanned private addons, automatic installation, release.

## R5 candidate D — EXT-001: validator compatibility and safe error provenance

**Precondition:** R4 D's valid legacy/modular positive fixtures and fail-closed negative fixtures are reviewed and integrated.
**Failure-oriented scope:** With CBDK-authored synthetic manifest/ZIP fixtures, verify fixed allowlist of known Blender 4.4.3/4.5.15/5.2.1 validator banner/status formats, stable sanitization, error separation, and repeatability across good ZIP / intentionally corrupted ZIP. Seek a concrete false-positive or false-negative before altering parser rules.
**Allowed files:** `cbdk/extension_*`, Extension-owned tests/docs. Shared validator CLI fixture script, CI, STATE, HANDOFF are A-owned.
**Acceptance:** valid preview retains `blocked_for_extension_release` rather than being mislabeled approved; invalid archives/logs cannot return complete diagnostic agreement; avoid raw paths, tokens, manifest values or private identifiers in outputs. Maintain tests for canonical ZIP safety from R2 and strict logs from R3.
**Explicit exclusions:** official publication, real package license clearance, unapproved code execution, authentication of logs without provenance.

## Allocation and no-idle protocol

- During R4: B/C/D work only on their respective R4 branches. A prepares integration/review and this R5 plan; this is *not* R5 authorization.
- After green R4 PRs: A checks exact SHAs and integrated CI, resolves ownership/API conflicts, decides v0.18 dev integration, then writes fresh R5 baselines and edits the canonical rolling queue.
- Only then: each specialist may create **one** dedicated R5 draft PR based on the new developer HEAD and targeting `feature/v0.18-shape-diagnostics`; no old R2/R3/R4 stacked-head reuse and no force-push.
- If any R4 is red, absent, or blocked: fix R4 or design tests read-only. Never infer success from branch existence.
- Any missing GUI, private GLB, licensing, rights or official package gate remains open and is not converted to an automatic completion claim.

## Team-A handoff table (to fill after actual R4 submission)

| Team | R4 PR | HEAD SHA | base SHA | Changed paths reviewed | Exact-head CI | Integration outcome | R5 go/no-go |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | pending | pending | pending | pending | unverified | not integrated | design only |
| C | pending | pending | pending | pending | unverified | not integrated | design only |
| D | pending | pending | pending | pending | unverified | not integrated | design only |

Source of operating rules: `AGENTS.md`, `docs/PARALLEL_DEVELOPMENT.md`, `docs/PARALLEL_ROLLING_QUEUE.md`, `docs/project/STATE.json`.
