# R15 — Periodic U wrap diagnosis and strict boundary incompatibility

**Local diagnostic experiment complete. No repair accepted. Product approval false.**

R14 final HEAD 165d392c5a0c0245b57f659ad330182b234a2be7 passed all four workflows; all ten Geometry Lab jobs passed (run 45515855571). R14's historical audit detected overlaps and mixed UV winding. R15 isolates one cause on that same already-seen R12/R13 synthetic corpus. This is not a fresh holdout, nor a proof of general UV parameterization impossibility.

## Method and controls

- Read archived Blender 4.4.3 raw output, reconstruct boundary edge ordering from triangle traversal and verify the paired recorded bridge UV corners. Seven R11-baseline rows already mismatch the source by design; retain their free diagnostic but reject them before strict repair.
- Per triangle, enumerate integer U shifts {-1,0,1} within the one-period input contract. Keep one anchor (or all boundary-pinned corners) fixed. Choose smallest U span (at most 0.5 + 1e-5), then smallest absolute shift sum, then lexicographic shift. Preserve V exactly, and U modulo 1. No source geometry, source UV, or face indices are modified.
- Compare baseline, a free periodic-lift *counterfactual* without source boundary locks, and a strict boundary-locked diagnostic. Failed strict faces remain unchanged in scratch arrays for measuring remaining defects, never accepted as repaired output. No face gauge coherence, global chart optimization, tile-aware overlap, or texture-render validation is claimed.
- Audit with frozen R14 Shapely/GEOS overlap metrics, thresholds 1e-9 and sensitivity 1e-6 UV-area, and actual corner matching tolerance 1e-5. Measure seams and geometric lengths as secondary outcomes. Integer shifting individual corners does not guarantee unchanged texture interpolation within a triangle.
- Seven analytic controls passed: clean, one-period lift with compatible pins, conflicting wide pinned edge, no short arc, already-lifted pins, integer translation, planar orientation control. The last manually checks orientation after unwrap, not a global solver test. Thresholds are selected diagnostic settings, not preregistered production criteria.

## Local results (Python 3.13.5 / NumPy 2.3.5 / Shapely 2.1.2)

| Historical arm (12 each) | Total overlap pairs before -> free | Same island pairs before -> free | Same island pairs >1e-6 before -> free | Seam edges before -> free |
|---|---:|---:|---:|---:|
| R12 corpus / R11 baseline | 6413 -> 0 | 6413 -> 0 | 6355 -> 0 | 0 -> 84 |
| R12 chart transfer | 7576 -> 1624 | 2811 -> 71 | 2716 -> 0 | 684 -> 753 |
| R13 corpus / R12 nearest chart | 8164 -> 2077 | 1814 -> 50 | 1755 -> 0 | 949 -> 1016 |
| R13 seam optimized | 7646 -> 1216 | 4765 -> 72 | 4653 -> 0 | 569 -> 642 |
| All 48 outputs | 29799 -> 4917 | 15803 -> 193 | 15479 -> 0 | 2202 -> 2495 |

All 48 free diagnostics remove mixed winding within inferred islands and all 386 wide-U faces; all free local lifts succeed. No UV-degenerate faces before or after. However, all 48 violate exact original source boundary UV, and 36/48 retain positive-area overlaps at the 1e-9 threshold (cross-island and tiny within-island residuals). The R13 optimized arm retains 1121 total overlap pairs at 1e-6 despite zero same-island pairs at that threshold. Seam changes affect island classification, so within-island pair reduction alone is not evidence of globally improved appearance. R13 local anisotropy median case p95 changes only 8.8754 -> 8.7446. UV stretch remains.

## Strict rejection certificate

All 48 outputs have exactly two source-boundary edges with U-span >0.5 (96 total, range 0.9411764–0.9879367). Keeping the endpoints within the source tolerance forces their containing triangle to have U-span greater than 0.5: changing only its third corner cannot fix this. This is a conditional obstruction to the chosen short-span requirement, not to every possible UV mapping.

- 7/48 already violate the original source boundary match and are rejected as input mismatch.
- Remaining 41/48 satisfy the source boundary tolerance but have two unliftable pinned triangles apiece. Strict diagnostic keeps all boundary values within 5.96e-8; nevertheless all 41 are rejected.
- Strict accepted repairs: **0/48**. Free result is explicitly non-adoptable. We do not alter original UVs or silently relax exact matching.

## Interpretation and next direction

R11's angle seed modulo 1 is a major contributor to the observed folding on these favorable synthetic collars. Original source UVs were constructed from the same seed, so this result is also an indictment of the synthetic UV fixture design, not a statement that real Blender models generally contain this defect. R16 should use independently authored seam-aware boundary charts, retaining exact corners; include incompatible negative controls, and test a cut-chart globally coherent mapping on genuinely fresh synthetic geometry. Add a separate rendering/texture and normal experiment later. No automatic R16.

## Reproduction / provenance

Inputs (local archive SHA256):
- R12 5ad9d3688662c1c1183e30e90bfa6c0eb26ebfcc17738a4ba9696d6eeb7d210e
- R13 52068ec5a47ea13caa86fd5fc2a175e2375cc1cc2b5ef681e3c8570aba68597a
- Locally tested wrap_audit.py SHA256 4d00d01f18cfeb668b0dc03b5a353254f20f653d0299b7eeb939627e4813436b

From research/geometry_lab, install cycles/r14/requirements.txt, use the R12/R13 raw JSON files, and run python -m cycles.r15.wrap_audit --input RAW --output NEW_JSON. Dedicated CI reuses same-run raw artifacts. CI reproduction is separately tracked. The script is diagnostic only; no private assets, no new Blender generation locally, no new holdout, no product adoption. R1–R14 code/results frozen. PR #114 stays Draft; main, ABCD, DIL and shared state unchanged. A need not act.
