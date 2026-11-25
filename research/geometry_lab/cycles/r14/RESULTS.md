# R14 — retrospective UV distortion, overlap and boundary-normal audit

**Local historical-output audit completed, 9/9 analytic controls passed for each input. Existing UV mapping is NOT ready for product adoption.** GitHub CI reproduction is separate from the local measured results.

## Evidence
Read only the saved Blender 4.4.3 raw JSON from previously completed R11–R13 workflows. No user assets, new Blender generation or new holdout in the local audit. Shapely 2.1.2/GEOS, NumPy 2.3.5, Python 3.13.5. Input hashes:
- R11: fd64528395e2c6efcb497060447d616261ade0e24edd8b3959d99360e36aec5d
- R12: 5ad9d3688662c1c1183e30e90bfa6c0eb26ebfcc17738a4ba9696d6eeb7d210e
- R13: 52068ec5a47ea13caa86fd5fc2a175e2375cc1cc2b5ef681e3c8570aba68597a
- Tested audit source SHA256: c2fcbaefb7863739882dea8248ca3d6183f3fecb0929b81979a16c4e819b87f6.

## Results
| Corpus / arm | Outputs with UV overlap | Pair count | Same inferred UV island pairs | Same-island pairs >1e-6 | UV-degenerate faces |
|---|---:|---:|---:|---:|---:|
| R12 / R11 cylindrical seed | 12/12 | 6413 | 6413 | 6355 | 0 |
| R12 / R12 chart transfer | 12/12 | 7576 | 2811 | 2716 | 0 |
| R13 / R12 nearest chart | 12/12 | 8164 | 1814 | 1755 | 0 |
| R13 / R13 seam optimized | 12/12 | 7646 | 4765 | 4653 | 0 |

All 48 UV outputs have positive-area overlaps even at the stricter 1e-6 threshold and mixed UV winding within at least one connected island. R13 reduces total pair count but **increases same-island overlap** relative to R12 on the same corpus; same-island pair area sum 3.3615 -> 7.9471 UV^2. This is a pair sum, NOT atlas union area. It is partly affected by changes to island connectivity, so it is not by itself a causal measure of increased geometric folding. Eight formerly-held-out R13 shapes (now seen) show the same trend: 1716 -> 3446 same-island pairs; at 1e-6: 1663 -> 3360. R13's seam-count/length gains remain valid for those previous metrics only.

R13 arm local anisotropy: median of 12 case-level p95 values 8.8754, worst case-level p95 12.2334, maximum triangle singular-value ratio 18.6872. R12 arm of the same R13 corpus gives effectively identical distortion (per-face translation cannot change the Jacobian except numerical roundoff). Both arms have 97 triangles whose U range exceeds .5; the cylindrical angular wrap is a plausible contributor to folded UVs, not yet isolated as the cause. The new metric does not label all large U spans as bugs.

### Normals
All 76 output meshes independently audited for geometric source/bridge face-normal angles. R11's 28 maxima matched the old Blender measurements within 5.3e-6 degrees (cross-check limit 1e-3). Maximum angles: R11 66.9298 deg, R12 62.0038 deg, R13 61.3477 deg. Different shape corpora are not an improvement comparison. The R13/R12 UV arms have identical XYZ and angles for paired cases. No normal correction was implemented. R11 raw archive lacks bridge corner UV arrays; UV audit unavailable for that corpus, not imputed.

## Verdict
The audit works on controlled data and detects known faults; the UV result is a **negative** finding. Do not infer production-quality texture continuity from prior boundary-match or CGAL gates. 3D CGAL collision tests address a different space. All inputs are synthetic; no rendered checker texture, arbitrary imported model, source+bridge UV overlap, explicit stacked-island intent, tile-aware overlap, or custom shading normals verified. This diagnostic uses finite-precision GEOS with absolute-scale thresholds, not an exact UV oracle. Nine analytical controls are limited, not exhaustive validation.

R15 candidate (NOT started): isolate cylindrical U wrap, explicit seam-consistent angular unwrapping and a boundary-constrained UV solver; require zero same-island folds/overlaps on supported cases or explicit rejection of incompatible frozen boundaries. Do not silently move original UVs. Separate normals experiment afterward. No product integration, no A action, PR #114 remains Draft.
