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

## GLB roadmap restored from the prior chat on 2026-11-07

- Source: [GLB-019 through GLB-022 roadmap](GLB_ROADMAP.md), canonical [STATE.json](project/STATE.json) and generated [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md).
- [GLB-019](https://app.notion.com/p/410948b7493781e888acd4392249365d): implemented / Blender synthetic CI; real-world GLB scalability and full geometry identity are not proven.
- [GLB-020](https://app.notion.com/p/410948b7493781f7a88cf4781588ee25): **partial / blender_ci**. Implemented an opt-in color-coded pair of GLBs and aggregate JSON; Python, Windows, Blender 3-version, kit and handoff workflows succeeded for code SHA `91e8b6a2` (2026-11-07 handoff). Selectable anonymized mesh parts and per-part color counts are now implemented and Blender3-version CI-verified (SHA `7365828b`, run `42265921506`); an offline synchronized dual-3D HTML viewer is now implemented and CI-checked (test SHA `b5d1d27`, Blender run `42268088779`; all 5 workflows succeeded). Actual browser GUI interaction, cross-file matching, unknown-area labeling, large meshes and user GLB tests remain open. Private viewer HTML contains derived geometry and must remain local.
- [GLB-021](https://app.notion.com/p/410948b7493781efb123c459b521312e): not_implemented / not_tested; relate difference categories to review-only property candidates.
- [GLB-022](https://app.notion.com/p/410948b74937811ea006d4d6bd55b1dc): not_implemented / not_tested; iterative experiments using only allowlisted CBDK-owned synthetic addons.
- Sequence: **GLB-020 → GLB-021 → GLB-022**. The roadmap is a plan, not a release or CI claim.


## GLB-020 phase 4: conservative matching and real-browser CI

- The offline viewer now provides manual, uncertain spatial part suggestions. Correspondence is **not proven**, no geometry or addon settings are automatically changed, and private derived HTML stays local.
- At code SHA `72e9bd4e4ad2cb9b9716ee0cb5ea10de60cd779e`, all six workflows succeeded: [Python 42274183982](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183982), [Windows 42274184368](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184368), [Blender 42274184086](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184086), [kit 42274184021](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184021), [handoff 42274183990](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183990), [Chromium GUI 42274183979](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183979).
- Browser CI checked only a synthetic two-part model; actual part identity, complex occlusion, private/large GLBs and unknown unmeasured surfaces remain unresolved. GLB-020 remains **partial**, GLB-021/022 remain **not implemented**. Keep Notion mirrored to the same state.


## GLB-020 phase 5 — incremental sampling sensitivity (2026-11-07)

- Added a bounded extra 24 Halton probes per triangle. Purple outlines in the private offline HTML mark **observed increases** in sampled error; absence of purple is explicitly **not** full coverage. Aggregate-only JSON stores per-part and total sensitivity counts, no raw vertices/names.
- コードSHA `38057b1da49eeb61020664c4923ced2b2bad8406`： [Python 42279824321](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824321)、[Windows 42279824307](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824307)、[Blender 4.4.3/4.5.15/5.2.1 42279824378](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824378)、[Windows kit 42279824398](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824398)、[引き継ぎ 42279824427](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824427)、[Chromium GUI 42279824304](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824304) **全6系統success**。
- Real Chromium smoke used a synthetic test flag for toggling behavior. The numerical criterion has separate Python tests. Exact missed holes, internal volumes, real user GLBs and definitive part identities remain **unverified**. GLB-020 stays **partial**.

## GLB-020 phase 6 — conservative edge-topology observations

- Anonymous per-part coordinate-welded triangle edge incidence is added to the review-only `review.json` and offline viewer part selector; source coordinates/names are not stored in aggregate JSON.
- Observed mismatches in boundary/nonmanifold edge state demote confident spatial part suggestions to `ambiguous`. No exact part matching, hole identity or parameter cause is proved. Private viewer HTML and colored GLBs remain local.
- The tested synthetic closed-vs-open tetra GLB comparison and CI outcome should be recorded in Notion with the code SHA. GLB-020 stays `partial`, GLB-021/022 remain `not_implemented`.

### Phase-6 exact tested SHA

コードSHA `2cec6c99082107a4f2a65459f36f641b189f3bc5` の [Python 42284401645](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401645)・[Windows 42284401719](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401719)・[Blender 4.4.3/4.5.15/5.2.1 42284401757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401757)・[Windowsキット 42284401594](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401594)・[引き継ぎ 42284401833](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401833) は全て success。 [Chromium 42284401610](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401610) は別途結果確認中。

GitHub is the technical source of truth; the Notion GLB-020 task remains 'in progress' and GLB-021/022 remain unimplemented. This evidence is limited to synthetic Blender tetrahedron cases and test harnesses, not arbitrary private user data.

## GLB-020 phase 7 — local-only cyan 3D boundary overlay

- Approximate world-space observed open-edge segments are shown in cyan in the synchronized local HTML viewer. Per-side and per-part toggle is available. **The derived line coordinates never enter review.json or Notion**; private HTML and GLBs stay local.
- テスト対象のコードSHA `2a2bc8c33aaf4d11811e7892a8bbc51542b316b4`： [Python 42286544157](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544157)、[Windows 42286544061](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544061)、[Blender 4.4.3/4.5.15/5.2.1 42286543992](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543992)、[Windowsキット 42286543968](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543968)、[引き継ぎ 42286543977](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543977)、[Chromium実GUI 42286544018](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544018) **全6系統成功**。
- Synthetic Blender tetra checks and headless Chromium overlay toggle are confirmed for the tested code SHA. These do not certify real-world hole detection, internal cavity equivalence, part identity, true occlusion or private GLB performance. Keep GLB-020 partial and GLB-021/022 not implemented.

## Milestone update checklist

1. Inspect the latest PR commit and changes; execute or inspect the relevant Python/Windows/Blender CI.
2. Update `docs/project/STATE.json` and generated `docs/PROJECT_HANDOFF.md` using the existing project process. Keep requirement IDs, statuses, verification levels, known issues, decisions and next actions consistent with tested evidence.
3. Update the existing specification, progress log and PR description only as warranted; preserve draft/release boundaries and commit SHA evidence.
4. Update the **same** Notion CBDK project and task pages, rather than duplicating them. Record the task ID, actual status, exact tested SHA, CI run URLs and restrictions. Close tasks only after acceptance is evidenced.
5. Compare GitHub and Notion statuses and report any partial update / connector failure. Do not assert synchronization when one side was not written.

## Next work

Continue from PR #25 and its `docs/project/STATE.json` / generated handoff; prefer the next validated synthetic GLB geometry-diagnostics step before claiming arbitrary addon auto-repair. Confirm CI at the most recent commit prior to any release decision.
