# R10 — quality-triggered R8 fast path / R9 repair (2026-11-11 JST)

## Decision

**The preregistered research gate PASSED on eight new synthetic holdouts, with 120/120 meshes independently checked. R10 remains research-only (`approved=false`), not a CBDK integration decision.**

On R9's six new prior synthetic shapes, the always-run R9 repair cost ~90.9 ms median versus ~7.3 ms for R8. R10 uses the cheap R8 output by default and **only invokes the frozen R9 internal edge-flip core when the R8 minimum triangle quality is below 0.1**. The R8 mesh is generated once; the R9 wrapper is *not* re-called, so repair does not duplicate initial geometry generation.

The trigger checks one local quality metric. It **cannot establish** CGAL collision freedom, correct UV/normals, manifoldness, or analytically correct shape. R10 returns a mesh even if repair fails the full quality rubric; a separate evaluator is required. R8/R9 source and previous fixtures/results remain frozen.

## Execution and controlled comparison

- [R10 preregistration](RESEARCH.md) was committed **before any new R10 holdout execution**. Eight authored synthetic test shapes (not private, not third-party blind). All prior 22 R7/R8/R9 fixtures are development data; they are *not* new evidence.
- Official Blender **4.4.3** archive downloaded and verified against Blender publisher SHA256 `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`.
- Methods: R10 quality dispatch, frozen R8 taper, frozen always-run R9, official native Blender 3-cut LINEAR. Same float32-rounded input XY star-shaped, disjoint Z-envelope nonplanar loops.
- **30 cases × 4 methods = 120 distinct meshes**; one warmup and **3 timed repeats** per combination (=360 timed generations). Independent Python3.12+CGAL 6.0.1 verified all 120, **zero CGAL intersections**, original boundary vertices and edges preserved for R10, valid topology and no unavailable evaluation. R7 analytic loft error and min triangle quality gates unchanged: q≥0.1, RMS≤0.12, max≤0.28.
- The new benchmark did **not** modify R10 code, holdout inputs or preregistration criteria after first execution.

## Pass/fail results

| Method | Previously seen 22 | Fresh R10 8 holdouts | Fresh mean triangles | Fresh mean min triangle quality | Fresh mean 3D synthetic RMS |
|---|---:|---:|---:|---:|---:|
| **R10 conditional** | **21/22** | **8/8** | 192.375 | 0.364498 | 0.019519 |
| Frozen R9 always repair | **21/22** | **8/8** | 192.375 | **0.403012** | **0.019472** |
| Frozen R8 no repair | 19/22 | 6/8 | 192.375 | 0.351347 | 0.019518 |
| Official Blender native 3-cut LINEAR | 13/22 | 4/8 | 336.875 | 0.161827 | 0.037508 |

R10 exactly matched R9's pass/fail on **all 22 previously seen cases**, including the R9 known failure `r9_reverse_narrow`. Prior R8 failure `r8_slender_opposite` remained rescued. Among eight new holdouts, **six** used R8 fast path without changing a single mesh vertex or triangle index. **Two** (`r10_slender_reversed`, `r10_narrow_opposed`) failed R8 q threshold and switched to the face-only R9 core. Both then passed full CGAL/topology/shape/triangle quality; neither introduced regressions.

| New synthetic case | Dispatch | R10 q | R8 q | R9 q | Blender native q | R10 pass |
|---|---|---:|---:|---:|---:|---|
| r10_circle_mild | fast | 0.74897 | 0.74897 | 0.74897 | 0.32392 | PASS |
| r10_lobed_waves | fast | 0.64722 | 0.64722 | 0.64722 | 0.23306 | PASS |
| r10_slender_reversed | **repair** | **0.13652** | 0.07298 | 0.13652 | 0.04172 | **PASS (R8 FAIL)** |
| r10_slender_forward | fast | 0.19682 | 0.19682 | **0.30303** | 0.07729 | PASS |
| r10_narrow_opposed | **repair** | **0.11407** | 0.07240 | 0.11407 | 0.03099 | **PASS (R8 FAIL)** |
| r10_far_lobed | fast | 0.32483 | 0.32483 | 0.32483 | 0.17183 | PASS |
| r10_skew_ellipse | fast | 0.23133 | 0.23133 | **0.43324** | 0.16012 | PASS |
| r10_wave_circle | fast | 0.51621 | 0.51621 | 0.51621 | 0.25569 | PASS |

**Trade-off:** R10 skipped quality improvements that R9 could still make on two already-passing fresh cases, e.g. `r10_skew_ellipse` q 0.23133 vs full R9 q 0.43324. R10 optimizes *passing the frozen rubric* with less computation, not maximum triangle quality.

