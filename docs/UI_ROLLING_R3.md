# CBDK Team C — rolling R3 lifecycle and mode-switch regression

**Scope:** UI-001 / BUILD-001, CBDK-owned five preview features / six recipes only. Draft stack only, no release or permission change.

## Scope and dependencies

- R2 green base: `work/v018-ui-builder-r2`, commit `31c5d119237347b7bb964a6928743fc0cca9119a`.
- R3 branch: `work/v018-ui-builder-r3`; **draft PR base must be `work/v018-ui-builder-r2`**. A's `work/v018-integration-bcd` remains untouched.
- Only `templates/modular_preview/__init__.py` and UI-owned tests/documentation changed. No shared Blender smoke, catalog, GitHub workflows, STATE, generated handoff, Notion, GLB or Extensions sources.

## Negative case: foreign Scene-property replacement

R2 tracked successfully allocated Scene properties **by name**, to allow cleanup retries. If one is replaced externally (e.g. while recovering from a controlled removal failure), the previous cleanup can inadvertently delete the new unrelated declaration because it uses `delattr(Scene, name)` with only the name as authorization.

R3 records the exact object left on `bpy.types.Scene.__dict__[name]` immediately after adding each CBDK-authored property. During `unregister()`, the property is deleted only when the current class-dictionary object **is the same object**. If another declaration replaced it, cleanup relinquishes the stale CBDK ownership record without removing the foreign declaration. The register preflight still rejects any existing collisions, and failed class/property unregister entries remain retryable. Blender's RNA type-registration implementation stores deferred property definitions in the type class dictionary after registration; use this as an ownership aid, **not** a claim of a security or source-authenticity guarantee.

This addresses an accidental replacement while an add-on is active or during cleanup. It does **not** promise to be safe against concurrent hostile writes, force-reuse of descriptors, Blender crashes, OOM or corrupted native RNA. Those cases require separate real runtime review.

## Negative case: unrecognized context mode on redraw

R3 snapshots `context.mode` **once per Panel.draw**. For a non-string or unavailable mode, composition shows no mode-specific actions instead of calling `.lower()` on an invalid value. It keeps first-round `visible_in` fixed literals and second-round `_preview_unavailable_reason` advisory conditions. The operator still performs final live Blender checks during execution: a green preview button is not success certification.

## Regression coverage

- New `tests/test_ui_rolling_r3.py`: six full register/unregister cycles including duplicate register and idempotent unregister, transient class-detach failure with a fresh cycle, repeated foreign preflight collision, **foreign replacement while registered**, **replacement after a controlled deletion failure**, six alternating Object/Edit Mesh/Sculpt UI displays, stale selection, missing mesh data, and unsupported mode values. These are synthetic context fixtures and one-shot injected failures.
- Existing R1/R2 fixture namespaces now initialize the new ownership map; R2 registration-error chaining and prior mixed-mode plan/ZIP tests remain intact.
- Target CI: Python 3.11/3.12/3.13, Windows PowerShell 3.11/3.13, trusted generated-preview Blender 4.4.3/4.5.15/5.2.1, other triggered workflows on the **exact R3 SHA**. The existing real-Blender smoke validates legacy life cycles and six authored recipes; it does **not** natively exercise foreign replacement or abnormal UI mode states. Please ask Team A to add those to A-owned `scripts/blender_modular_addon_smoke.py` if warranted.

## Explicit unverified boundary

Real Windows GUI/mouse/Undo, actual third-party addon collisions, pathological Blender failures, private content, official Extensions packaging, licensing and release remain unverified/not authorized. No direct-install mechanism or arbitrary operator generation.
