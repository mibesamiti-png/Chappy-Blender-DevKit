# CBDK × Notion development sync

Last handoff: 2026-11-07 JST.

## Purpose and authority

- GitHub remains the **technical source of truth**: `docs/project/STATE.json` (canonical machine-readable state), generated `docs/PROJECT_HANDOFF.md`, `docs/PROJECT_SPEC.md`, `docs/PROGRESS.md` and `AGENTS.md`.
- Notion is the **human-friendly mirror** for project status and actionable tasks. A Notion status does not replace a GitHub code review, test result, or release.
- Updates occur **during an active development conversation / work session, at milestones**. There is currently **no always-on webhook or autonomous scheduler**; do not imply updates happen while no work is running.

## Current milestone sync (2026-11-07 JST)

- Current canonical state: [development branch STATE](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/blob/feature/v0.18-shape-diagnostics/docs/project/STATE.json). Earlier snapshots below are history.
- Existing project and GLB-019/020/021/022 task pages are accessible through the Notion connector; no connection setup is required for this session.
- GitHub source inventory/count hints at code `e254aa7` have all six workflows successful. Report-integrity code `31bf3de18c357d796194dcac369c66e55b3973bf` passed all six workflows: Python707 tests x3 (`42359722780`), Windows2 (`42359722774`), Blender3 (`42359722777`, all four new inventory cases), Kit (`42359722842`), Handoff (`42359722778`), Chromium (`42359722853`). GLB-019 implemented/blender_ci; GLB-020/021/022 remain partial.
- Sync status: **pending final CI reflection**. Existing project and all four GLB tasks were updated successfully with interim status; now reflect the successful code CI after saving this GitHub evidence. No new pages, private sources/models/reports, or personal data are included.
- At every milestone: save canonical state and observed evidence on GitHub, update existing Notion records, then record the actual outcome here and in STATE. On connector failure leave pending with a reason and retry target; never mark unsaved changes synchronized.
- If a future session has no Notion connection, connect Notion in the client Apps settings using the intended workspace and grant access to these existing pages; retry fetch before writing. Never request credentials in chat.

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

## GLB-020 synthetic joint MVP acceptance — scope freeze (2026-11-07)

- The GLB-020 **review MVP acceptance gate** passed a 3-mesh synthetic ball/socket/shaft regression covering identical, narrower opening, shifted ball, and deleted lip faces. First negative-control failure exposed an *actually uncapped synthetic shaft*; fixture caps were added without relaxing diagnostics.
- 最終テスト対象コード SHA `db33ce4242bbe98b3c5f9ac43d89bf21c3657089`：
[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898364)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898499)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898512)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898604)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898325)・[Chromium実GUI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898701) **全6系統成功**。
- Synthetic source SHA-256 integrity, aggregate-only JSON, modified-part-only observations and bounded Blender3 versions were verified.
- **GLB-020 remains `partial` for full precision scope, but `NEXT-018=done` for its MVP acceptance.** Freeze optional GLB-020 elaborations; prioritize GLB-021 then GLB-022. Both remain not implemented. No real user/private GLB has been tested. Derived HTML and GLBs are geometry-bearing and local-only.

## GLB-021 first-stage visual-to-AST review-only linkage (2026-11-07)

- The new `glb-visual-property-review` consumes aggregate-only anonymous GLB-020 observations, reads **only explicitly selected** source Python AST, and reuses static declaration/reference/geometry-flow evidence. Human `--role` hints are unverified; no actual Blender property registration, cause, parameter value or part identity is proved.
- Private AST mapping report stays under local ignored `reports/latest`; CLI stdout redacts property names, source paths, defaults and raw mesh details. Original addon/GLB never executed or modified.
- コードSHA `8c51a867415738dcca6616a4a197b62a105075e5`： [Python 42292708122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708122)、[Windows 42292708128](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708128)、[Blender 4.4.3/4.5.15/5.2.1 42292708248](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708248)、[Windows Kit 42292708114](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708114)、[引き継ぎ 42292708111](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708111)、[Chromium実GUI 42292708124](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708124) **全6系統success**。
- GLB-021 is now **partial / blender_ci**, next action `NEXT-019=in_progress`; GLB-020 remains partial with MVP accepted/frozen, GLB-022 remains not implemented, and v0.18 PR #25 remains draft. This synthetic CI does not validate arbitrary real user GLBs/addons.

