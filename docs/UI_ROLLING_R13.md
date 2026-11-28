# Team C R13 — enable failure, module eviction and original ledger recovery

**Authority:** [docs/R13_ABCD_START.md](R13_ABCD_START.md), coordinator A's
merged R13 allocation [PR #99](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/99)
and combined R11/R12 code [PR #98](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/98)
at `ab42913d300efd003450027a2697586e15ca76ad`.
The latter has **seven distinct completed and successful push CI families**;
R13 is a new independent PR based on the latest
`feature/v0.18-shape-diagnostics` HEAD immediately before branch creation.
The B R13 PR #100 and D changes are independent, not imported.

## Why this test exists

`addon_utils.enable(PACKAGE)` can fail after registering **some** Blender
classes and then evict `PACKAGE` from `sys.modules`. If its own exception
rollback also fails, the old module still has a populated
`_REGISTERED` and sometimes `_OWNED_PROPERTY_TOKENS` ledger even though
the package name is no longer importable *as that object*. A later
`importlib.import_module(PACKAGE)` yields a distinct Python module with
empty ledgers. The empty new records do NOT prove Blender has no
registered class, and `fresh.unregister()` is not recovery of the stale
old module. The original module reference has to be retained and
`original.unregister()` explicitly invoked.

These are bounded failure-injection observations, **not** an automated
cross-reimport ownership registry or a promise of crash recovery. Never
blindly use the newly imported module as proof that all registrations
have been released.

## Native Blender fault model and acceptance

The C-owned `tests/blender_ui_lifecycle_r5.py` is already invoked in
the A-owned Blender 4.4.3 / 4.5.15 / 5.2.1 jobs against a locally
generated allowlisted, **preview-only CBDK-authored** `modular_all` ZIP.
It uses Blender factory settings and no user data.

Two cases are explicitly bounded:

1. On **second** real `bpy.utils.register_class` during
   `addon_utils.enable`, deliberately raise; also raise during rollback
   of the **first** successfully registered class. All original Scene
   properties must clean, but the old module still tracks one real Blender
   operator class.
2. Repeat the same failure, and additionally inject one failure while
   rolling back `bpy.types.Scene.cbdk_modular_result`. The old module
   must track both the real class and that precise RNA token.

For each case: the failed enable returns no module, reports a handled
`RuntimeError`, evicts `PACKAGE` from `sys.modules`, and leaves the
original module's owned record(s) intact. Prove the Blender class is
really still present via `bpy.types`, not only a list length. Import
the same package name **before recovery** and verify a different module
object with empty class/property/token ledgers while the old class
persists. Install a CBDK-made synthetic *foreign* Scene RNA declaration.
The new module's registration must reject the collision and its
`unregister` must not change old ownership or delete the synthetic
property. Explicitly invoke the **old** module's `unregister()` and
verify all old classes and ledger claims are gone and the foreign
descriptor preserved by exact identity. Remove only that synthetic
declaration, and verify a clean subsequent `addon_utils.enable/disable`
and full detach.

R13 native success marker IDs, appended only after the full relevant
Blender assertions:

- `native_r13_failed_enable_evicts_live_module`
- `native_r13_fresh_import_hides_original_pending_ledger`
- `native_r13_old_reference_recovers_live_classes`
- `native_r13_foreign_scene_survives_recovery`
- `native_r13_reenable_after_eviction_2`

All existing R5–R12 markers and five authored features / six authored
preview recipes are preserved. The native script runs *real*
`addon_utils.enable`, `bpy.utils.register_class` and
`bpy.utils.unregister_class`; only bounded synthetic callback
exceptions and an authored foreign stand-in are used. All temporary
function patches are restored in `finally`.

The separate `tests/test_ui_lifecycle_r13.py` uses a Python-only
synthetic bpy context to emulate old/new module identity, fail-closed
ownership and explicit recovery, plus fixed native script contract
assertions. These are NOT native Blender evidence. The generated preview
`templates/modular_preview/__init__.py` only receives an explanatory
**comment**, no production behavior or owned code is changed unless a
real fault is reproduced.

## CI / verification gate

At the exact draft PR HEAD, inspect Python 3.11/3.12/3.13,
Windows PowerShell 3.11/3.13, Chromium, Handoff and all Blender 4.4.3 /
4.5.15 / 5.2.1 matrix jobs. For Blender, examine each completed
version-specific job log's `CBDK_R5_UI_LIFECYCLE_PASS` JSON `checks`
and require **all five R13 native marker IDs**. Old R5–R12 marker
presence should be checked too. Script presence or synthetic unit tests
cannot count as native execution. Report any red / incomplete / skipped
workflows explicitly; Kit/Skill are counted only if actually triggered.
The R13 individual PR and A's future combination/post-merge CI are
different SHA-level evidence.

## Scope, privacy, unreached gates and R14 proposal

Changes are limited to `templates/modular_preview/`, C-owned
`tests/`, and C-owned `docs/`. No shared STATE, Handoff, PROGRESS,
Notion, scripts, workflows, main, B GLB (including PR #100), D
Extensions, or private user/third-party addon material is modified.
No actual third-party addon coexistence, arbitrary multi-module orphan
recovery, real Windows GUI/Ctrl+Z, process crash/OOM resilience,
user-provided GLB, license/SPDX determination, official Extensions
distribution or release is proven.

**R14 design only (requires fresh A authorization):** Repeated failed
`addon_utils.enable` / import / recovery across multiple stale module
generations, with one stale registered operator each, to determine
whether *all* saved old references must be released before a new
registration can safely proceed. Bound depth to 2 or 3, never
execute an unknown addon, require identity-aware foreign Scene
protection, and distinguish a recovered original from a merely
disabled/evicted fresh copy. Prefer conservative warning/diagnostic
over global recovery automation; preserve all previous native markers.
