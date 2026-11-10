# R6 — Blender official Bridge Edge Loops vs frozen R5: measured result

Measured 2026-11-11 JST. **A single research cycle finished. The preregistered research advantage gate passed; product adoption remains unapproved.**

## Provenance and protocol

- PR #114 branch `research/geometry-lab-20261110`; no main merge. Blender official Linux **4.4.3** (build `802179c51ccc`), downloaded and checked against publisher SHA256 **`8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`**.
- 20 synthetic cases × 5 methods × 3 timed repetitions (+1 warmup) = **100 distinct mesh configurations, 300 timed generations**. First 15 cases are R4/R5 previously seen regressions; last 5 are new R6 holdout fixed before running. One Blender version and one GitHub Linux runner. No user/private models.
- Frozen R5 (`radial_loft(a,b,cuts=3)`); native `bpy.ops.mesh.bridge_edge_loops`: 0 cuts PATH, or 3 cuts LINEAR/PATH/SURFACE. Smoothness 1, profile factor 0, twist 0. All have the same float32-rounded input rings.
- Independent Python3.12 CGAL oracle and R4/R5 analytic centroid-loft error/triangle quality thresholds: no CGAL self-crossings, unchanged input boundary vertices **and edges**, manifold topological strip, min triangle quality≥0.1, RMS≤0.08, max≤0.2. Each candidate gets its own pass/fail; do not discard bad native settings.
- No generator/model tuning after new holdout. Temporary Blender objects removed; scene, datablocks, active/selected object state restored. Research source and data are review-only. Neither Blender GUI mouse workflow nor real meshes are assessed.

## Core results

| Method | **New R6 holdout passes /5** | Previously seen passes /15 | New holdout median generation ms | Mean vertices / new5 | Mean triangles / new5 |
|---|---:|---:|---:|---:|---:|
| R5 Radial Loft (frozen) | **5** | **13** | **2.835** | 118.2 | 196.8 |
| Blender no-cuts PATH | 3 | 11 | 1.740 | 39.6 | 39.6 |
| Blender 3 cuts LINEAR | 3 | 11 | 2.627 | 158.4 | 277.2 |
| Blender 3 cuts PATH | 1 | 6 | 2.586 | 158.4 | 277.2 |
| Blender 3 cuts SURFACE | 2 | 7 | 2.568 | 158.4 | 277.2 |

All **100 configurations generated**, and all were independently evaluated (no oracle-unavailable / generation-error). The R5 holdout 5/5 exceeds the **best single standard 3-cut variant 3/5 by two cases**, clearing the predefined +1 threshold. R5 has no CGAL hits on these new cases. The best standard variant LINEAR also has zero CGAL hits; the advantage is shape/triangle quality on two difficult shapes, not that native modes are universally defective.

**Caution:** R5 direct NumPy/mesh creation versus native bpy edit-mode context and triangulation does **not** have identical overhead. Both run on the same host, but speed differences of ~0.2ms are not a defensible product-speed advantage. R5 can use more triangles than the *no-cuts* standard, while fewer than the 3-cuts standard. The current figures are for only this 5-shape sample.

### New R6 fresh shapes (✓=pass; ✗=fail)

| Synthetic fixture | R5 | Native 0 PATH | Native 3 LINEAR | Native 3 PATH | Native 3 SURFACE |
|---|---|---|---|---|---|
| r6_twisted_lobed | ✓ | ✓ | ✓ | ✗ | ✗ |
| r6_ellipse_tall | ✓ | ✓ | ✓ | ✗ | ✓ |
| r6_sparse_circle | ✓ | ✓ | ✓ | ✓ | ✓ |
| r6_slender_shift | **✓** | ✗ | ✗ | ✗ | ✗ |
| r6_far_lobed | **✓** | ✗ | ✗ | ✗ | ✗ |