## GLB-021 second-stage human review sheet (2026-11-07)

- The opt-in `--markdown` command creates a private Japanese decision checklist next to its AST matching JSON. The sheet separates GLB-020 sampled observations from AST declaration/reference hints and states causal and numeric uncertainty explicitly.
- Both JSON and Markdown stay under local untracked `reports/latest`; no addon source code, original paths, default values or derived geometry may be committed or mirrored to Notion. Local candidate identifiers and line numbers are potentially private even without source text.
- Synthetic identical/narrowed/moved/uncapped joint CI now checks the Markdown report, and Python tests reject unsafe flags and path/overwrite attacks. Record exact successful workflow SHA and run IDs only after verification.
- GLB-021 stays partial, GLB-022 not implemented, and GLB-020 has MVP accepted/frozen.

## GLB-021 review Markdown evidence ordering (2026-11-07)

- `--markdown` creates a **private local** Japanese human-review sheet. Candidate display order is checkability (syntactic geometry route → attribute reference → declaration only), never proven cause probability or recommendation strength.
- コードSHA `af8e873a613b6b3075448db11f8f26c860dba2a4`：[Python 42296654049](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296654049)、[Windows 42296653825](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653825)、[Blender 4.4.3/4.5.15/5.2.1 42296654171](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296654171)、[Windows Kit 42296653959](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653959)、[引き継ぎ 42296653876](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653876)、[Chromium 42296653807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653807) **全6系統成功**。
- GLB-021 remains partial; GLB-020 MVP is frozen and GLB-022 remains unimplemented. Private candidate/property declarations and derived data must never enter public GitHub/Notion.

## GLB-021 fixed-synthetic-parameter counterfactual (2026-11-07)

- Known CBDK-owned synthetic socket opening values 0.78 (observed defect) and 1.70 (restored) were compared against a decoy unrelated ball movement. The narrowed socket remains different under the decoy; restored synthetic socket has zero observed medium/high faces.
- テストコードSHA `3b553039968e982e973d10d3427bf0607bbad88d`：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028446)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028346)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028811)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028286)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028673)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028338) **全6系統成功**。
- This evidence proves only the controlled synthetic generator behavior and SHA-256 invariance. **It does not certify a real user's Blender addon parameter or advise them to set 1.70.** GLB-021 remains partial, GLB-022 not implemented, private data stay local.

## GLB-021 synthetic trial history (2026-11-07)

- Built `cbdk/glb_synthetic_trial_history.py` to compare exactly three allowlisted CBDK-owned synthetic GLB-020 reports: defective socket (`narrow`), unrelated-ball-placebo (`narrow_placebo`), and known restored socket (`identical`). Outputs only bounded, anonymous per-part yellow/red counts and test-only control parameters in private local `synthetic_trial_history.json` and Japanese `synthetic_trial_history.md`.
- Unsafe names, fake proof flags, contradictory counts and existing destination files are rejected. Real user sources/addons are not run or edited; a drop in observed error faces is not a proof of complete model equivalence or an appropriate actual joint parameter value.
- Code SHA `ece5b0a6c6bc5ec03e1b8f54687bd4bdd4462a4f` verified by Python run `42299997255`, Windows `42299997246`, Blender 3-version `42299997251`, Windows kit `42299997311`, handoff `42299997254`, Chromium `42299997355` — **all success**. Exact code SHA is distinct from later docs-only commits.
- Keep GLB-021 partial, GLB-020 accepted MVP/frozen, GLB-022 not implemented, v0.18 PR #25 draft, formal v0.17.0 unchanged. Never publish private GLB/HTML, local history reports or unapproved AST property names to Notion.

