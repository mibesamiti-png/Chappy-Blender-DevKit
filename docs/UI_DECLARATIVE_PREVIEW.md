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
