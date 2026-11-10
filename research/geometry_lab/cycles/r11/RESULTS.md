# R11 — Blender 4.4.3 Edit Mode integration / UV / material / normal audit (2026-11-11 JST)

## Decision

**Pre-registered, limited *attribute audit* passed. The six new synthetic conditions all passed the scoped attribute checks. This is NOT proof of general artist UV continuity or normal shading. No CBDK product adoption (`approved=false`).**

The candidate is a **research-only temporary Blender BMesh adapter**, not an enabled CBDK add-on. It creates two open synthetic collar surfaces with preassigned per-corner UVs and different original materials, enters Blender **EDIT mode**, stitches in the frozen R10 detached triangulated strip and assigns a third material plus new per-corner UV values. It checks that all original face vertex coordinates, polygon windings, material indices and loop UV values are bitwise identical inside BMesh before and after adding the strip; then restores the scene, selected objects, active object and mode.

The collars are *constructed from R10's own boundary edges*, to create a controlled, correctly oriented test geometry. This is an **author-designed favorable case**, not a blind external working model. External live files, private meshes and production app content are not used.

## Frozen research design and evidence

- The [R11 preregistration](RESEARCH.md) and [6 new fixture specifications](fixtures.py) were committed before first holdout. A prior 4-geometry development subset used two UV modes each, 8 attribute checks + 8 negative controls. This 16-result **pre-holdout smoke passed**. Source was not modified after fresh holdout execution.
- Frozen new synthetic holdout has **6 distinct geometries**, three with a deliberately compatible continuous UV rule and three deliberately misaligned split-island UV rules. Each has one attribute-aware and one deliberately broken zero-UV/incorrect-material arm (2 arms). Totals: **14 geometry×UV conditions × 2 arms = 28 Blender Edit Mode integrations** (16 seen development, 12 fresh holdout outputs).
- Verified official Blender **4.4.3** with publisher SHA256 `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`, separate Python 3.12 CGAL `6.0.1.post202410241521`.
- The external oracle evaluated **each assembled collar+strip triangle mesh and each standalone R10 strip**, not only the generated new faces; **zero CGAL self-intersection pairs on all 28 of both scopes**. Original source/attribute and scene cleanup were checked in Blender. All 14 standalone candidate R10 strips passed their existing independent geometry rubric in this selected corpus.

## Preregistered attribute audit

| Check | Seen development | New holdout | Result |
|---|---:|---:|---|
| Attribute adapter: original face/UV/material exactly unchanged, original XYZ boundary fixed, new material=2 and finite nonzero UV, topology and cleanup valid | **8/8** | **6/6** | PASS |
| Deliberate zero-UV/wrong-material **negative control correctly detected** | **8/8** | **6/6** | PASS |
| Continuous source UV: boundary UV discrepancy ≤1e-6 | 4/4 | 3/3 | PASS, observed max **0.0** |
| Split UV island: UV discontinuity **correctly detected**, not repaired | 4/4 | 3/3 | PASS *for detection*, observed max **0.25** |
| Whole assembled mesh: CGAL self-intersection pairs=0 | 8/8 adapter | 6/6 adapter | PASS on scoped corpus |
| Original geometry strip standalone R10 geometric rubric | 8/8 adapter | 6/6 adapter | PASS on scoped corpus |

All 14 original collar signatures were unchanged. Expected connected join was found at the source boundary edges: each original loop edge is now shared by exactly one original collar and one added bridge triangle; only the two outer collar rims remain open. Zero nonmanifold edges. A third material was assigned to new bridge faces. Blender original temporary object/mesh/material resources were all removed, restoring mode and selection. This is not a demonstration of existing *file* import/export or real authored object editing.

### New holdout case diagnostics

| Synthetic case | UV source | Max UV boundary discrepancy | Mean face-normal angle | Maximum face-normal angle | Combined CGAL | Audit |
|---|---|---:|---:|---:|---:|---|
| r11_clean_circle | continuous | **0.0000** | 8.70° | 18.53° | 0 | PASS |
| r11_lobed_collar | continuous | **0.0000** | 12.41° | 22.07° | 0 | PASS |
| r11_tilt_ellipse | continuous | **0.0000** | 16.33° | 46.74° | 0 | PASS |
| r11_split_circle | split | **0.2500** | 12.10° | 22.51° | 0 | PASS *detects mismatch* |
| r11_split_offset | split | **0.2500** | 30.75° | **56.35°** | 0 | PASS *detects mismatch* |
| r11_split_lobed | split | **0.2500** | 33.10° | 54.70° | 0 | PASS *detects mismatch* |