### Actual runtime measurements

All values are **case-level medians of three runs**, measured on the same GitHub Actions Linux host, and the ratios below are matched within that run. R10/R8/R9 detached Python are comparable. Native bpy context is a different workload.

| Method | Mean per-case time on fresh 8 | Median per-case time on fresh 8 |
|---|---:|---:|
| **R10 conditional** | **34.607 ms** | **7.194 ms** |
| R9 always repair | 68.935 ms | 50.326 ms |
| R8 no repair | **6.859 ms** | **6.816 ms** |
| Blender native 3-cut | 2.754 ms | 2.762 ms |

Six fast-path cases only: R10 median **6.810 ms**, R9 median **40.595 ms**, ratio **0.16774** (~83.2% reduction in this subset). Over all eight holdouts, mean time ratio R10/R9 = **0.50202** (~49.8% mean reduction). Both measured speed gates were satisfied (fast<=0.65; all<=0.8). The repair subset remains expensive due to frozen R9's Python iteration; performance is not a universal bound.

These times do **not** establish that R10 is always faster than Blender native or that all production workflows benefit. In the new holdout, R10 is **~5 times slower than R8 alone by arithmetic means**, which is the cost of rescuing two otherwise-failing cases. A GPU, other Blender version, high-poly mesh or actual user interaction can differ substantially.

### Frozen research gate checklist

- Old R9 outcomes identical on **22/22** and all known R9 successes preserved; known reverse slender rescue preserved: **PASS**
- New holdout R10≥5/8 and ≥R8, with ≥1 formerly failed R8 case rescued and no regression: **PASS** (8/8 vs 6/8, two rescues)
- Per-case exact R8 XYZ+triangles, and route output exactly matches frozen R8 on fast or frozen R9 on repair: **PASS**, 0 invariant violations, all 30 cases
- Fresh fast path count ≥3: **PASS** (6)
- Fast-path matched R10/R9 median-time ratio ≤0.65: **PASS** (0.16774)
- All-eight mean-time ratio ≤0.8: **PASS** (0.50202)
- Independent CGAL 0, original boundaries unchanged, valid connected strip topology, no oracle omissions: **PASS**, all 120 cases
- No post-holdout tuning: **PASS**

## Failure modes, caveats and next governance

The 22 known cases still include the stubborn `r9_reverse_narrow`, which is **not solved by dispatch**, and R10 correctly reports it as failed in the independent evaluation. The router is deliberately **blind** to non-quality failures: if an R8 mesh has q≥0.1 yet crosses itself or misses the analytic surface, R10 will pass it unchanged and the separate oracle will reject it. That limitation prevents treating this as a production-safe automatic repair.

All R8 input restrictions remain: finite 3–48 XYZ loop vertices; simple XY-star-shaped angularly monotone boundaries; strict positive Z separation; no general arbitrarily oriented curves, branching, and no UV/normals/materials/undo/artist judgments. The eight test shapes were made by the researcher and are not independent real assets. A new R11 must not reuse R10 fresh data as unseen. Any full CBDK integration requires A commander review and real mesh/UV/normal validation.

**One R10 cycle ended.** Candidate `promising_unapproved` only. Draft PR #114 stays Draft/unmerged. R1–R9 source and results, main/ABCD/DIL PR #115/STATE/Handoff/private assets are untouched. No R11 auto-start.

## Evidence and exact reproducibility

- Initial successful run: [R10 official Blender + CGAL CI #42915469986](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915469986). Job `r10-conditional-quality-router` SUCCESS; artifact `geometry-lab-r10-*` includes 3.49 MB raw mesh JSON and full evaluation `ci-r10-eval.json`, 14-day GitHub retention.
- Source SHA256 captured by actual independent evaluation:
  - `cbdk_geometry/quality_router.py`: `2aab08686733f487203510f0e52da8afcbef12cfe6a7f5254ac9c6ddb5cae66b`
  - `cycles/r10/fixtures.py`: `eb08b4d37a5442724f9cae69aad4fe70af49c2e7741253dce58255c4c2a6e931`
  - `cycles/r10/blender_run.py`: `e6f86d6b627f0b16cd2d2ab98280432e0231513beabf1e11e93f077af9d18f5b`
  - `cycles/r10/evaluate.py`: `df13204d4817af32f0c49e7db4f035c978a2cbc7f1152e2a61d4bf65aedf4f33`
- In `research/geometry_lab`, use verified official Blender 4.4.3 and `requirements-oracle.txt` in separate Python 3.12:

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r10/blender_run.py -- --output runs/r10-raw-new.json
python -m cycles.r10.evaluate --input runs/r10-raw-new.json --output runs/r10-eval-new.json
```
