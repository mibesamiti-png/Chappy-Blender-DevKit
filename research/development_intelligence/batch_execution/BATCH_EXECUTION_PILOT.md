# CBDK — Similar-work batching pilot (DIL proposal, not active policy)

2026-11-15 JST. **PROPOSAL ONLY:** this document is confined to the independent DIL research branch/PR #115. It does **not** modify `AGENTS.md`, the official R16 assignment, Issue #125, production code, common CI, STATE/HANDOFF, the v0.18 development branch, `main` or permissions. A must explicitly accept any later rollout through the normal quality gates.

## Motivation and hypothesis

The CFRL development discussion identified high overhead from treating each similar implementation or negative test as a separate user/agent turn. CBDK should try **one coherent objective, one common fixture, one bounded batch of related scenarios, one minimal implementation, one final evidence review**, rather than one PR/chat round per tiny scenario. This targets fewer chat turns, context handoffs and repeated setup/CI runs; **faster elapsed time and lower usage are hypotheses**, not measured CBDK results.

**Batch means several related scenarios within a single officially assigned B/C/D task. It does not mean merging roles, skipping approvals, bundling unrelated features, multiplying PRs, or silently converting proposals into permissions.**

## Preconditions and source hierarchy

1. Before every new task, read live `feature/v0.18-shape-diagnostics` HEAD, `AGENTS.md`, current accepted assignment `docs/Rxx_ABCD_START.md`, own draft PR and exact-head CI, and [Issue #125](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/issues/125). Current checked official assignment is R16 at dev `2b8220210c2475239a43354d544b5a6f176fba80` (as of 2026-11-15 check); this SHA is **not** a future-live assertion.
2. A remains sole owner of common CI/STATE/HANDOFF/official assignments/integration. Team B owns `cbdk/glb_*` and specialist tests; C owns UI/modular preview scope; D owns `cbdk/extension_*` and specialist tests. Honor exact ownership in the *current* official assignment, even if this template's examples differ later.
3. Issue #125 is an advisory router only, never an execution permit. Unknown/outdated/contradictory assignment => do not start a batch.
4. Existing five required exact-specialist-HEAD CI families, five combined-HEAD CI families and seven independent post-merge dev-HEAD workflow families are **unchanged**, including required real Blender 4.4.3/4.5.15/5.2.1 observations where applicable. A successful specialist job cannot replace combined or post-merge CI.
5. Research Geometry Lab #114 and DIL #115 remain independent and unmerged. Private meshes, third-party original addon sources, paths, user GLB or derived outputs must never enter public evidence or be executed without explicit separate permission.

## Batch grouping rule (key to the method)

Group scenarios only when all of these are true:

- **Same failure mechanism or invariant** to preserve (not merely the same folder/topic), e.g. "stale UI enable hints must not bypass live operator rejection".
- **Same owned code area**, compatible base HEAD and same A-defined deliverable/acceptance gate.
- **Same reusable fixture/oracle and resource envelope**, so results are meaningfully comparable.
- **One bounded patch** can fix the root cause for several related negative cases without broad refactoring.
- **Independent per-scenario results** can still be inspected, with failures retained, not averaged away.

Do **not** batch mixed permissions/licensing, cross-team files, uncertain dependencies, different CI gates, or radically different failure causes. Use a reasonable candidate window (e.g. 4–8 cases), **not a forced case quota**. If no defect is reproduced, deliver tests/evidence only and stop. Prioritize confirmed missing official acceptance conditions before inventing new experiments.

## Five internal stages in ONE task turn where feasible (R0–R4)

| Stage | Agent action | Durable result |
|---|---|---|
| R0 Scope | Resolve official task, one failure family, owned files, existing tests, expected invariants, acceptance limits | Short batch contract + skip/stop conditions |
| R1 Freeze | Freeze base HEAD, scenario IDs, seed, fixture and independent gold, resource/time/read budget and original checksums **before comparing changes** | Immutable baseline/evaluation protocol |
| R2 Implement | Add related table-driven fixtures/negative cases in one changeset, run baseline; apply only smallest root-cause change that genuinely helps | Focused implementation + per-case outcome |
| R3 Compare | Run positive + negative regression matrix under the **same** test setup; check output equality, unknown/refusal, repeatability, resource use and relevant Blender versions | Per-case measured A/B; no hidden failures |
| R4 Close | Run the specialist's required CI against **the exact final PR HEAD**, report evidence and untested cases to A once | One draft PR/update, a concise result table and decision |

A separate integration pass (A-only) verifies candidate HEAD + required five families, then one dev merge if authorized and independent seven post-merge families. B/C/D **never** merge or claim release readiness. R0–R4 are logical checkpoints, not five user prompts or five required GitHub PRs. The agent may proceed through them in one response/task if safe; if it hits red CI, uncertain permissions, missing fixture or resource limits, it must stop and report a concrete blocker. Do not fake continuing work or assume it is running after the turn ends.

## CBDK R16 examples (for understanding; not new authorizations)

- **B / GLB provenance:** one synthetic set covers stale revision, same self-claimed digest on different trials, missing basis, and mixed batch boundaries; verify `unknown/review_only` never becomes authenticity, edit authorization or license clearance. Only adopt tests/minimal code if R16 permits and findings reproduce.
- **C / generated UI:** one table-driven real-Blender test family covers `Panel.draw` enabled-state followed by mode change, deselection, foreign Scene and operator `CANCELLED`; assert no coordinate/Scene mutation; preserve existing five functions/six recipes; report each Blender version independently. Headless success is **not** proof of real Windows GUI/Undo.
- **D / Extensions:** one bounded synthetic timeline covers same-inode same-digest two-read windows with temporary rewrite/restore, unknown/reparse visibility, ZIP member/size quotas and seven known good previews as controls; never conclude continuous stability, external rights or public-release authorization from observed agreement.

If current R16 work is already drafted or CI-approved, **do not create a second R16 implementation task** on the strength of these examples. Use for the *next accepted* official assignment after A authorizes this pilot.

## Single common resume prompt for existing B/C/D chats

> 続けて。最新のCBDK開発HEAD、AGENTS.md、Issue #125、正式なRxx割当、担当PRとCIを取得。自分の既存担当範囲だけで、同一の失敗原因・fixture・検証条件を持つ関連ケースを一括実装・検証してください。R0(作業境界)→R1(条件固定)→R2(最小実装)→R3(同条件A/Bと正負例)→R4(担当PR/最終HEADで必要CI/一括報告)を、止まる条件に該当しなければ一度の作業内でまとめて進める。CI、Blender実検証、担当境界、A統合承認を省略しない。効果が再現しなければtests/docsのみで終了。正式割当がこの実験案を認めていなければ、従来手順を守り、提案のまま扱う。

This prompt is a *candidate*, not a replacement for live official assignment instructions. Existing chat cannot be remotely awakened by GitHub alone.

## Minimum batch result schema (plain Markdown/JSON summary in specialist PR)

- `base_dev_sha`, `specialist_head_sha`, `assignment_id`, `team`, `scope`, `batch_id`, `pr`.
- `scenario_ids[]` with frozen input, positive/negative label, expected invariant, observed output, per-case pass/fail/UNKNOWN, original checksum or other independent basis.
- `changed_files`, `root_cause`, `reproduced_regression`, `code_change_reason`, `unfixed_or_untested`.
- `resource_caps`, measured runs/bytes/time if relevant, `final_head_ci_urls[]`, version-specific test coverage, security/privacy gate evidence.
- `chat_turns`, `manual_user_interventions`, `PR_count`, `CI_run_count`, `elapsed_walltime` **only when actually recorded**.
- `can_merge=false`, `may_skip_ci=false`; A-only final decision.

## Proposed pilot and scoring (A approval required)

1. Keep **current R16 work and draft PRs intact**. A selects one small family in each team's *next accepted assignment* and records a single batch in the official dispatch. Ownership and CI unchanged.
2. For one or two short batches, compare historical similar tasks (only descriptive, not matched causal data) on chat turns, elapsed wall-clock time, duplicated setup/test work, unique bugs found, missed negative cases, CI failures, PR count and human intervention. If actual usage quota is not directly observed, mark `usage=unavailable` (do not estimate).
3. **Pass** only when all mandatory per-case gates and CI are green, no new safety/privacy regression, and measured setup/turn reduction is meaningful. If evidence is inconclusive, keep `research_only`; if patch scope or reviewer workload grows or independent tests regress, **rollback** batching for that family.
4. A records a brief decision and may enable per-team batch scope explicitly. If A does not approve, continue existing non-batched R16 workflow.

**Decision now:** research-only proposal prepared; no activation, official queue edits, CI change or observed benefit from CBDK yet.
