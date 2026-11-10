# R11 pre-registration — Blender edit-mode mesh/UV/material round-trip audit

**Purpose:** Find out what R10 does *not* guarantee when it is inserted into a real Blender Edit Mode object with existing faces, per-corner UV coordinates and materials. This is a synthetic workflow prototype, **not** automatic production integration or a generic UV unwrapping algorithm.

## Immutable hypothesis and protocol

- R10 `conditional_flip_loft` remains frozen. R11 provides one *research-only* Blender adapter that creates two open collar surfaces with deliberately tagged original polygons, UV layer, and two original materials, then attaches the detached R10 bridge in a **temporary Edit Mode BMesh** with a third, explicit bridge material.
- The pre-existing collar polygons, UV corners, material indices and source boundary XYZ must be exactly equal before and after the edit. No user files/models/scenes. Operator/adapter must restore object set, active object, selection and mode. No product add-on registration.
- New bridge UVs: deterministic cylindrical UV map from per-vertex XY angle and normalized Z over the gap. Original collar UVs are constructed with the same per-vertex mapping in 'continuous' mode (an explicitly compatible UV source), while 'split' mode deliberately uses different per-corner UV island offsets on the collar. R11 adapter **does not automatically reconcile islands**. Measure signed UV gap at original boundary corners. Never assert real artist UV continuity.
- For the temporary sleeves, build collar face orientation to oppose the R10 strip's boundary edge orientation. Original collars have two materials (lower=0, upper=1); bridge has material=2. Open outer ends remain boundary edges, connected through strip. Different original UV maps are preserved exactly. The metric does not require normal smoothness. Measure adjacent face-normal angle across the original boundary as a risk indicator.
- Both UV modes have a **negative control**: baseline newly created bridge UV all-zero and material=0, which should retain existing collar attributes but not satisfy added-bridge UV/material expectations. This ensures the audit can detect broken new-attribute assignment instead of rewarding unchanged source-only data.

## Frozen fixtures, independent tests and gate

- 4 *seen development* from earlier R10 data, two UV modes each. 6 **new R11 holdouts** with new authored nonplanar star-shaped geometry specs, three marked continuous UV and three split UV, frozen before first CI execution; all wholly synthetic.
- Each fixture/mode compares `r11_attribute_adapter` to the negative `r11_zero_uv_control`, using **Blender 4.4.3 Edit Mode BMesh**. Aim: exactly **10×2 =20** results, no dropped failures.
- Both Blender records must show zero existing-face/UV/material mutations, exact bridge geometry and no scene leftover. New bridge polygons must be material 2, UV finite and in range [0,1]. The negative control should fail new-attribute assignment for each case. Continuous mode must report <=1e-6 UV discrepancy on the boundary, split mode should report >0.05 (expected limit, not a false full success). No promise of zero normal mismatch; report mean/max dihedral angle only.
- Independent Python3.12 CGAL oracle must confirm zero self-intersection for the **new strip** (at minimum) as R10 does, and report any full joined-mesh CGAL cross pairs **separately**, not suppress defects or pretend away adjacency. Reject if oracle unavailable.
- A high-confidence research **audit gate** requires every continuous sample pass boundary UV continuity, source integrity and bridge material; every split sample preserve source and detect UV mismatch; and all negative controls fail bridge material/UV expectation. If any gate fails, record failure without adjusting frozen fresh fixtures/algorithm. If full joined CGAL fails while the strip passes, record an integration blocker and do not approve a product route.
- If any R10 output fails its established geometry-quality rubric, keep this independent audit result but do not relabel it as a successful R10 surface. Never equate this scoped workflow experiment with full Blender model support, artist editing quality, painted UV continuity or normal/shading preservation.

## Governance

Only `research/geometry_lab/**` and `.github/workflows/geometry-lab.yml`. Keep PR #114 Draft/unmerged, `approved=false`. Do not touch main, ABCD, DIL PR #115, shared STATE/HANDOFF, or user/private meshes. No R12 automatic start. No holdout-driven tuning after the first new-case Blender run.
