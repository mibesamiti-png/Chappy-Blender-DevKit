# R19 — conservative boundary tangency refinement: NOT PREFERRED

**Frozen research gate failed. 12/12 final outputs safe under the specified checks, only 1/12 improved boundary-angle p95 by at least 5% (required >=6/12). No product approval.**

R18 final HEAD passed four workflows. R19 consumed the same-run R18 raw Blender 4.4.3 candidate-arm arrays. All 12 are previously seen synthetic assembled geometries; no fresh holdout. This was detached geometry refinement, not a Blender shading or custom-normal experiment. All source vertices including bridge boundary vertices, corner UVs, face connectivity and seam/material metadata were held fixed. Three regularization weights times five step fractions, 15 trials per case. R7 geometry assessment, R14 UV audit and joined CGAL required for accepted outputs; original R18 retained if no admissible improvement.

## Measured results
| Case | Before p95 degrees | After p95 degrees | Reduction | Rejected at normal screen | Rejected at UV screen | Selected method |
|---|---:|---:|---:|---:|---:|---|
| r16_circle | 19.451 | 15.231 | 21.70% | 4 | 6 | smooth1.0_step1.0 |
| r16_ellipse | 36.081 | 36.081 | 0.00% | 0 | 15 | baseline |
| r16_sparse | 27.654 | 27.654 | 0.00% | 3 | 12 | baseline |
| r16_skew | 35.640 | 35.640 | 0.00% | 4 | 11 | baseline |
| r17_round | 18.227 | 18.227 | 0.00% | 3 | 12 | baseline |
| r17_oval | 31.560 | 31.560 | 0.00% | 1 | 14 | baseline |
| r17_lobed | 16.629 | 16.629 | 0.00% | 5 | 10 | baseline |
| r17_offset | 39.582 | 39.582 | 0.00% | 7 | 8 | baseline |
| r17_taper | 47.557 | 47.557 | 0.00% | 3 | 12 | baseline |
| r17_sparse | 25.643 | 25.643 | 0.00% | 3 | 12 | baseline |
| r17_wave | 20.002 | 20.002 | 0.00% | 6 | 9 | baseline |
| r17_skew | 35.132 | 35.132 | 0.00% | 3 | 12 | baseline |

- 180 attempted candidates, 42 rejected at normal screen, 133 at UV anisotropy screen, 0 at geometry screen, 5 surviving preliminary screens. 0 subsequently rejected by final geometry/CGAL screen among tested shortlisted candidates. These are sequential first-failure counts, not independent causal frequencies; not every rejected trial received CGAL.
- Only r16_circle selected a moved geometry (p95 19.451 -> 15.231 deg, max 19.588 -> 15.809 deg, mean 9.621 -> 7.495 deg, maximum displacement 0.021087 model units). Remaining 11 returned exact baseline. Mean relative p95 improvement across 12 including fallbacks 1.808%. Worst case max 54.111 deg remains.
- All 12 selected/fallback outputs pass the specified source XYZ, R7 geometry, joined CGAL=0, UV overlap/winding/degeneracy/island and anisotropy checks. This does NOT mean all attempted candidates were safe. No evidence that these constraints are mathematically impossible in general.
- Dominant observed rejection is anisotropy increase with fixed UV. Next proposed research: compare the same geometric displacements with constrained UV reoptimization (R17-style, fixed source boundary and seam), retaining strict original acceptance metrics. Separate geometric shape from custom normals/shading. No automatic R20; no post-result threshold changes.

## Evidence
First R19 CI https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520668308/job/138891772333 failed as intended because improvement gate failed. R17 and R18 dependencies passed. Unrelated R13 Blender acquisition failed, R14/R15 skipped due to dependency; whole workflow not green. Raw and evaluation data in same-run artifacts, retention 14 days. Source hashes: {"cycles/r19/refine.py":"c6dbde47bc6c62f8f53b51cef5459dd5475f60b300e9b1e9f32dfc2019daf510","cycles/r19/run.py":"a05479c9dcdc44b22170da0068da3b4fc2ca2d560cb7ae7c2fd53ff7bd35c49c"}. Only synthetic data, no new Blender roundtrip or rendered appearance. R1–R18 code/results unchanged. No A action. PR #114 Draft, approved=false. Preserve negative outcome; do not rerun or relax gate to manufacture success.
