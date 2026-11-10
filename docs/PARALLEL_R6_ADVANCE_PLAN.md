# CBDK R6 advance design — Coordinator A (PROPOSAL ONLY)

Prepared 2026-11-08 JST while R5 combined integration candidate [PR #49](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/49) undergoes verification. **Not authorized as R6 work** until A proves merged R5 code has successful required combined and post-merge CI and updates canonical `docs/PARALLEL_ROLLING_QUEUE.md`. Do not branch, implement, force-push, or start a second unintegrated PR for R6 now.

## Required R5 gate

- Source B [#47](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/47), C [#48](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/48), D [#46](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/46). Each source R5 SHA had five green families; this does **not** prove their combined tree.
- A has integrated nine disjoint specialist paths into isolated R5 [#49](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/49), plus A-owned shared Blender CI invocation of C's new standalone native UI lifecycle regression.
- **First #49 head `b300e74356848ffbd9131c2c0d651991f7c10cbf` was RED on all three Blender versions**, because the new native probe incorrectly assumed invalid-mode operators were hidden rather than present-but-disabled. A test-only correction was committed as `106bf2504923346ac4cd25b51ebaaa87da9e7d7b`; do not claim its Blender results without checking actual jobs. Never erase the first failure from records.
- Explicitly require `CBDK_R5_UI_LIFECYCLE_PASS` in each Blender 4.4.3/4.5.15/5.2.1 job; ensure tests validate real Blender's state and do not assert a mock result as native evidence. Fix any subsequent failure narrowly, recheck exact SHA all required workflows.
- Merge only to `feature/v0.18-shape-diagnostics` after green combined CI and safety review; verify all seven post-squash dev-sha workflow families before activating R6. Retain `main`, released 0.17.0, private addons/GLBs, Windows GUI and license/official Extension gates unchanged.

## Candidate R6 — B (GLB review bounded fast-path investigation)

Aim: reduce R4's high observed 256-open-edge synthetic matching time while **not** weakening the R2 spatial distance or R3 boundary component controls. Design and benchmark a bounded, canonical, *undirected* equal-boundary-segment signature as a possible **early accept for exact equivalent observed contours only**. On any mismatch, float32 scale ambiguity, disconnected component discrepancy, or resource-budget uncertainty, use existing spatial review and keep ambiguous/fail-closed semantics. Do not equate a contour hash with true part identity or introduce auto-apply. Test rotated/reversed segment order, translated/scaled geometry, re-triangulation, near-gap and 255/256/257 edges, 64 parts / 512 faces. Observe robust per-Blender and Python metrics without making a latency guarantee. If evidence does not show a useful safe speedup, keep test+design only.

Owners: `cbdk/glb_*`, B-specific tests/fixtures/docs. Any shared GLB Blender smoke or workflow changes are A-owned.

## Candidate R6 — C (native Scene ownership and lifecycle adversarial follow-up)

After R5's new native script actually passes on all three Blender versions, widen *trusted authored* Blender negative tests to cover scene property ownership, class identity and lifecycle transitions under: repeated addon module reload, descriptor replacement, foreign shadow/inherited property, explicit register exception recovery, mode switch with Edit mesh and shared datablock. Prove no deletion of foreign properties, no leaked CBDK classes/tokens, no mesh mutation when operator is invalid. Treat Blender headless as evidence for headless runtime only — **not Windows GUI mouse/Undo hotkeys or actual external-addon interoperability**. Fix smallest concrete reproduced issue, otherwise tests only. Preserve exact five features, six authored recipes and strict preview-only status.

Owners: C-specific `templates/modular_preview/`, `cbdk/ui_layout.py`, `cbdk/modular_builder.py`, tests/docs. A owns `scripts/blender_modular_addon_smoke.py` and common CI; C may add narrowly scoped dedicated native fixture when A explicitly approves its invocation.

## Candidate R6 — D (bounded extension ZIP/parser input boundary matrix)

Bounded, synthetic, data-only tests for archive total size/member size/member count and truncated local/central directory records, plus official validator log length at its existing 200,000-character limit, unknown/duplicate/contradictory lines, and sanitized outputs. **Do not raise resource limits or relax unknown-message rejection without observed official evidence.** Pair every negative with R4's seven healthy authored preview ZIP positives and existing three-Blender-version official validation checks. Prefer no production changes if no defect. Preserve status `blocked_for_extension_release`, no attribution/rights inference or actual untrusted ZIP execution.

Owners: `cbdk/extension_*`, D-owned tests/docs; official validator script/shared CI/STATE are A-owned.

## Next coordinator action

Once R5 integrated and post-merge 7 CI families validated, A updates canonical rolling queue with final R6 base branch/head SHA, one R6 draft per specialist (`work/v018-glb-analysis-r6`, `work/v018-ui-builder-r6`, `work/v018-extension-quality-r6`) targeting `feature/v0.18-shape-diagnostics`, acceptance negative cases, current dependencies and ownership. Then publish source-of-truth STATE, generated handoff, PROGRESS, and existing Notion milestone mirror. Codex remains optional. No automatic release/main merge, licensing decision, actual private data execution, or v0.19 activation.
