# Team C R7 — registration rollback with Scene declaration disappearance/replacement

**Workstream:** UI-001 / BUILD-001, rolling R7. Authorized by A-owned latest `docs/PARALLEL_ROLLING_QUEUE.md` after R6 [PR #56](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/56) integrated at `e2f09e593d9c7bdff66695c7e8972eea98e160ca`. Its **separate post-merge seven-family CI** succeeded. Start from the latest descendant development HEAD; do **not** branch from historical Team C #55 or re-merge it.

## Specific negative cases

The existing R5/R6 CBDK-owned `tests/blender_ui_lifecycle_r5.py` is already executed by A's Blender matrix with **factory startup** and an explicitly generated, preview-only, fixed-five-feature `modular_all` ZIP. R7 extends that *same* native script without touching shared CI/smoke files:

- **Mid-register missing property + synthetic foreign replacement:** during a controlled exception at the second `bpy.utils.register_class` call (after one operator class has genuinely registered), externally **delete one** CBDK-owned Scene declaration and **replace the other** with a fresh CBDK-authored stand-in descriptor. Run both permutations. The generated preview's registration rollback must detach the one registered class, release all ownership ledgers, preserve the new foreign descriptor unchanged, and leave the missing property missing.
- **In-flight reload refusal and post-rollback reload:** before injecting the controlled exception, attempt `importlib.reload(module)` with a populated registration ledger. R6 fail-closed guard must reject it. After rollback, `importlib.reload(module)` must succeed without removing or claiming the foreign descriptor. A fresh registration while the foreign name exists must reject it; after explicitly removing the stand-in, a normal register/unregister cycle must succeed.
- **Real Blender enable/disable after recovery:** after the two interrupted cases recover, repeat `addon_utils.enable` and `addon_utils.disable` **twice**, checking that the fixed operator-class count, Scene descriptors and ownership ledgers are complete and then fully gone. This differs from calling `module.register`/`module.unregister` directly.

**Native positive evidence markers**, appended only after every corresponding assertion:
`native_r7_mid_register_missing_foreign_rollback`,
`native_r7_partial_live_reload_rejected`,
`native_r7_foreign_reload_collision_preserved`,
`native_r7_enable_disable_after_recovery_2`.

All existing R5 and R6 positive/negative checks, five fixed features, six authored recipes and privacy/release gates are preserved. No production change is necessary unless a reproducible mismatch appears. Existing `CBDK_R5_UI_LIFECYCLE_PASS` JSON summary includes these R7 check labels when the complete native script finishes successfully.

The new Python-only `tests/test_ui_lifecycle_r7.py` independently injects the two permutations of Scene deletion/replacement during an intermediate class registration failure, tests class-unregister retry plus foreign preservation, checks R6 reload protection, and audits the new native fixture's static import/marker scope. Python mocks are **not** real Blender/Windows GUI evidence.

## Acceptance and runtime truth

Run the existing workflow `CBDK Blender multi-version runtime smoke` at the **exact R7 PR HEAD**, inspect all three version-specific job results (4.4.3 / 4.5.15 / 5.2.1) and their `CBDK_R5_UI_LIFECYCLE_PASS` JSON *checks*, confirming **all four R7 labels** are present in each actual job. Also require Python 3.11/3.12/3.13, Windows 3.11/3.13, Chromium and Handoff if triggered. Kit/Skill must not be counted as triggered unless that is observed. An individual PR pass is not a combined or post-merge SHA pass.

**Boundaries:** only controlled, locally synthesized Blender Scene descriptors stand in for foreign ownership. No real third-party addons, private user `.blend`/GLB/Python, model auto-execution, arbitrary commands, GUI Undo shortcut, licensing, distribution or official Extension authorization. Deliberate failures are **not** spontaneous OOM or process crash recovery. No A-owned `scripts/blender_modular_addon_smoke.py`, workflow, STATE, HANDOFF, PROGRESS, Notion or `main` edits.

## Next candidate for A (R8 design only)

Study a **bounded unregister failure followed by replacement of a Scene descriptor before a retry**, plus successive `addon_utils.enable/disable` lifecycle repetitions. Distinguish expected foreign preservation from CBDK-owned cleanup; ensure reload continues fail-closed while *any* registration ledger retains a failed class/property. Begin with synthetic Python first, require actual native Blender three-version evidence and no private plugins. Do not create another stacked PR until A resolves R7 integration/base and approves its queue.