## GLB-022 bounded synthetic regeneration loop (2026-11-07)

- Added a **real** Blender regeneration/comparison loop for exactly two predefined CBDK-owned synthetic candidates. The unrelated ball move is rejected; restoration of the known synthetic socket setting is accepted; observed zero sampled error stops the run.
- Implementations: `cbdk/glb_synthetic_iteration.py`, `scripts/run_glb022_synthetic_iteration.py`, tests `tests/test_glb_synthetic_iteration.py`. History with steps, decisions and stop reason is stored in local synthetic CI-only JSON and Japanese Markdown. No real addon code execution, no private GLB upload, no source overwrite; input SHA-256 checked.
- テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`：[Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)・[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)・[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)・[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)・[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)・[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。
- **GLB-022 status: partial / blender_ci**. This is a **fixed two-trial synthetic test**, not an arbitrary addon optimizer, not a verified cause on users' code, and not proof of exact geometry. GLB-020 stays accepted MVP/frozen and GLB-021 partial. Formal v0.17.0 remains unchanged and v0.18 PR #25 stays draft.

## GLB-022 fixed synthetic generate/compare/accept/reject loop (2026-11-07)

- Added a strict two-attempt generator/comparator for **CBDK-owned synthetic** three-part fixtures only; fresh actual Blender GLBs are generated for each candidate. The unrelated-ball decoy is rejected; known synthetic restoration is accepted. Stop at sampled zero, with no other-part regression.
- All derived geometry and private outputs remain local, source fixture generator/GLBs SHA-256 unchanged, aggregate-only accepted/rejected history is written to new JSON/Markdown without overwrites. No arbitrary addon, private user code or real GLB execution.
- テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`： [Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)、[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)、[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)、[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)、[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)、[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。
- GLB-022 is **partial / blender_ci**, not implemented for arbitrary user addons or optimizers. GLB-021 partial, GLB-020 review MVP accepted/frozen; formal v0.17.0 unchanged and v0.18 PR #25 draft. Avoid uploading private derived GLB/HTML or user AST output to Notion.

## GLB-022 cross-part three-candidate synthetic experiment (2026-11-07)

- CBDK-owned synthetic three-part models are freshly generated for 3 candidate trials. `narrow_placebo` rejected because socket does not improve; `shifted` rejected because the ball gets worse despite socket improvement; `identical` accepted with sampled zero and no other-part regression. Legacy 2-candidate test remains running.
- Fail-closed 1/2 iteration budgets, strict candidate IDs and no forged or private history data; JSON and Markdown remain local. No actual user addon code or private GLB is run or changed.
- コードSHA `d8d233e801b4da33f5f79cf6983818cefdca918c`：[Python 42305594556](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594556)、[Windows 42305594566](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594566)、[Blender 4.4.3/4.5.15/5.2.1 42305594589](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594589)、[Windows Kit 42305594635](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594635)、[引き継ぎ 42305594684](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594684)、[Chromium 42305594551](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594551) **全6系統成功**。
- GLB-022 remains partial: this is a three-candidate synthetic test, not an arbitrary optimizer. Preserve GLB-021 partial, GLB-020 MVP frozen, formal v0.17.0 and draft PR #25.

## GLB-022 progressive synthetic sampled-distance acceptance (2026-11-07)

- A new allowlisted mid socket diameter 1.24 is tested between defect 0.78 and known-restored 1.70; a mid-with-displaced-ball negative control is rejected for other-part regression. Mid alone is accepted as **partial progress** based on the aggregated two-way sampled maximum distance, then restored synthetic geometry reaches sampled zero and stops.
- This is a global sampled maximum, not an exact Hausdorff metric, not a per-part distance, not a real-user parameter recommendation. Private GLB/HTML, user code and reports never leave local CI workspace.
- テスト対象コードSHA `44e15f8f6664fe29e06810fd06d8d73dda70bec6`：[Python 42307811087](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307811087)、[Windows 42307810687](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810687)、[Blender4.4.3/4.5.15/5.2.1 42307810797](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810797)、[Windows Kit 42307810828](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810828)、[Handoff 42307811040](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307811040)、[Chromium 42307810743](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810743) **全6系統成功**。
- GLB-022 remains `partial`/Blender CI; GLB-021 partial; GLB-020 MVP freeze and v0.17.0 current release, v0.18 PR #25 draft remain unchanged.

## GLB-022 bounded generated arithmetic grid (2026-11-07)

- Introduced generated synthetic numeric socket values: CBDK-owned fixed interval 0.78..1.70 split arithmetically into 4 candidates 1.01,1.24,1.47,1.70. Trusted Blender generates each new GLB for the controlled candidates and GLB-020 compares sampled distance; stagnation is rejected, 1/2/3 budget is incomplete, and 1.70 known reference reaches sampled zero.
- Private geometry and locally generated history stay under ignored `reports/ci`. No user addon code or private GLB is executed or modified. This is a bounded fixed arithmetic grid, NOT adaptive general optimization or proof of surface equivalence.
- テスト対象コード SHA `23e9dec5d313468a70cc3bab7a5bb57fc090a8b3`：[Python 42309145079](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145079)、[Windows 42309145003](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145003)、[Blender4.4.3/4.5.15/5.2.1 42309145076](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145076)、[Windows kit 42309145019](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145019)、[引き継ぎ 42309145005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145005)、[Chromium 42309145006](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145006) **全6系統success**。
- Keep GLB-022 partial, GLB-021 partial, GLB-020 MVP frozen; formal v0.17.0 and draft v0.18 PR #25 unchanged. CI SHA is for source tests; docs-only commits are not a new code verification.

## GLB-022 adaptive bounded synthetic feedback loop (2026-11-07)

- New bounded adaptive bisection on **CBDK-owned synthetic socket fixtures only**. Feedback on aggregate GLB-020 global bidirectional sampled maximum against hardcoded test target 0.12 changes the next 0.01-step candidate, under max 4 trials; local history distinguishes measured target-feasible value from any proven optimum.
- Blender 3-version actual generated/compared path was 1.24→1.47→1.35→1.41; 1.47 was within the synthetic test target and the final bracket remained 1.41..1.47. Python counterbranch changes measured outcome at 1.24 and selects 1.01 next. No user addon or private GLB is opened, executed, modified, or uploaded.
- テスト対象コードSHA `37ee124aabb44df5ad9cb246342712bd9e0eb2ef`：[Python 42311608904](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608904)、[Windows 42311608916](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608916)、[Blender4.4.3/4.5.15/5.2.1 42311608910](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608910)、[Windows Kit 42311609353](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609353)、[引き継ぎ 42311609070](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609070)、[Chromium 42311609211](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609211) **全6系統success**。
- GLB-022 remains partial; formal v0.17.0 and draft PR #25 unchanged. Do not claim complete shape equivalence, part identity, exact Hausdorff distance, a real-user setting recommendation, or manufacturing tolerance.

## Milestone update checklist

1. Inspect the latest PR commit and changes; execute or inspect the relevant Python/Windows/Blender CI.
2. Update `docs/project/STATE.json` and generated `docs/PROJECT_HANDOFF.md` using the existing project process. Keep requirement IDs, statuses, verification levels, known issues, decisions and next actions consistent with tested evidence.
3. Update the existing specification, progress log and PR description only as warranted; preserve draft/release boundaries and commit SHA evidence.
4. Update the **same** Notion CBDK project and task pages, rather than duplicating them. Record the task ID, actual status, exact tested SHA, CI run URLs and restrictions. Close tasks only after acceptance is evidenced.
5. Compare GitHub and Notion statuses and report any partial update / connector failure. Do not assert synchronization when one side was not written.

## Next work

Continue from PR #25 and its `docs/project/STATE.json` / generated handoff; prefer the next validated synthetic GLB geometry-diagnostics step before claiming arbitrary addon auto-repair. Confirm CI at the most recent commit prior to any release decision.
