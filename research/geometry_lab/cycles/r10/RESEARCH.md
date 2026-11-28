# R10 preregistration — quality-triggered R8 fast path + R9 local repair

## Decision set before first fresh holdout run

R8's nonplanar XY-star-shaped boundary loft is much lighter than full R9 diagonal flipping, but known skinny triangles can be improved by R9. R9's 6-case median runtime was ~90.93 ms vs R8 ~7.26 ms, while R9 won only one extra new case. **Do not run the expensive R9 repair on already-acceptable R8 mesh**.

### Exactly one algorithm and frozen dispatch

1. Compute frozen R8 `tapered_radial_loft` **once** (do not invoke R9 wrapper which re-generates R8).
2. Compute min triangle quality using the same mean-ratio formula `4*sqrt(3)*area / sum(edge_length_squared)` as R7's independent evaluator. This *local cheap score* is only an optimization trigger, **not** validation for CGAL, analytic shape, or topology.
3. If `min_quality >= 0.1`, **return the original R8 mesh unchanged** (same vertices and faces, no flips).
4. Otherwise, run R9's frozen `_one_pass` internal-edge flip core for at most **3** passes using the already-generated R8 mesh. Return the resulting mesh even if q remains below threshold (no pretending the result passed). No candidate search/parameter tuning and no runtime CGAL claims. `approved=false`.
5. Never move any input vertex or boundary edge, increase vertex/triangle count, mutate scene or handle unsanitized input beyond R8's limits.

### Synthetic cases

All **22 previously seen** R7–R9 cases are `development`, including prior R9 holdout (`r9_reverse_narrow` is now known). **8 new** fixed R10 synthetic holdouts in `cycles/r10/fixtures.py`; author-designed, not blind third-party data or private assets. Three arms: conditional R10, frozen R8 baseline, frozen R9 always-run; fourth official Blender 4.4.3 native Bridge 3 cuts LINEAR context comparator. Cases typed as float32 for all four methods. Exactly 30 shapes×4 methods = 120 generated meshes; 1 warmup +3 timed repeats per method/case; budgets 10 s/call, <60k vertices/20k faces, overall ~14 min research workflow job.

### Independent acceptance and cost gate

Use original independent R7 3D analytic shape/quality/oracle evaluator unchanged (CGAL6.0.1 on Python3.12 outside Blender), including all original 3D boundary vertices **and boundary edges**, components=1, Euler=0, nonmanifold=0, self-intersection=0, min triangle quality >=0.1, RMS<=0.12 and max<=0.28. Run oracle on every output, including failures.

Research passes ONLY if all are met:
- All 22 **known** conditional R10 cases have the **same pass/fail as the frozen R9** (R9's 21 prior successes preserved); and known `r8_slender_opposite` passes. A quality trigger cannot detect non-quality failures, so report any difference. Zero CGAL intersections/topological/boundary faults on **all** R10 outputs.
- On **8 new** cases, conditional R10 passes at least as many as R8 and at least **5/8**. At least **one fresh case** fails frozen R8 but passes conditional R10, without losing any fresh R8 pass. No per-case cherry picking after results.
- On *each* of the eight holdouts, if R8 mesh min-quality >=0.1 then R10 vertices/faces must be **bit-for-bit identical** to R8, with dispatch="fast". If quality <0.1, R10 output must be **bit-for-bit identical** to the frozen R9 wrapper result (including faces), with dispatch="repair". All R10 vertex coordinates and triangle counts always equal R8.
- **Fast subset:** >=3 fresh holdout cases take fast path; median R10 timing across this fast subset <= **0.65 ×** frozen full R9 on the same subset (same host/3 timed repeats, report actual paired ratios), and mean R10 time over all 8 holdout cases <= **0.8 ×** full R9. Both are required; even if the quality gate succeeds, a slow router has no justified advantage.
- No algorithm or fixture changes after first heldout run. If any clause fails, stop and record `not_preferred`; do not rework or retest using the same fresh holdout.

### Limitations

Research-only: limited to R8 input contract (3–48 points each, XY-radially monotone / star-shaped, fully disjoint Z envelopes). This *does not* make arbitrary nonplanar meshes safe. Local quality thresholds do not guarantee surface self-intersection freedom or material/UV/normal preservation, and may keep an R8 output that fails a non-quality metric. No actual user, private, business, or third-party models. No commercial CBDK integration without team A approval. Only `research/geometry_lab/**` and dedicated `.github/workflows/geometry-lab.yml`. PR #114 remains Draft, not merged; R1–R9 records unchanged. **R11 must not start automatically.**
