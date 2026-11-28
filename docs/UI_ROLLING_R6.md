# Team C R6 — Blender registration state, module reload and guarded geometry

**Task:** UI-001 / BUILD-001 R6, per the updated coordinator-owned `docs/PARALLEL_ROLLING_QUEUE.md`. Fresh base is the latest `feature/v0.18-shape-diagnostics` after integrated R5 [PR #49](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/49) (`a1c2f84715acce1f8cd33abaf003556708c13c07`); post-merge seven-workflow CI was independently green. This change is **Team C only** and does not re-merge old PRs.

## Failure being prevented

`importlib.reload(module)` executes the generated package's top-level source again in the **same module dictionary**. The prior preview template reassigned `_REGISTERED=[]`, `_OWNED_PROPERTIES=[]` and `_OWNED_PROPERTY_TOKENS={}`, regardless of whether Blender operator classes or Scene declarations were still live. A reload while registered could therefore orphan live registrations and cause a subsequent unregister to lose its ownership evidence.

R6 adds an early, fixed preflight after the trusted imports and **before** feature imports/class definitions/ledger initialization: if *any* ownership ledger is nonempty, the reload raises a controlled RuntimeError advising unregister first. A fresh import and a reload after successful detach are still permitted. This is a **specific guard for importlib.reload**; it does not promise recovery from arbitrary custom Python re-execution, process termination, OOM or untrusted module tampering. Existing R3/R5 descriptor-identity checks remain unchanged.

## New actual Blender negative cases

The **C-owned** `tests/blender_ui_lifecycle_r5.py`, already invoked by the **A-owned** Blender 3-version CI on every pull request that changes `templates/modular_preview/**`, now includes five R6-specific assertions in addition to all previous R5 checks:

1. `native_r6_shared_mesh_nudge_refused_no_mutation` — create a second unselected Blender object sharing a single authored triangle datablock; in Edit Mesh with vertices actually selected, nudge is disabled/refuses due to shared `mesh.users` and returns `CANCELLED`, preserving mesh vertex coordinates and Scene result; delete the extra object afterward.
2. `native_r6_live_reload_rejected_without_leaks` — attempt `importlib.reload` while CBDK operator classes and Scene descriptors are registered; verify the controlled refusal, identical registration ledger and RNA descriptor token references; explicitly unregister and verify complete detach.
3. `native_r6_detached_reload_reregistered` — after successful unregister, use real `importlib.reload`, then register and detach again without class/property leakage.
4. `native_r6_dual_foreign_descriptors_preserved` — substitute **both** Blender Scene declarations while preview registered with controlled CBDK-authored stand-ins; unregister must leave both replacement descriptor identities untouched and block conflicting registration; clean the stand-ins explicitly before re-register.
5. `native_r6_partial_registration_retry` — inject a controlled failure at the second class registration using a wrapped `bpy.utils.register_class`, confirm full rollback and successful subsequent register/unregister. This is not natural Blender OOM or an uncontrolled crash.

Only generated **`modular_all` preview** code is executed, after explicit preview opt-in, factory startup and ZIP allowlist review. No user/third-party add-on source, user geometry, real foreign add-on or private report is read or executed. All 5 known features and 6 authored recipes remain supported.

The added `tests/test_ui_reload_r6.py` asserts the top-level guard is located *before* assigning registration ledgers or constructing classes, tests detached/live-ledger conditions (including a missing token), checks the native script's fixed R6 marker inventory and builds all six generated authored ZIPs. Python unit tests are synthetic and must not be mistaken for real Blender-native evidence.

## Verification and reporting

The existing **A-owned** `.github/workflows/blender-smoke.yml` already calls the R5 lifecycle script once per Blender version with the locally generated `modular_all` ZIP. **No shared script or workflow changes are necessary**: changing this C-owned script and preview template triggers the existing native matrix, so its R6 cases really run on Blender 4.4.3 / 4.5.15 / 5.2.1 when the GitHub job finishes. Require each actual job to succeed; if a run fails, inspect its log, correct R6-only test assumptions or real code defects and rerun the exact updated head. The legacy `CBDK_R5_UI_LIFECYCLE_PASS` marker remains for the A-owned workflow, but its presence alone is **not** proof the new R6 cases ran: check that each R6 check name appears in that JSON or logs, and the job succeeded.

Also verify Python 3.11/3.12/3.13, Windows 3.11/3.13, Chromium and durable handoff at the R6 HEAD. Kit/Skill are counted only when triggered. Combined-code integration CI is a separate coordinator decision. All real Windows GUI/Undo keyboard sequences, real third-party property collisions, arbitrary user GLBs, license/Extensions readiness and formal release remain unverified. Shared STATE/HANDOFF/PROGRESS/CI/Notion/main must be left unchanged.

## Proposed R7 (not authorized to implement until coordinator resolves R6)

Review conservative recovery when Blender Scene RNA property declarations disappear **externally after partial failed registration**, and inspect whether module reload rejects stale/half-registered ledgers across multiple generated preview enable/disable cycles. Use one CBDK-authored fail-injection and bound its time/resource use. Avoid any automatic repair or deletion of a declaration whose ownership token does not match; ask A for any common smoke/CI ownership change. R6 success does not authorize R7 stacking while the R6 PR is still the one unmerged specialist PR.