The maximum angle across *all* 14 candidate examples, including seen development, was **66.93°** on `r10_slender_forward`. No threshold for smooth shading was promised or met; large dihedral angles mean a visible ridge may remain. Nothing in this research transfers existing split UV islands across the bridge seamlessly.

### What the negative control proved

In all 14 controls, adding faces but leaving their UVs at `(0,0)` and material index 0 **did not corrupt the original collar faces**, so an audit that only checked old data would have falsely claimed success. The explicit bridge UV/material checks flagged **14/14 controls**, demonstrating detection capability for missing new-face attributes.

## Major caveats

1. **UV continuity is achieved only when the original source collars use the researcher's same cylindrical UV convention**; the three unseen split-UV cases show discontinuities. It is incorrect to call R11 automatic UV reconstruction or support for arbitrary painted seams.
2. **Source geometry is synthesized from the candidate strip itself**, making topological orientation and 3D placement particularly favorable. Real model files, nested disconnected shells, multiple UV layers, custom split normals, vertex colors, material slots, modifiers, Undo history, selection editing and library linkage were NOT tested. It does not yet add a bridge to an existing user asset.
3. **Normals are measured, not fixed.** New holdout maximum adjacent face-normal angle **56.35°**, and previous seen maximum **66.93°**. Smooth shading, normal interpolation, sharp-edge tags, and weighted normals are not preserved or newly implemented.
4. Standalone R10 restricts inputs to finite 3–48 XYZ points/loop, XY-radially monotone star-shaped contours with strictly separated Z envelopes. Arbitrary orientation, self-intersecting input, per-face UV islands, many holes, large production meshes, and different Blender versions unsupported.
5. **Blender Edit Mode tested in a disposable factory-startup scene.** No interactive human workflow, no file saved to disk, no user attachments, and no production support claim. Full joined CGAL success is only for 14 generated controlled cases.
6. A bridge UV projection and material assignment exists **only in the research test adapter**. It is not packaged as CBDK API/GUI and does not imply standalone R10 owns or preserves UV/material data.

## Research artifacts and reproduction

- [First full six-holdout Blender+CGAL research run](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42922222985) (job `r11-editmode-attributes-frozen-holdout` SUCCESS); earlier separate development-only pre-holdout smoke [CI #42922049754](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42922049754) SUCCESS.
- GitHub Actions artifact `geometry-lab-r11-*` contains `ci-r11-raw.json` (~1.73MB with full triangle data/source face signatures) and `ci-r11-eval.json` (~42KB with per-case UV/normal/material/CGAL results), retention 14 days. All synthetic.
- Actual full-run source SHA256:
  - `cycles/r11/fixtures.py`: `59e5b214bcfc5fecc34e29ef4361ebad240560cae0e0ec806d9df9d4bb5a4986`
  - `cycles/r11/blender_run.py`: `3caf884511e5fbf4c7b3a04ecb90fe80204204a0b5d8b748cd62d305687b1797`
  - `cycles/r11/evaluate.py`: `7838662142ec520ee75afbf43dbf3c2a2e92a4f098f6d42c185d63ea75bdd36c`
  - Frozen R10 `cbdk_geometry/quality_router.py`: `2aab08686733f487203510f0e52da8afcbef12cfe6a7f5254ac9c6ddb5cae66b`.
- Within `research/geometry_lab`, validated Blender4.4.3 (archive SHA-verified), then independent Python3.12 with `requirements-oracle.txt`. Never overwrite previous results:
```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r11/blender_run.py -- --output runs/my-r11-raw.json
python -m cycles.r11.evaluate --input runs/my-r11-raw.json --output runs/my-r11-eval.json
```

## Verdict and handoff

**R11 complete: attribute-preservation audit passed on the synthetic collars, full-mesh CGAL clean. Real model/UV island/normal integration is NOT approved.** Draft PR #114 stays open/unmerged. Team A receives this as *optional future review material*; no need to interrupt busy ABCD integration. No changes to R1–R10 code or their fixed data, ABCD, Development Intelligence Lab PR #115, main or shared STATE/Handoff. `approved=false`.

Potential **separate R12**: study boundary UV island transfer and continuity without destroying existing painted UVs, and independently test actual imported open surfaces (with permission, only private CI if non-public). **No R12 automatically started.**
