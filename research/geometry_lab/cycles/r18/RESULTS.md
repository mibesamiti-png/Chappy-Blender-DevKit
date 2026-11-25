# R18 — Blender Edit Mode integration and joined-surface UV audit

**Retrospective integration gate passed 24/24. Product adoption remains unapproved.**

R17's final documentation CI passed all four workflows. R18 consumes the same-run frozen R17 artifact and uses all 12 now-known artificial geometries with both R16 and R17 UVs. This is a retrospective real Blender 4.4.3 roundtrip, not a new holdout. Source collars are constructed from original input rings and independently authored source UV pins from R16. They are deliberately compatible rectangular charts. The bridge is inserted into a temporary Edit Mode BMesh, source face signatures are compared before/after reentry, and actual stored Mesh loop triangles, UV corners, face IDs, materials and seam flags are independently evaluated in Python. No user assets.

## Measured results

- 24/24 original collar face/XYZ/UV/material signatures preserved under cyclic loop-start equivalence; 24/24 scene restoration.
- Actual float32 bridge UV equals the incoming float32 representation exactly (max gap 0); source-to-bridge edge gap 0; maximum source pin difference 2.9764054998437928e-8 from authored double-precision coordinates.
- 24/24 correct seam flags: four contiguous internal bridge edges and two collar extensions. Flags equal UV discontinuities on the joined surface.
- All 24 joined meshes: zero positive-area UV overlap pairs at R14 1e-9 threshold, zero mixed winding, zero near-degenerate UV triangles, one inferred island. All 24 bridge-only audits pass too.
- All 24 joined CGAL tests: zero intersections; geometry checked through indexed bridge triangle correspondence and float32 XYZ matching.
- Full joined chart p95 anisotropy improves in 12/12 paired geometries, mean relative reduction 15.60%. Mean of individual percentage reductions, not pooled quantile.

| Case | Joined R16 p95 | Joined R17 p95 | Reduction | Max boundary face-normal angle (unchanged) |
|---|---:|---:|---:|---:|
| r16_circle | 7.107 | 6.358 | 10.54% | 19.59° |
| r16_ellipse | 8.938 | 7.465 | 16.48% | 46.19° |
| r16_sparse | 7.958 | 6.250 | 21.46% | 28.74° |
| r16_skew | 9.824 | 7.777 | 20.84% | 45.54° |
| r17_round | 7.596 | 6.394 | 15.83% | 18.78° |
| r17_oval | 9.118 | 7.496 | 17.79% | 43.35° |
| r17_lobed | 7.978 | 7.035 | 11.82% | 16.86° |
| r17_offset | 7.267 | 6.345 | 12.69% | 40.54° |
| r17_taper | 7.979 | 7.461 | 6.49% | 54.11° |
| r17_sparse | 7.972 | 6.288 | 21.12% | 26.02° |
| r17_wave | 8.234 | 7.509 | 8.81% | 21.77° |
| r17_skew | 10.345 | 7.934 | 23.31% | 52.16° |

Maximum measured boundary face-normal angle 54.11 degrees. This is geometry-derived, not evaluated shading. No actual checker image/render, repeat-tile overlap, arbitrary UV layout, multi-UV-layer or Undo/modifier preservation, artist-authored .blend or actual user models. The source collars extend V outside 0..1; raw UV plane overlap does not establish repeat-tile safety. No normal smoothing. The prototype runs a controlled temporary scene, not a registered operator. R14 finite-precision UV audit is reused; no exact 2D oracle.

## Evidence

First R18 job succeeded: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520052862/job/138889484289 . Frozen R17 same-run dependency succeeded. An unrelated legacy R12 job in the same run failed at the official Blender download (HTTP 403); do not label entire workflow successful. The R18 job itself downloaded checksum-verified Blender, completed roundtrip and independent evaluation. Artifacts include actual raw and evaluation JSON. Final documentation HEAD CI separately tracked. Protocol: RESEARCH.md. Reproduce using dedicated workflow. R1–R17 unchanged. No A action, no product integration, Draft PR #114 remains unmerged. R19 not auto-started; next study may investigate boundary normal continuity and/or checker rendering with explicit source preservation.
