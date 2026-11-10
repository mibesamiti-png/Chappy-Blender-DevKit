# CBDK Team C R16 — stale Panel.draw context / real operator TOCTOU

## Formal task, authority, base

R16 C (UI-001 / BUILD-001) is allocated by A's
[formal R16 assignment](R16_ABCD_START.md).
R15 B#120/C#121/D#119 were integrated **once** via A
[PR #122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/122)
at dev `08ddb3e3a51e526ddfe857268f31b2de443c0fec`.
A's R16 milestone [PR #123](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/123)
was merged at verified dev HEAD
`3f425212c560043a43ca092443e390cf57d82ae3`.
This exact HEAD has **seven distinct completed-success CI workflow
families** (Python, Windows, native Blender, Chromium, Handoff, Kit,
Skill). Latest HEAD was reacquired before R16 branch creation.
R16 is restricted to the five fixed CBDK-authored preview features
and six existing preview recipes, not v0.19, main or distribution.

## Problem: old draw state must never authorize execute()

The generated Blender panel uses
`_preview_unavailable_reason(feature_id, context)` to display an
advisory enabled state, while operators must re-check current context
through their own runtime safety helpers. `Panel.draw` and the
user's eventual click can be separated by a mode or selection change.
An old `enabled=True` snapshot does not grant permission to edit
or inspect invalid context. The native test deliberately records a
ready button, **then changes the live Blender context**, and invokes
the real `bpy.ops.cbdk.*` operation.

**Cases implemented in `tests/blender_ui_lifecycle_r5.py`:**

1. An authored triangle is active in OBJECT mode.
   `Panel.draw` reports the three OBJECT readers enabled.
   Switch to EDIT_MESH before invoking the real selection count,
   bounds and modifier-summary operators. All must `CANCELLED`
   without changing the mesh, mode, active object or Scene result.
2. In EDIT_MESH select one native BMesh vertex and draw.
   `vertex_nudge` must be enabled. Deselect *after* draw,
   then call the actual nudge operator: `CANCELLED`, mesh coordinates,
   Scene result and selection unchanged by execution. A new draw
   must show nudge disabled while the XYZ input stays usable.
3. Select one vertex and draw both edit actions enabled,
   then switch to OBJECT before calling nudge and edit-selection:
   both must `CANCELLED` with no geometry or Scene-result mutation.
4. Fresh valid draws and real calls must still succeed after the
   negative cases: OBJECT bounds and EDIT_MESH selection count return
   `FINISHED`. This ensures the test doesn't mistake unconditional
   refusal for correct revalidation.
5. Draw a previously valid OBJECT action, then replace
   `Scene.cbdk_modular_result` with an authored synthetic foreign
   descriptor, switch to EDIT_MESH and call that previously enabled
   OBJECT operator. It must `CANCELLED`, without writing to the
   foreign Scene field or touching the descriptor by identity.
   Disable must release CBDK registered classes and its owned
   descriptor, but **preserve** the foreign declaration.
   Remove only the exact synthetic foreign fixture, then
   enable/execute/disable once more with no remaining ledger.
6. The final recovery must retain five fixed feature IDs and all
   earlier R5–R15 native regression markers.

**R16 native markers** appended only after successful real assertions:

- `native_r16_object_draw_then_edit_cancel`
- `native_r16_edit_draw_then_deselect_cancel`
- `native_r16_edit_draw_then_object_cancel`
- `native_r16_redraw_valid_actions_still_finish`
- `native_r16_foreign_scene_stale_cancel_safe`
- `native_r16_reenable_after_stale_draw`

The real operator must not reuse an old button flag. We do not
simulate an actual mouse click, UI event queue or a multithreaded
Blender race; these are deterministic, sequential live-context
TOCTOU fixtures and therefore **not GUI usability/Undo proof**.
All geometry and foreign descriptors are created by CBDK's
own test code. No private addon/GLB/user blend or external addon
is imported or published.

## Safety decision and verification

`tests/test_ui_stale_draw_r16.py` independently exercises
synthetic mode/selection advisory transition tests and a static
native-script contract. It **does not** claim native Blender
operation results.

`templates/modular_preview/__init__.py` changes only a comment
describing live execution checks, also activating the existing
native CI path filter. If all live negative scenarios are
successfully rejected, **no production logic change** is warranted.
If a reproducible failure is seen, fix only the affected C-owned
file, then retest. Never add generic UI, arbitrary recipe sources
or automatic actions.

For the exact final R16 C branch HEAD, independently check the
five required workflow families (Python 3.11/3.12/3.13, Windows
PowerShell 3.11/3.13, native Blender 4.4.3/4.5.15/5.2.1, Chromium,
Handoff). Fetch **each completed Blender job log** and parse
`CBDK_R5_UI_LIFECYCLE_PASS` JSON `checks` for all SIX markers
above and all previous R5–R15 markers. Source inclusion or
mock success alone is not runtime evidence.
Kit/Skill are additional only if they actually run on this exact
specialist SHA. A's later combined five and post-dev-squash seven
are distinct checks requiring their own GitHub evidence.

Strict ownership: `templates/modular_preview/`, C-specific
`tests/`, C-specific `docs/` only. No shared STATE/Handoff/
PROGRESS/CI/scripts/Notion/main, no GLB B or Extension D changes,
no old R15 PR stacking, no Geometry Lab #114 or DIL #115 adoption.
No rights/license/author consent or formal Extensions permission.
Private user assets, Windows GUI Ctrl+Z, external third-party addon
coexistence, crash/OOM and arbitrary unknown module recovery
remain **unverified**.

**R17 design-only candidate** (not authorized for implementation):
If fresh R16 native evidence remains sound, prefer a compact
context-change regression matrix that tests transient active-object
removal or a second authored edit object *after* draw. Compare
guard refusal, unchanged coordinates and foreign ownership,
without changing generic runtime APIs; ask A to prioritize only
cases not already covered by R5–R16.
