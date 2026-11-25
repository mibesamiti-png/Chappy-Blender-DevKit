# R17 — fixed-boundary conformal distortion refinement

**Scoped detached-strip research gate passed. Product adoption remains unapproved.**

R16's final documentation CI had an unrelated external HTTP 403 on the R6 Blender archive download; R16 itself succeeded. R17 freezes the R16 cut chart and optimizes only the free UV nodes using analytic gradients of logarithmic p-means of conformal energy q=(r+1/r)/2, p=2,6,12, bounded backtracking (180 iterations each). All original source and seam corners are fixed exactly. R16 fallback is included. Candidates must preserve seam edge identity, winding, nondegeneracy, one island, zero positive-area overlap (R14 threshold), and must not worsen either p95 or maximum singular-value ratio. No global optimum claim.

## Frozen independent evaluation

Development-only job 138886677374 in run 45519270283 passed 4/4 seen cases. First frozen full job 138887108775 in run 45519359594 passed 12/12 (4 seen, 8 fresh). Source hashes match between runs. No post-holdout tuning. All eight fresh cases improved p95 by >=5%, exceeding the preregistered minimum of four. Mean case-level p95 reduction 24.40%; mean case-level maximum ratio reduction 43.69%. These are arithmetic means of per-case relative reductions, not pooled face quantiles.

| Fresh case | R16 p95 | R17 p95 | Reduction | R16 max | R17 max | R16 density p95/p05 | R17 density p95/p05 |
|---|---:|---:|---:|---:|---:|---:|---:|
| r17_round | 8.047 | 6.435 | 20.03% | 12.728 | 7.592 | 1.219 | 1.273 |
| r17_oval | 9.964 | 7.070 | 29.05% | 13.410 | 7.190 | 1.586 | 1.507 |
| r17_lobed | 8.530 | 7.090 | 16.88% | 14.404 | 7.520 | 1.264 | 1.256 |
| r17_offset | 8.033 | 6.069 | 24.45% | 14.198 | 6.588 | 1.481 | 1.381 |
| r17_taper | 8.917 | 5.905 | 33.78% | 11.313 | 7.581 | 2.330 | 2.272 |
| r17_sparse | 8.614 | 6.227 | 27.72% | 13.556 | 6.949 | 1.522 | 1.318 |
| r17_wave | 8.949 | 7.602 | 15.05% | 16.042 | 8.230 | 1.316 | 1.294 |
| r17_skew | 11.128 | 7.986 | 28.23% | 13.820 | 9.539 | 1.691 | 1.435 |

All 12 candidate charts have zero UV overlaps at R14's 1e-9 area threshold, zero mixed winding, zero UV degeneracy, exact authored boundary pins (measured gap 0), exact seam corner UVs and seam edge set, one inferred UV island, unchanged XYZ/face arrays, detached CGAL zero intersections, and R10 geometry rubric passed. R14 analytical controls ran before evaluation. The average new-case refinement time was 166.1 ms on this CI host (includes candidate audits; not Blender end-to-end timing). Density spread worsens in 1/8 new cases; density is not a gate or objective. No visual texture test.

## Evidence and limitations

- [Development run](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45519270283/job/138886677374)
- [First frozen holdout](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45519359594/job/138887108775)
- Source hashes: cycles/r17/refine.py=5f43171718e3b079faf1789a3b9f5621566698b2883371fc12f959e1a236459a; cycles/r17/fixtures.py=a05c66a05b902dd710d55aaac7de805ffd231735f50288dbb64056fbe3d2b57e; cycles/r17/run.py=2c73a215cf5f30577fcd6fe33e2406eef966e583a3de56e62384cddfb998d709.
- CI artifact geometry-lab-r17-* includes baseline and candidate UV corners, geometry, metrics, selected optimizer and source hashes. Run from research/geometry_lab: python -m pip install -r requirements-oracle.txt shapely==2.1.2; python -m cycles.r17.run --output runs/local-r17.json.
- The independent geometry oracle is CGAL; UV acceptance uses finite-precision GEOS and measured thresholds, not exact predicates. Refine and evaluator share the R14 audit and seam helper; not an independent second implementation of every UV metric. The compared source boundaries are compatible rectangular charts authored from synthetic original loops, not arbitrary painted source UVs. Detached Python only, no Blender Edit Mode roundtrip, joined source geometry UV audit, explicit seam flag, actual texture, shader normals or real user model. No absolute texture quality guarantee. R18 proposed: Blender roundtrip and complete source+bridge UV audit with checker texture and source-preservation/negative controls. No auto-start.
- Only Geometry Lab-owned research and dedicated workflow changed. No R1–R16 code/fixture/result changes, main/ABCD/DIL/shared state unchanged, no private assets, no A action. PR #114 Draft, approved=false. Final documentation HEAD CI separately tracked.
