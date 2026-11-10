# R12 preregistered synthetic UV-chart transfer and explicit seam audit

## Hypothesis (freeze before fresh holdout)

R11 left max 0.25 UV discrepancy at intentionally split source islands. BMesh UV is *per-face-corner*, not per geometric vertex. If adjacent source faces have different UV coordinates at the same vertex, a single continuous UV map cannot match both: a seam must be retained or moved into the new bridge. Following multi-chart seam ideas (libigl parametrization tutorial, https://libigl.github.io/libigl/tutorial/ ), evaluate a research-only deterministic chart propagation (not LSCM or a globally seamless unwrap).

## One candidate

- Create R10 bridge as R11. Preserve all original mesh coordinates, source-face UV and material values, and every existing face.
- Derive each boundary face's UV **translation** from its two real existing source BMesh UV corner values relative to R11's synthetic cylindrical base UV. Reject inconsistent endpoint translations and conflicting seed faces. No fixture-name, UV-mode, or known .25 offset used to select the bridge charts.
- Label each new bridge triangle by a deterministic multi-source BFS on triangle dual edges, with source-to-bridge edge-adjacent triangles pinned to the source translations. Add its assigned 2D chart translation to all of the triangle's BMesh UV loops. Adjacent differently labelled faces form **explicit internal UV seams**. Boundary source-to-new edge mismatch should approach 0 without altering old source corners.
- Continuous compatible source should generate 0 interior seams and match R11 baseline; split source may move UV seams inward, not erase them. No scale/rotate/affine island transfer, no seam optimality, no UV packing, no normal smoothing or user texture fidelity claims.
- Compare with frozen R11 baseline cylindrical UV assignment. Both arms use identical 3D strip+collars and bridge material=2. R12 only changes *new face-corner UV*.

## Frozen test

- 4 already-seen R11 shapes, 2 continuous and 2 split, are **development**.
- 8 completely new R12 author-designed nonplanar XY-star-shaped shapes, fixed before CI: 3 continuous, 3 alternating split, 1 grouped-block, 1 multichart UV offset. These are not private assets or third-party blind models.
- 12 shape/UV configurations × 2 methods = **24 Blender 4.4.3 Edit Mode complete meshes**. Each candidate and comparator also undergoes independent Python3.12 CGAL inspection of standalone strip and joined geometry.
- Gate on all 8 fresh conditions: candidate old-face XYZ/UV/material exactly unchanged, joined topology valid, new face material 2, Blender scene restored, per-source-edge boundary UV mismatch ≤1e-5, full joined CGAL pairs=0, and previous R10 standalone mesh geometry quality pass. Source geometry and all new triangle vertex indices/XYZ must be identical in both arms.
- The three new continuous conditions have 0 internal UV seams. The five split/block/multi conditions require >=1 internal UV seam and **seam count divided by internal strip edges <=0.60**. Record seam edge count, fraction, physical length, and max gap. This is not seamless UV and does not prove visual quality.
- The five split/block/multi baseline cases must have boundary UV discrepancy >=0.1. Both methods must have finite UVs (UVs outside 0..1 are valid), and every candidate new triangle's signed UV area must match the baseline within 1e-5 because per-triangle constant translation preserves local UV shape.
- If any gate fails, report not preferred, without post-holdout algorithm or fixtures retuning. No cherry picking or dropped oracle errors.

## Governance

Only research/geometry_lab/** and .github/workflows/geometry-lab.yml may change. PR #114 stays Draft, approved=false, no main/ABCD/Development Intelligence Lab PR #115/STATE/HANDOFF/private mesh changes. No automatic R13.
