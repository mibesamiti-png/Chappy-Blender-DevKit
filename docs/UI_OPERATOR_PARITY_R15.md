# Team C R15 — UI readiness vs actual Blender operator results

## Task authority and exact base

Coordinator A's [R15 formal assignment](R15_ABCD_START.md) tasks Team C
(UI-001 / BUILD-001) with verifying **live Panel.draw button availability
against actual Blender operator return status** for the fixed five
CBDK-authored features and six preview recipes. The R14 combined code and
long-term vision documentation were integrated once in
[PR #117](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/117)
at developer squash `db25585342e19e629fc32e2cc94ceae5d2e3d7b4`.
The latest R15 milestone HEAD `492b6d83e81de7c5283e70d4da55f58f8a598530`
has **seven separate completed-success CI families**. The R15 C branch
must start at the live, newest developer HEAD, not a historical R14
specialist branch. B/D current work and independent Geometry / DIL research
PRs are not imported.

## Why this test matters

The generated preview's `_preview_unavailable_reason` is a **cheap UI
hint**, not the authoritative safety check. It uses cached Blender
context, geometry and selection for a button enabled flag. Actual
`bpy.ops.cbdk.*` operators call their respective helpers to revalidate
live context, selection and edited geometry at execution time. A
correct user-facing preview should enable the five reviewed
operators in supported contexts, show unavailable actions in wrong
modes, and never imply that an earlier Panel.draw snapshot
authorizes future mutation. Headless Blender operator return values
`{'FINISHED'}` and `{'CANCELLED'}` are observed separately from mocked
UI layout flags.

## Bounded native scenario matrix

The C-owned `tests/blender_ui_lifecycle_r5.py` already executes under
the A-owned workflow with Blender **4.4.3 / 4.5.15 / 5.2.1** and only
a locally generated, allowlisted `modular_all` ZIP. R15 introduces
an authored, isolated triangle and empty mesh fixture, with real
Blender `bpy.ops`, `bmesh.from_edit_mesh`, mode changes and
`VIEW3D_PT_cbdk_modular_preview.draw` through the existing
effective-enabled layout recorder:

1. **OBJECT, active valid triangle:** all three object readers are
   visually enabled and actually `FINISHED`; edit selection and nudge
   are visually disabled and actually `CANCELLED` on explicit
   programmatic calls. The readers must not move geometry.
2. **OBJECT, active empty mesh:** selected-object and modifier readers
   remain enabled/`FINISHED`; bounds are disabled/`CANCELLED`.
   **No active object:** every action disabled/`CANCELLED`. Cancel
   outcomes cannot alter the Scene result.
3. **EDIT_MESH, zero selected vertices:** edit-selection counter
   enabled/`FINISHED`; nudge disabled/`CANCELLED`; object readers
   disabled/`CANCELLED`. The XYZ property remains editable.
4. **EDIT_MESH, exactly one selected BMesh vertex:** both edit
   actions enabled and actually `FINISHED`; object readers
   disabled/`CANCELLED`. The nudge must move only the selected vertex
   in the expected axis and amount. Compare real Edit BMesh coordinates,
   not potentially stale Mesh vertex fields.
5. **OBJECT → EDIT_MESH → OBJECT:** after each context transition
   the panel recomputes availability; disabled operations still cancel
   and valid ones still finish. No previous UI flag is cached as
   permission.
6. **Disable → foreign Scene descriptor → register refusal →
   foreign fixture removal → re-enable:** the non-CBDK synthetic
   descriptor must remain intact during collision refusal, no owned
   class/Scene ledger may leak, and the new enabled module must again
   display accurate OBJECT readiness against real operator results.

These are controlled author-owned fixture and descriptor tests, not
imports of a real third-party addon or private user Blender file.

**New native R15 checks** (written only after associated assertions):

- `native_r15_object_ui_execute_status_parity`
- `native_r15_empty_missing_mesh_cancel_parity`
- `native_r15_edit_zero_selection_cancel_parity`
- `native_r15_edit_selected_operator_result_parity`
- `native_r15_mode_switch_rechecks_operator_parity`
- `native_r15_foreign_scene_reenable_preserves_parity`

`tests/test_ui_operator_parity_r15.py` adds separate Python-only
mocked advisory-state transition tests, a static uniqueness contract
for all native markers, and preservation of all six fixed recipes.
It does **not** fake or count mock operator status as native Blender.
The existing R5–R14 marker suites, five features and six recipe-build
tests remain in place. The template `__init__.py` change is an
explanatory comment only, not product behavior; the diff also triggers
the existing Blender workflow path filter.

## CI quality gate and decision rule

At the exact R15 draft PR HEAD inspect completed Python 3.11/3.12/3.13,
Windows PowerShell 3.11/3.13, Blender 4.4.3/4.5.15/5.2.1,
Chromium and Handoff workflow families. Fetch each completed native
Blender job log and parse `CBDK_R5_UI_LIFECYCLE_PASS` JSON
`checks`; all six R15 IDs must appear in every version. Preserve
the prior R5–R14 checks. A Python mock pass or native marker string in
the source is **not** proof that a Blender operator executed.

If any real UI/execute disagreement appears, make a minimal fix under
Team C's exact authorized path, prove fail-before/pass-after on the
affected fixture where feasible, and recheck all required HEAD-CI.
If no divergence is found, **finish with tests/docs only** and do not
expand the UI or import arbitrary feature code. Kit/Skill count only
when truly triggered at the R15 specialist SHA. Coordinator A must
separately verify any R15 combined candidate and post-squash SHA.

## Ownership, privacy and known limitations

Only `templates/modular_preview/`, UI-specific `tests/` and
UI-specific `docs/` may change. Shared
STATE/HANDOFF/PROGRESS/scripts/workflows/Notion/main, Team B GLB,
Team D Extension code, A benchmark PR #109, Geometry Lab #114,
DIL #115 and other research are untouched. Actual Windows GUI
button clicks, keyboard Undo/Redo Ctrl+Z, arbitrary external
addons, private/user GLB, unknown source imports, multi-user
automation, crash/OOM recovery, license/author consent,
official Extensions/public release and v0.19 activation remain
**unverified or unauthorized**. Operator success is a bounded
native test, not a guarantee against post-draw context changes.

**R16 design candidate only, subject to formal A allocation:**
deliberately change mode or vertex selection *between*
`Panel.draw` and operator `execute` in the same known CBDK
preview, ensure the operator revalidates and cancels without source
mutation or UI flag reuse. Add a carefully bounded
multi-object Edit Mode negative fixture only if needed. Keep
foreign Scene/old-module recovery tests and real three-version
job markers; do not introduce generic UI, background state
monitoring or unverified third-party execution.
