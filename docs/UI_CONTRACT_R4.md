# Team C R4 — authored UI declaration, generated package and rejection contract

**Requirement:** UI-001 / BUILD-001 (still *partial*). **Branch:** `work/v018-ui-builder-r4`, based on the latest v0.18 development HEAD after [A's PR #38](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/38). This is a **local, unapproved CBDK-authored preview**, not an Extension/release.

## Goal and bounded fix

The round-1 through round-3 code preserves strict fixed `visible_in` modes and distinguishes preview readiness from actual execution. R4 checks the end-to-end consistency of the **six existing authored modular recipes** and finds two additional **known false-ready** contexts:

1. `object_selection` execution calls `selected_mesh_objects(context)`, which refuses when the `selected_objects` collection is unavailable. The preview used to enable the action in that context. R4 reads only the collection's presence in `_preview_unavailable_reason` and disables the action with the same fixed diagnostic.
2. `mesh_bounds` execution refuses a nonfinite world-space bounding box; a base-object bounding corner containing NaN/Inf is an inexpensive, definite refusal case. R4 checks the eight 3-component corners with a **constant maximum of 24 scalar finiteness checks**. It does not scan mesh vertices, create BMesh, evaluate modifiers or traverse arbitrary user data. A finite bound box is *not* proof of a valid world transform or successful execution.

R4 intentionally **does not** alter the execute methods, the audited BMesh-edit helper, the nudge offset domain, the five fixed feature IDs, or the recipe schema. Existing R3 foreign Scene property identity guard and multi-mode layout are preserved.

## Contract matrix

The UI-owned `tests/test_ui_contract_r4.py` builds all six CBDK-authored `modular_*.json` recipes with the **explicit** `preview_unapproved=True` gate in a disposable directory. It reads each ZIP's generated `__init__.py` AST and metadata, verifies the filtered `plan_ui_layout()` sections and `control_visibility`/typed nudge options, then executes only trusted CBDK-authored `Panel.draw`/readiness AST for Object, Edit Mesh and Sculpt modes.

Invalid synthetic contexts compare the generated button's disabled state and fixed reason with the original CBDK-authored operator `execute()` method's **actual `CANCELLED` result** and unchanged synthetic Scene result, data reference and mode **when the rejection occurs before Blender-only imports**. The zero-selected-vertices nudge case tests only the shared advisory helper; its fresh BMesh execution path is reserved for real Blender smoke:

| Case | Known disabled feature | Effect on other controls |
| --- | --- | --- |
| Active object with missing mesh data | `object_selection` (and all feature-specific active-mesh guards) | No execution permission |
| Context with no `selected_objects` collection | `object_selection` | Other valid Object-mode readers are independent |
| Mesh with zero vertices | `mesh_bounds` | Object selection and modifier inspection remain available when their guards pass |
| Missing/non-8-corner bounding box | `mesh_bounds` | No geometry mutation |
| Nonfinite bounding-box corner (NaN/±Inf) | `mesh_bounds` | **UI only:** Python does not invoke Blender `mathutils` for this one |
| Incompatible Object/Edit mode | `modifier_summary` and other authored guards | Preview visibility is declarative, not authorization |
| Two unique mesh datablocks or unknown Edit Mode object collection | `edit_selection` / `vertex_nudge` | No BMesh scan in panel |
| Zero selected vertices | `vertex_nudge` | XYZ input remains editable, read-only selection counter remains available |

The operator-negative tests use the real **code-authored execute method AST** and the real helper preflights. They intentionally select cases that reject **before** importing Blender-only `bmesh` and `mathutils`; they cannot certify full native behavior. Repeated registration/unregistration, foreign collision, partial cleanup and mode switching stay covered by the preexisting R2/R3 Python tests. The six existing modular preview packages and the legacy schema-1 recipe are unchanged.

## Test evidence and limitations

Record the exact R4 HEAD SHA and triggered GitHub Actions runs in its **draft PR**. The required matrix is Python 3.11/3.12/3.13, Windows launchers, Blender 4.4.3/4.5.15/5.2.1, Chromium, Handoff, and Kit/Skill only if triggered. The existing shared Blender smoke checks generated addon enable/disable, read-only operators, nudge and all six preview recipes. **Passing it does not prove that R4's new unsupported-collection/nonfinite-corner states were exercised in real Blender.**

**A-owned shared script request:** update `scripts/blender_modular_addon_smoke.py` (or allocate a separate C-only Blender fixture and CI invocation) to test real empty mesh, multi-datablock Edit Mode, zero selection, Object/Edit mode transition and allowed user property replacement/registration where possible. Do not emulate unavailable `bpy.context.selected_objects` or a nonexistent `Mesh.data` as if such contexts were produced naturally by Blender. Nonfinite coordinates must be introduced only in disposable, controlled synthetic meshes, never private user models.

No shared `docs/project/STATE.json`, `docs/PROJECT_HANDOFF.md`, Notion, `main`, `catalog/`, shared `scripts/` or `.github/workflows/` files are changed by Team C. Real Windows GUI, native Undo hotkeys, private GLBs/addons, official Extensions, licensing and release remain unverified/not authorized.
