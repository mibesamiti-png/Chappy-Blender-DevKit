# Team A — R7 acceptance gates and R8 advance research (DESIGN ONLY)

Prepared 2026-11-08 JST. Source of truth: `docs/PARALLEL_ROLLING_QUEUE.md` on `feature/v0.18-shape-diagnostics`. This document **does not authorize R8**, does not supersede the canonical queue or state, and must not be merged to `main`. At creation the authoritative developer baseline is `a857e1c2e4cc3e0d61b274cf7984625dcac5d40a`, with R6 code `e2f09e593d9c7bdff66695c7e8972eea98e160ca` ancestral. User-provided private sources, arbitrary addons, real-world GLBs, Windows GUI behavior, licensing and release gates stay unverified.

## R7 inbound acceptance checklist (A before any integration)

1. Discover current B/C/D R7 PRs; **do not mistake open historical R6 source PRs #53–#55 for new R7 submissions**. If R7 PR absent, no team integration attempted. Specialist max one unintegrated new PR. Confirm team identity, exact head SHA, latest dev base ancestry, draft status and changed-file ownership.
2. B: mathematically/adversarially check R6 exact undirected contour shortcut against changes in segment tessellation, near-zero-length segments, duplicated motifs and near-equal float32; require both R2 conservative fallback and R3 independent connected-component guard even if canonical signature equals; ensure no implicit part-identity claim or auto-apply. Assert bounded 256-edge work; distinguish synthetic matcher-only speed from GLB import/export time.
3. C: ensure **actual native Blender CI calls** any R7-specific registration/teardown tests; a test file existing is insufficient. Confirm headless 4.4.3, 4.5.15 and 5.2.1 jobs emitted unique R7 markers. Check failed class-register recovery, foreign Scene descriptor preservation, mode transitions, unchanged input mesh, five features/six authored recipes, and safe re-registration. Avoid asserting real UI/Windows hotkey coverage.
4. D: inspect TOML manifest parser's actual 32 KiB/64-field meaning before setting boundary expectations (count bytes vs Python code points, unique field keys vs recursive nested keys). Test invalid UTF-8, duplicate TOML keys, nested unexpected values and output symlink/path refusal **with data-only fixtures**. Do not replace fixed valid authored ZIP or official validator positives; keep release blocked and owner/rights unapproved.
5. All specialists: exact-head five CI families success (Python3, Windows2, Blender3, Chromium, Handoff), Kit/Skill only if triggered. Inspect actual logs for newly introduced native probes. Re-review full diff; require no cross-team file collisions. Do not infer a passed result from a prior SHA.
6. Construct isolated A integration branch based on **latest** `feature/v0.18-shape-diagnostics`. Copy exact specialist changed paths, never merge older historical sources. Add A-owned common smoke invocation only if a new test is otherwise not executed. Obtain combined exact-head CI evidence and review before dev merge.
7. After dev-only squash merge, verify **seven post-merge CI families**, including Kit and Skill, and preserve first failure/retry records. Only then update canonical rolling queue with R8 exact current base, release gate status, STATE/Handoff/PROGRESS and existing Notion mirror.

## R8 candidate research (not assignment)

### Team B — GLB match anti-collision and bounded verification

Design a *negative-evidence* review protocol to explain when exact-contour fast-path decisions cannot be promoted to semantic part identity: coincident contours on geometrically different interior meshes, duplicate repeated part motifs, changed surface normals/material/group splits, and unit/transform ambiguity. Ensure independent R2 and R3 checks remain; optionally add synthetic report-level differential confidence fields only after schema review (no unapproved report mutation). Compare fallback and exact paths across Python/Blender versions using stable, capped fixtures. **No geometry auto-apply.**

### Team C — generated addon operator transaction/undo safety, headless only

Investigate failure-atomicity for authored preview operators: if validation/exception occurs between mesh selection and mutation, assert no partial mesh edits, no stale active object or leaked registered Scene properties. Make a synthetic Blender-native fixture for successful edit + operator cancel + unregister/re-register and compare object/mode/selection states. Headless `bpy.ops.ed.undo()` may have environment-specific behavior; never equate it to verified GUI shortcuts or user workflows. Keep external addon execution off.

### Team D — manifest/Extensions provenance boundary trace

Design a static evidence report that keeps **build validity**, **official validator output**, **author consent**, **license attribution** and **release authorization** as independent facts. Use only CBDK-authored samples, no untrusted code execution. Add malformed archive/path entries and disallowed provenance cases if they expose observable issues. Unknown or conflicting validator messages remain blocked. No installing/issuing official Extension.

## Coordinator operational efficiency

- B/C/D develop in parallel; A uses idle time for acceptance-test review and R8 design, not premature branching/merging.
- Separate completed code round from milestone-document round. Require exact SHA gate for both; document any Windows CRLF/STATE-size regression with its observed failure and corrected runs.
- Maintain historical open R1–R6 specialist PRs as source references only. Any potential cleanup/closure needs dedicated review and must not accidentally merge or discard specialist work.
- Never change `main`, published v0.17.0, private inputs, release permissions or canonical task queue from this preparatory branch.

**Next A action:** as R7 specialist PRs appear, check head SHA + job evidence, review per-team changed paths and ownership, then create the R7 integration candidate. Until then, this plan remains a draft and no R8 work is activated.
