# CBDK Team C R2 — advisory panel readiness and retry evidence

Status: **R2 isolated draft; not merged into v0.18 or main.** Scope: UI-001 / BUILD-001, only the five CBDK-authored preview operators.

## Why this is an improvement

R1 mixed-mode composition properly hides controls by fixed mode, but a matching mode and an active object of type `MESH` were not enough to predict whether the operator would refuse execution. R2 deliberately makes the panel's inexpensive *advice* more faithful to each relevant operator:

| Feature | Cheap preview-only refusal | Final execute authority |
| --- | --- | --- |
| All five | No active `MESH` **or** `active.data is None`; incorrect mode | Existing operator and helper preflights |
| `mesh_bounds` | No vertices / missing or non-eight-corner bound box | `mesh_world_bounds`: base-geometry bounds, transformed finite coordinates |
| `edit_selection` | Unknown `objects_in_mode_unique_data` / anything other than one unique mesh | `count_edit_selection`: actual BMesh element counts and same uniqueness check |
| `vertex_nudge` | Existing code-owned `translation_unavailable_reason` and cached selected-vertex count | `translate_selected_vertices`: fresh BMesh selection, numeric, mesh invariants, topology limits, post-edit audit |
| `object_selection`, `modifier_summary` | Active mesh with data and required mode | Existing read-only helpers |

**UI-ready is not execution success, Undo certification, or authorization.** The panel neither imports BMesh nor copies/scans geometry. No user-defined conditions, dynamic expressions, additional operators, free-form RNA types, private code or new build inputs are accepted.

The nudge control has two independently enabled elements: **XYZ is editable** when an active mesh with data is in Edit Mesh mode, including when nothing is selected or the offset is zero; the **action button remains disabled** until the module-owned guard reports no known preflight reason. Missing mesh/data or incorrect mode disables the whole row. Other features disable the corresponding button on a known refusal. Reasons are displayed without user/private data.

## Retry and ownership

R1 already tracked successfully registered classes and owned Scene properties separately, continued cleanup after a detach failure, retained failed entries and rejected register while cleanup was incomplete. R2 tests these exact existing semantics more exhaustively without broadening ownership:
- controlled Scene property **deletion** failure (not only class failure);
- simultaneous one-shot class-unregister and Scene-delete failures, followed by retry;
- original registration error when rollback also fails;
- foreign Scene property collision preserved without unregistering/deleting foreign state.

These are **synthetic injected failures**, not an observed Windows crash, real out-of-memory event, or guarantee of recovery from arbitrary Blender failure. Registration with a duplicate class/operator ID depends on Blender-native registration failure and requires separate runtime review.

## Regressions

- New `tests/test_ui_readiness_r2.py` executes only the trusted preview's `_preview_unavailable_reason`, `Panel.draw`, `register` and `unregister` AST nodes with tiny synthetic Blender-context mocks; no third-party code or `bpy` import.
- Legacy `tests/test_ui_composition.py` preserves R1 `visible_in` fixed allowlist, existing ZIP behavior and retry.
- Six authored recipes and five known features are untouched; `catalog/`, `cbdk/ui_layout.py`, `cbdk/modular_builder.py`, and shared scripts are unchanged.
- Exact run URLs and commits belong on the draft PR after the matrix finishes. Check the PR head SHA for Python 3.11/3.12/3.13 and Blender 4.4.3/4.5.15/5.2.1. Passing the *existing* Blender smoke tests exercises the generated package and legacy cases, **not** all R2 invalid-state scenarios in real Blender.

## Team A handoff: shared Blender smoke follow-up request

The shared `scripts/blender_modular_addon_smoke.py` is reserved for Team A. Please extend its synthetic real-Blender fixture **after review** to test (a) true empty mesh vs bounds button/execute refusal, (b) two unique datablocks in multi-object Edit Mode vs edit-selection button/execute refusal, (c) real Scene property detach failure where test harness can safely inject it, and (d) nudge XYZ remains editable on zero selected vertices. R2's focused Python tests are not replacements for these Blender-native cases; do not describe them as verified until executed.

No global STATE, generated handoff, shared CI, Notion, main, releases or Extensions code changed.
