# R16 — independently authored seam-aware UV boundaries and cut-disk harmonic solve

**Scoped detached-strip research gate passed. Product adoption NOT approved.**

R15 final CI: all four workflows succeeded at ba75bc6edb7a9b89760730b3c6f4b2eaeeab5bac (research run 45516632737). R15 showed the previous wrapped source boundary could obstruct the selected short-span UV repair. R16 instead authors source edge-corner UVs from the input rings before R10 creates the geometry. The existing loop direction is made CCW, an anchor at maximum X fixes the 0/1 seam, and normalized perimeter distances define U. Lower and upper source rings have V=0 and V=1 respectively. These are deliberately compatible rectangular UV boundaries, not arbitrary existing artwork.

The candidate chooses one shortest interior path between the source anchors, cuts the topology along that path in UV corner space, pins the source and seam corners and solves a uniform graph Laplacian on the interior. No XYZ coordinates or geometric face indices are changed. The comparator is the naive angular modulo U seed with identical independently authored boundary corners overwritten, **not R13's chart optimizer**. The earlier R12/R13 inputs were incompatible with the selected short-span repair and are not claimed repaired by this experiment.

## Frozen results (independent CGAL and R14 overlap auditor)

The predeclared 4 seen cases passed before enabling the eight new fixtures; the source and fixture definitions were unchanged between development and holdout. All 12 cases satisfy the gate (boundary error <=1e-8, no positive-area UV overlap at 1e-9, no mixed winding, no degenerate UV, one inferred island, seam-edge count equals chosen cut path, unchanged 3D arrays, zero detached-strip CGAL intersections). Previous R10 geometry rubric also passed for all 12. Four deliberately incompatible source inputs were correctly rejected on the first seen shape (missing edge, contradictory pin, wrapped/nonmonotonic boundary, nonfinite pin).

| New case | Comparator overlap pairs | Candidate overlap pairs | Comparator seams | Candidate seams | Comparator anisotropy p95 | Candidate anisotropy p95 |
|---|---:|---:|---:|---:|---:|---:|
| circle | 420 | 0 | 88 | 4 | 7.221 | 7.468 |
| ellipse | 461 | 0 | 68 | 4 | 9.877 | 9.267 |
| lobed | 550 | 0 | 102 | 4 | 8.872 | 9.180 |
| offset | 459 | 0 | 93 | 4 | 7.159 | 8.244 |
| taper | 426 | 0 | 63 | 4 | 9.042 | 8.167 |
| sparse | 335 | 0 | 64 | 4 | 5.803 | 8.044 |
| wave | 553 | 0 | 113 | 4 | 9.612 | 9.187 |
| skew | 506 | 0 | 75 | 4 | 10.782 | 11.242 |
| Total | 3710 | 0 | 666 | 32 | — | — |

Seen four cases: comparator overlap pairs 1910 -> 0, seams 373 -> 16. All 12 candidate boundary gaps measured zero in the detached solver. Every chosen cut contains four consecutive edges. Actual UV seam counts were independently recomputed from the emitted corner arrays (count equality, not an independent per-edge identity proof). The seam count is not a guarantee of shortest seam among all valid charts; the selected path minimizes 3D length on the restricted graph.

**Distortion remains:** case-level anisotropy p95 increased in 5/8 new cases. In the sparse case it rose from 5.803 to 8.044. Uniform positive-weight harmonic mapping is not a distortion minimizer. No claim of a visually natural painted texture or uniform texel density.

## Reproduction and limitations

- Development-only run: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45518546581, R16 job 138884220212 success.
- Frozen full run: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45518626774, R16 job 138884601745 success, R16_SUMMARY gate=true, 12/12 and four rejections.
- The CI artifact contains candidate UVs and vertices/faces, comparison metrics, and rejected input reasons. Run from research/geometry_lab with requirements-oracle.txt and shapely==2.1.2, then python -m cycles.r16.run --output runs/my-r16.json.
- This round is detached Python/NumPy and CGAL, not a new Blender Edit Mode test; no source object, assembled surface, custom normals, textures, tiles, multi-island artwork or actual user assets tested. Boundary pin preservation is measured within the candidate implementation, not independently round-tripped through Blender. R14 GEOS finite-precision UV threshold remains in effect.
- All prior source and results frozen. No A action requested. Draft #114, approved=false. R17 not started; next candidate is distortion-aware positive-weight/harmonic refinement with frozen boundary and seam, plus fail-closed overlap checks; later Blender integration and normal testing.
