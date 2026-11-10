# R8 — Tapered-ring density for skinny triangles: independent experiment results

2026-11-11 JST. **Preregistered research gate PASSED; CBDK product adoption remains NOT approved.**

## Decision and experiment

The frozen R7 XYZ warped radial loft uses one dense internal ring count `k=max(n,m,12)` at all three interior sections. In the previously seen `r7_slender_offset` (37/12 vertices), a dense-to-sparse last strip generated a very skinny triangle, min quality **0.061831** (<0.1). R8 adds ONE distinct candidate `cbdk_geometry.tapered_loft.tapered_radial_loft`: three interior ring counts `k_h=max(12,round((1-h/4)*n+(h/4)*m))` for h=1,2,3. Angle-based sampling, triangulation, XYZ positions, original endpoint vertices and edges are unchanged except for the changed interior angular density. It does **not** move boundary vertices or run global mesh repair.

Before new holdout testing, a local reproduction on **old previously seen R7 artifacts** observed that all 10 old cases gained triangle quality, including `r7_slender_offset` from 0.06183 to ~0.12952. This was *development data*, not new holdout proof. The independent R8 run then froze a distinct six-case holdout (never used for algorithm tuning), plus the ten seen R7 cases. Original R5–R7 code and prior results were not modified.

Official Blender **4.4.3** (publisher SHA256 verified: `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`) generated all **16 synthetic cases × 3 methods = 48 configurations**, each with one warmup and **3** timed runs = 144 timed generations. Methods were frozen R8 taper, frozen R7, and native `bpy.ops.mesh.bridge_edge_loops(number_cuts=3,interpolation='LINEAR')`. A separate Python3.12+CGAL environment checked all 48. No failures were dropped or reported as clean after an oracle error.

### Pass/fail results

| Mode | Seen R7 cases /10 | Fresh R8 holdout /6 | Mean holdout minimum triangle quality | Mean holdout triangles | Holdout median generation milliseconds | Mean holdout analytic RMS |
|---|---:|---:|---:|---:|---:|---:|
| **R8 tapered loft** | **10** | **5** | **0.28952** | **189.3** | 3.246 | 0.02319 |
| R7 fixed-density loft | 9 | 3 | 0.18386 | 248.3 | 1.851 | **0.02112** |
| Blender 3-cut LINEAR | 8 | 3 | 0.15640 | 331.3 | **1.652** | 0.05493 |

The speed values are not fully like-for-like: native uses bpy edit-mode object setup/triangulation, whereas R7/R8 output detached Python mesh. **Even comparing R7 against R8 in similar Python paths, R8 incurs more geometry sampling cost**; its value is quality, not speed.

**Fresh R8 holdout, min quality and pass status:**

| New synthetic fixture | R8 tapered | R7 fixed | Native 3 Linear |
|---|---|---|---|
| r8_slender_tilt | **PASS**, q=0.122505 | FAIL, q=0.054330 | FAIL, q=0.074895 |
| r8_slender_opposite | **FAIL**, q=0.078598 | FAIL, q=0.052124 | FAIL, q=0.039209 |
| r8_offset_lobed | PASS, q=0.330963 | PASS, q=0.255641 | FAIL, q=0.190404 (analytic max=0.44612) |
| r8_sparse_bend | PASS, q=0.564956 | PASS, q=0.228088 | PASS, q=0.248362 |
| r8_ellipse_skew | **PASS**, q=0.152021 | FAIL, q=0.080453 | PASS, q=0.138355 |
| r8_wide_lobed | PASS, q=0.488060 | PASS, q=0.432519 | PASS, q=0.247192 |

Note: quality failures are NOT a substitute for all other gate conditions; `r8_slender_opposite` fails R8's min-quality cutoff despite shape error RMS=0.02609, max=0.09689 and CGAL crossings=0. New R8 holdout has all six min-quality values at least **0.015** larger than the fixed R7 baseline, exceeding the predetermined “≥2 fresh cases” requirement. R8 **does not** guarantee q>=0.1 for all slender shapes.

### Preregistered gates and independent checks