Notable failures (not silently filtered):
- **r6_slender_shift:** native 3 LINEAR min triangle quality 0.0861 (<0.1), while R5 0.1089; R5 analytic RMS 0.0078 versus native LINEAR 0.0243.
- **r6_far_lobed:** native 3 LINEAR RMS 0.1696 / max 0.5990, both violating limits, despite min quality 0.1604. R5 RMS 0.0219 / max 0.0480.
- Native 3 PATH with `smoothness=1` sometimes overshoots or self-intersects. On the new holdout, it has a total of 51 CGAL intersection pairs, concentrated in 3 cases, and SURFACE has 40. This **does not imply** that alternative smoothness/profile values or manual intervention cannot improve standard Blender outputs.
- On previously seen `holdout_lowpoly`, R5 remains a failure (RMS 0.1039), while Blender native 3 LINEAR, PATH and SURFACE pass. The R5 method is not a universal replacement.
- On previously seen `r5_ellipse_offset`, all five methods fail. R5's min quality remains 0.0634.

### Shape and topology

Every R6 fresh R5 output preserves its original boundary edge set, is topologically valid under the research checks and has **0** CGAL self-intersection pairs. In these 5 inputs, R5 average centroid RMS 0.0288; Blender native 3 LINEAR average 0.0590. These error values reflect the **synthetic author-chosen analytic loft**, not a human's preferred sculptural surface or material/UV fidelity. The previously used analytic target samples do not model upper-ring phase for lobed fixtures and ignore area/Hausdorff/curvature; retain as explicit metric bias.

## Decision and limitations

**Research conclusion:** keep the R5 radial loft as a promising, narrow, research-only candidate; the hypothesis that Blender's 3-cuts operator is always sufficient is **not supported** on this synthetic corpus. No CBDK integration now: `approved=false`, existing Blender baseline unaffected.

**What improves:** new holdout 5 vs 3 passes, sometimes lower geometric error and less triangulation than native 3-cuts on difficult offset/star-shaped planar loops. **What worsens/remains:** 3 internal rings and more faces than no-cuts baseline; native 3 LINEAR improves low-poly cases R5 cannot; no demonstrated general Blender speed benefit; R5 does not support non-planar/branching/non-star-shaped targets or an existing mesh's UV/normals/materials.

**Unverified and stop:** no third-party blind mesh, real edit/Undo workflow, A/B artist scoring, actual working time, nonplanar surfaces, other Blender versions, new shape scales, alternate native smoothness/profile optimization or 3D topology improvement. R6 is ended after the frozen comparison rather than tweaking R5 or continuing into R7.

**Next research candidate (not started):** test radial/R5 on a diverse independent **nonplanar** / star-shaped volume set with a user-visible quality criterion, or combine native 3 LINEAR first with a targeted fallback for only extreme offset cases. A commander review is required for any CBDK implementation.

## Reproducibility / actual CI

- [R6 GitHub Actions](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905626479), `r6-native-bridge` and `exact-oracle` jobs SUCCESS, no skipped oracle. 33 existing research unit tests also passed.
- CI artifacts (`geometry-lab-r6-*`): `ci-r6-raw.json` (same-generator meshes, repeat times, source hashes) and `ci-r6-eval.json` (all passes, failures, quality). CI retention 14 days. The full synthetic raw mesh data stays in artifact; not committed to public history.
- SHA256 from the actual result: `cycles/r6/fixtures.py` = `43ed2215c3bf9b0a3aeb652cba476cf357a9785d045013624e528e9599c8fa1a`; `cycles/r6/blender_run.py` = `546c11dd28ba4db3187860739d351d5b583df4f71524d6922d448047157f69b5`; `cycles/r6/evaluate.py` = `e6bdff6a063f451cd0aa7ab841c2252b7844ae2fce96c67406ba8c01b8172272`; original R5 `cbdk_geometry/radial_loft.py` = `0b404cc2f5b8b6440b7ab44035a608a41942c8efb329c2a3028df014d175c7ac`.
- Commands: in `research/geometry_lab`, use the approved research workflow. Equivalent local CLI (when official Blender4.4.3 and Python3.12+CGAL installed):
  `blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r6/blender_run.py -- --output runs/r6-raw-new.json`
  then `python -m cycles.r6.evaluate --input runs/r6-raw-new.json --output runs/r6-eval-new.json`.
- First infra error: Blender's built-in `cycles` namespace prevented importing the research `cycles.r6` module. Corrected fixture import isolation **before any output generation**. SHA256-verified official executable and all 100 configurations generated successfully on the subsequent run. This environment fix did not modify R5 or the frozen R6 fixture/evaluation.
