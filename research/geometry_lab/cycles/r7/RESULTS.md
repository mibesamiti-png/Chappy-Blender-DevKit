# R7 — mildly nonplanar radial loft, independently verified (2026-11-11 JST)

## Decision

**Preregistered research gate achieved: promising review-only proposal, not a CBDK product adoption.**
An XY-radial 3D interpolation candidate (`warped_radial_loft`) preserves original Z-varying boundary vertices and edges and generated collision-free synthetic strips on all 10 measured cases. **Never claim general arbitrarily tilted, branching, or non-star-shaped 3D support.** `approved=false`.

## Source / method / independence

- Parent branch at start: `research/geometry-lab-20261110` HEAD `1e24aa1551032279917437db550864e82fa0ece5`. R5/R6 preserved; PR #114 remains Draft.
- Candidate: `cbdk_geometry.warped_loft.warped_radial_loft(a,b,cuts=3)`. XY polar angle correspondence, 3D polygon edge ray interpolation (retains Z), 3 intermediate 3D rings, no mutation of original rings. Limits: each loop 3–48 XYZ vertices, finite/simple, XY star-shaped and angularly monotone, strict positive global Z separation. Not arbitrary 3D curve matching.
- Native comparator: official Blender 4.4.3 `bpy.ops.mesh.bridge_edge_loops` 3-cut LINEAR (primary) and no-cut PATH (secondary). Same float32-rounded inputs. Caller overhead differs; **speed is reported, not interpreted as performance superiority**.
- New synthetic corpus only: 4 development, 6 frozen holdout, none from user, third-party, or production. Each method/shape: 1 warmup + 3 timed runs. 10 × 3 = **30 generated and independently evaluated meshes**, 90 timed runs. One GitHub Linux host, one Blender version.
- Independent Python3.12 CGAL `self_intersections`; input edge coordinate sets, Euler=0, connected components=1, nonmanifold edges=0. Triangle quality≥0.1 and sampled analytic 3D loft RMS≤0.12, max≤0.28; the latter is measured at triangle centroids against 384×33 dense parametric target grid. **This target was designed by the same researcher and may favor a correspondence style; not a third-party blind validation.**
- All 30 cases generated; zero oracle-unavailable; zero intersections, no topology or original-boundary violations in all three modes. R5 is expected to reject the undulating rings and its original implementation is not changed.
- R7 native Blender archive SHA256 published `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`, verified before execution.

## Frozen R7 verdict

| Method | Development pass /4 | New held-out pass /6 | Mean held-out triangles | Median held-out generator ms | Mean held-out analytic RMS |
|---|---:|---:|---:|---:|---:|
| R7 warped radial | **4** | **5** | 214.2 | 2.188 | 0.02253 |
| Blender native 3-cut LINEAR | **4** | 4 | 309.2 | 1.948 | 0.04419 |
| Blender native 0-cut PATH | **4** | 4 | 44.2 | 1.277 | 0.05104 |

*Native vs detached-Python timings have different overhead and mesh outputs. Do not assert R7 is globally faster. R7 has more triangles than the no-cut comparator, though fewer than the 3-cut one for these six inputs.*

| New fixed holdout case | R7 | Native 3 LINEAR | Native 0 PATH | R7 min triangle quality | R7 CGAL hits |
|---|---|---|---|---:|---:|
| r7_lobed_wave | PASS | PASS | PASS | 0.42314 | 0 |
| r7_ellipse_tilt | PASS | PASS | PASS | 0.22888 | 0 |
| r7_sparse_circle | PASS | PASS | PASS | 0.22458 | 0 |
| r7_slender_offset | **FAIL** | FAIL | FAIL | **0.06183** | 0 |
| r7_far_lobed | **PASS** | FAIL | FAIL | 0.21816 | 0 |
| r7_opposed_waves | PASS | PASS | PASS | 0.45136 | 0 |

Held-out pass gate set before first execution: candidate ≥4/6 **and** ≥1 over native 3-LINEAR, with no candidate topology violations/self-crossings. Achieved **5/6 vs 4/6**, delta **+1**, zero self-crossings, 0 evaluation exceptions. After first holdout **zero algorithm and fixture changes**.

### Failures and tradeoffs

- **r7_slender_offset:** fails triangle-quality threshold (R7 0.06183 <0.1), although RMS 0.01503 and max 0.03450 are under limits, topology valid and CGAL 0. Native 3 LINEAR quality 0.08456 also fails. The R7 triangle-quality score is **worse than native** on this one shape. Do not treat "no collisions" as a valid result when skinny triangles remain.
- **r7_far_lobed:** native 3 LINEAR fails analytic max 0.45295 (>0.28) while R7 0.03621; R7 passes, CGAL 0. Distinction depends on author-selected analytic loft, not real artist quality.
- **r7_sparse_circle:** native 3 LINEAR quality 0.36197 > R7 0.22458, and native RMS 0.03861 < R7 0.04985; **R7 is not uniformly better**.
- No algorithmic speed dominance. Extra intermediate triangles compared with no-cuts can increase later editing expense. Non-star-shaped profiles, non-Z-monotone ring envelopes, arbitrary oriented planes, hole branching, UV/normals/material preservation, real manual workflow and alternate Blender versions **unverified**.
- Blender's built-in interpolated bridge remains the default production tool; R7 should only be considered as a **possible specialized fallback** after A review and further genuinely independent modeling validation.

## Execution record & reproducibility

- [Completed R7 independent CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42907699732): `r7-nonplanar-bridge` SUCCESS, `r6-native-bridge` SUCCESS, `exact-oracle` SUCCESS. Full raw meshes and sampled scores in `geometry-lab-r7-*` artifact, retention 14 days.
- Original source SHA256 recorded by the measurement:
  - `cbdk_geometry/warped_loft.py`: `5422e828dec0f09d59dc75dd14ac63c0170385b30e95e6f67fc95b1047c81266`
  - `cycles/r7/fixtures.py`: `a455b44b8a5b1205995a0cd40c4dc063731681cb5b5a980a35cf0b7e582a8663`
  - `cycles/r7/blender_run.py`: `12fadfec37c322cc447d7e85c0b76b7fac5b99a8a15ba1af45d883304e9ccfcb`
  - `cycles/r7/evaluate.py`: `c572b8acf62f64ee1cf72fca879dc036951ca216727c637e0f431d557aa91173`.
- In `research/geometry_lab`, install `requirements-oracle.txt` and verified Blender4.4.3, then run:
  `blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r7/blender_run.py -- --output runs/new-r7-raw.json`
  and `python -m cycles.r7.evaluate --input runs/new-r7-raw.json --output runs/new-r7-eval.json`.
- Never overwrite a prior run output. All R1–R6 results, experimental algorithms and frozen datasets are retained unchanged. Only Geometry Lab ownership and its dedicated workflow modified.

## Stop / next

Research result `promising_research_candidate`. **R7 complete**; no further optimization or new R8 cycle without a separate instruction. Future candidate: validate *general* curved/nonplanar boundaries in independent fixtures; test geometry quality with original surface normals/UV and actual editing conditions; or research a selective, deterministic repair for skinny triangles. A commander decides product integration after review; no merge into main, shared STATE, handoff, ABCD or PR #115.
