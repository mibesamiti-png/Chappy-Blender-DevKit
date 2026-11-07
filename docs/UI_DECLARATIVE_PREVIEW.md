# CBDK UI-001 — safe declarative preview panel (development)

v0.18 working implementation. **Not a general-purpose visual UI designer or
formal Blender Extensions release.** Existing five authored feature modules
remain the only permitted operators; existing v2 recipes and v1 legacy builder
are preserved.

- `catalog/ui_layouts.json` controls section titles, text labels and button
  ordering for the five existing allowlisted authored features.
- `cbdk/ui_layout.py` rejects duplicate JSON keys, unsupported fields,
  unknown/repeated/missing feature IDs, unsafe labels and oversized sources.
  The layout must cover exactly the five known features; a recipe selects a
  subset and hides empty sections.
- `cbdk/modular_builder.py` injects validated layout **as Python literals**
  into `templates/modular_preview/__init__.py` with the existing feature
  allowlist; no arbitrary operator ID, user Python source, dependency or
  dynamic import can be introduced by the JSON.
- `--preview-unapproved` stays mandatory. Built ZIPs are developer-only,
  never license-cleared or automatically approved, and a runtime CI success
  does not grant redistribution permission.
- `scripts/blender_modular_addon_smoke.py` records actual `Panel.draw`
  calls to check generated sections, button order, operator allowlist and
  registration/unregistration in the headless Blender CI matrix. This is
  **not** a Windows GUI screenshot/interaction or Ctrl+Z verification.

## Development test

```sh
python -m unittest tests.test_ui_layout tests.test_modular_builder -v
python -m cbdk build-addon --recipe recipes/modular_all.json \
  --target-blender 4.5.15 --preview-unapproved \
  --output reports/latest/cbdk-ui-preview.zip
```

No automatic source execution, private GLB upload, main merge, official release,
unknown operator injection, or feature adoption is permitted. UI-001 should
remain **partial** pending general-purpose layout/controls and actual GUI review.

## UI-001 next step: context guards and nudge parameters (v0.18)

- Fixed safe Blender context map: object inspection buttons require an active
  mesh in OBJECT mode; selection counts and vertex nudge require EDIT_MESH.
  Only Blender RNA context values are inspected, never user Python.
- Unavailable functions remain visible but disabled, instead of launching a
  guaranteed CANCELLED operator in the wrong mode. The operator's own original
  execute-time safety checks remain unchanged.
- The existing vertex-nudge operator gets an editable local XYZ offset in the
  panel, through a bounded Scene FloatVectorProperty (each component -10..10).
  Its source module, existing default and safety validation remain unchanged.
  Adding a UI property does **not** establish arbitrary operator parameter
  support or a general UI designer.
- CI asserts the panel controls in no-active-mesh, object-mode and edit-mode
  contexts, checks the operator argument mapping, and verifies Scene properties
  are removed on disable. This is a synthetic headless Blender UI test, **not**
  an actual Windows graphical click/undo test.

## 2026-11-08 JST: presentation, typed defaults and registration recovery

Sections optionally accept `layout: "row" | "column"` and `boxed: bool`.
Defaults preserve the old catalog and all six recipes. Only the authored
`vertex_nudge` control may specify `parameters: {"offset": [X,Y,Z]}`.
A code-owned float-vector contract fixes size 3, bounds -10..10 and the
existing default. Overrides must be finite numbers (not booleans), within
bounds, and a nonzero vector. Unknown parameters, types or operators fail
before ZIP creation. Runtime RNA uses the same validated contract.

The old `plan_ui_layout` return shape is preserved; the builder requests the
additional presentation/parameter plan and injects it using Python literals.
A temporary copied authored project tests a horizontal, unboxed section and
custom XYZ default without editing tracked catalogs or adopting new features.

Registration refuses existing Scene-property collisions before mutation and
tracks owned properties. Property/class registration is inside the rollback
boundary. Native Blender tests inject failure on the second class, confirm
cleanup, re-register, reject duplicate registration, and preserve an unrelated
pre-existing Scene property. This is controlled headless evidence, not arbitrary
failure atomicity or Windows GUI/Undo certification.

## 2026-11-08 JST 実測更新

機能実装8d28b69を含む統合HEAD 63bddb9dcd47ca985995f000efb06b14f056a2cfでPython820件×3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1とKit/Handoff/Chromium/Skillの全7系統成功。[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761850)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761797)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761748)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761811)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761787)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761776)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761778)。

[検証範囲・同時更新/失敗履歴・未確認・再開点](EXT_UI_VALIDATION.md)。合成fixtureの公式検証は実部品の権利/ライセンス/公開承認や正式Extension検証ではない。EXT-001/UI-001/BUILD-001は全体partialを維持。

## 2026-11-08 JST: advisory reasons and shared edit guards

The fixed preview panel now explains missing active mesh/wrong mode and, for
vertex nudge, invalid offsets, no selected vertices, linked/shared data,
shape keys and unsupported multi-object edit context. Structural checks and
offset validation are shared with the existing edit helper; execute still
rechecks actual BMesh selection, numeric changes, topology and resource limits.

The panel uses cached Mesh.total_vert_sel and never imports/scans BMesh or
copies vertex coordinates for readiness. Cached RNA can be stale: an enabled
button is advisory, not edit authorization. The execute-time guard remains
mandatory. A zero vector/no selection disables only the action, keeping XYZ
editable in the appropriate mode so the input can be corrected.

Synthetic Blender tests exercise selection/zero/shared/shape-key reasons,
both Scene-property factory failures, cleanup and subsequent registration.
Existing class-registration/foreign-property tests remain. This is headless
Panel.draw and Blender data evidence, not real Windows GUI/hotkey verification.

## 2026-11-08 JST UI共通ガード/プロパティ復旧の実測

コードeac7453b3e052267c45a83fa7c47180882d02419でPython823件×3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1とKit/Handoff/Chromium/Skillの全7系統成功。[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411841)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411842)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411863)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388412044)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388412165)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411889)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388412036)。

[検証範囲・負荷観測・未確認・再開点](UI_GUARD_VALIDATION.md)。全3版で理由表示と両property factory失敗からの復旧を確認。UIのcached選択数は助言、実行時監査を維持。全体partial、実GUI/権利/汎用UIは未確認のまま。