- Prior known R7 slender is **rescued**: R8 q=0.12952 >0.1, passes the full CGAL, boundary, topology and 3D analytic metric gates.
- Previous 9 R7 passes still pass, no previously passing synthetic case becomes a failure. R8 10/10 seen, frozen R7 9/10.
- R8 5/6 new holdout vs frozen R7 3/6; requirement ≥4 and no worse than R7 achieved.
- At least two fresh min-quality improvements ≥0.015: achieved **6/6**.
- **Zero CGAL self-intersections** across all 48 outputs; exact input boundary vertex and edge sets, connected topology, Euler=0, nonmanifold count=0 on all R8 outputs.
- No generation errors/oracle-unavailable configurations. No source or fixture changes after the first held-out execution. Original R8 candidate is **not** tuned or revised to repair the holdout failure.
- R8 added only research source/tests, 6 new synthetic fixtures, one cycle-specific pipeline, and documentation; no main/ABCD/PR#115/STATE/HANDOFF/private models.

## Trade-offs and limitations

- **Improved:** R7's known skinny-triangle failure is fully rescued; fresh 5/6 vs 3/6, and all six have higher minimum triangle quality. Mean triangles reduce to ~189 from R7 ~248 and native 3cut ~331.
- **Worse:** R8 median generation time ~3.25ms vs R7 ~1.85ms on the held-out cases (additional radial resampling), and author-designed analytic RMS mean increases from 0.02112 to 0.02319. Not a general performance win.
- **Unresolved:** the reverse slender case `r8_slender_opposite` still fails quality (q=0.078598). The design is not curvature-adaptive, not global quality optimization, and rejects arbitrary oriented or non-star-shaped/non-Z-separated boundaries. Existing Blender mesh integration, normals, UV, materials, edit history, user models, third-party blinded data, Blender versions beyond 4.4.3, visual artist judgments, and actual task time are not tested.
- **Oracle caveat:** the 3D analytic target is researcher-authored and samples a known parametric loft, not a source artist's desired surface; “passed” is only under this specific synthetic research rubric. The CGAL self-intersections test is independent of the R8 generator.

## Evidence and reproduce

- First verified R8 benchmark: [Geometry Lab CI run #42909533739](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42909533739), job `r8-tapered-triangle-quality` **SUCCESS**.
- GitHub Actions artifact `geometry-lab-r8-*`: `ci-r8-raw.json` (full generated meshes/3 timing repeats) and `ci-r8-eval.json` (per-case quality, shape RMS/max, topology, CGAL, source SHA), retention 14 days. Never commit raw generated copies of private models: this artifact consists only of synthetic fixtures.
- Actual code SHA256 verified from artifact:
  - `cbdk_geometry/tapered_loft.py`: `5734f3dfa5100360c596a1e9b80dd4d821d3af945707200ba20ba4fa86d6c8ab`
  - `cycles/r8/fixtures.py`: `9f7717cb6b3ab3d3f573386381f4eacb316da1be707d088b9e9a16e4445c8b68`
  - `cycles/r8/blender_run.py`: `5e7af0591b321e3a23d337a4ec1c88dca9897b3a41327e6a7eb4a65e328ae59c`
  - `cycles/r8/evaluate.py`: `c0640d152d383669180f694d46571a720c241bcf1486eec0221de8972e17e4e2`
- Local reproduction from `research/geometry_lab` with official checked Blender 4.4.3 and `requirements-oracle.txt`:

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r8/blender_run.py -- --output runs/new-r8-raw.json
python -m cycles.r8.evaluate --input runs/new-r8-raw.json --output runs/new-r8-eval.json
```

## Stop and governance

**R8 complete: research gate reached and algorithm retained as a promising but narrowly scoped candidate.** `approved=false`. Do not integrate into CBDK without A team review of production constraints. Draft PR #114 stays open/unmerged. No R9 is automatically started.

Potential next **separate** cycle: a topology-safe fallback on reverse slender configurations, or an independent nonplanar artist/model/UV evaluation. The R8 holdout is now seen and must not be used as fresh R9 evaluation.
