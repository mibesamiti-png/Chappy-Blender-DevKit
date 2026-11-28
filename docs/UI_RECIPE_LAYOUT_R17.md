# R17 Team C — recipe-specific declarative preview UI

Existing five authored features and six unchanged recipes remain the only
operator/source allowlist. No arbitrary Python, paths, RNA types, operator
names, new mode permissions, extension approval or third-party imports.

## User-visible capability

A schema-2 modular recipe can now add an optional **inline** `ui_layout`
object. It follows the existing catalog schema (schema_version 1,
kind cbdk_authored_preview_ui_layout, preview_only true, sections).
The layout covers exactly the resolved features once; 1–4 sections, known
feature IDs, printable labels, row/column, boxed/unboxed, mode visibility,
and the existing finite typed nudge default and narrowed input bounds.
These are display/input settings, not new execution permissions. The
existing operator guard is still authoritative (including direct bpy.ops);
the narrowed bounds constrain the panel's RNA input, not the operator API.
Unselected features, unknown fields, incompatible visibility, arbitrary
paths and types are refused before ZIP creation. No global catalog edit
is needed and legacy recipes retain their previous plan/output.

For an example, copy the existing `recipes/modular_all.json` and add
`ui_layout` with the contents of `catalog/ui_layouts.json` as an object.
Change only supported data, e.g. section title, controls order, layout
"row", boxed false, or the vertex_nudge control's parameters:

```json
{"offset": {"default": [0, 0, 0.25], "min": -1, "max": 1}}
```

For a subset, include only its resolved feature controls and remove empty
sections. Existing build command (local-only preview):

```sh
python -m cbdk build-addon --recipe my_recipe.json --preview-unapproved --output my_preview.zip
```

The build and static plan share one C-owned implementation:

```python
from cbdk.addon_builder import ROOT
from cbdk.modular_builder import plan_modular_recipe
import json
from pathlib import Path
recipe = json.loads(Path("my_recipe.json").read_text(encoding="utf-8"))
plan = plan_modular_recipe(recipe, root=ROOT, target_blender="4.4.3", include_ui=True)
print(json.dumps(plan, ensure_ascii=False, indent=2))
```

**A-owned CLI hook (not edited):** the existing `addon-plan --with-ui`
command separately calls the legacy feature-only validator and global
catalog. For custom layouts it deliberately fails closed rather than
misreporting the global UI. A can replace that branch's separate
validation/plan/UI calls with
`plan_modular_recipe(recipe, root=Path(__file__).resolve().parent.parent,
target_blender=args.target_blender, include_ui=args.with_ui)` and import
the function from modular_builder. No need to change CI, old recipes,
shared STATE or ownership rules. Until that wiring is reviewed, use the
static Python API above. Legacy CLI behavior is unchanged.

## Evidence target

Two distinct fixtures with identical five-feature sets:
- compact: horizontal unboxed Object group, boxed Edit group,
  renamed buttons, narrowed +/-1 input with +0.25 Z default.
- grouped: Edit first with row/unboxed layout and reversed buttons,
  separate selection and geometry groups, +/-0.5 input with +0.125 X.

Python tests check static plan/build equality, AST literals, ZIP
determinism, legacy and subset handling, refusal of unsafe data.
The existing R5 lifecycle script invokes the native fixture for both:
real Blender Panel.draw with recording layout, matching labels/order/group
paths, real RNA bounds/default, all five live operators, selected-vertex
translation using the actual drawn offset, and full unregister. Separate
native marker per variant only after successful checks. Existing R5–R16
tests remain intact. Final exact-head five CI and actual Blender logs
must be checked before declaring runtime success.

Actual Windows GUI/Undo, generic arbitrary addon composition, third-party
coexistence, rights and formal distribution remain unverified. No additional
research round is needed for this bounded capability; A decides whether
the CLI hook and owner/environment blockers remain for completion.
