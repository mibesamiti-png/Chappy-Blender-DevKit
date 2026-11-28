# GLB boundary contour layout guard — Team B round 2

**Scope:** draft v0.18 / NEXT-007 and NEXT-008; CBDK-owned synthetic fixtures.
**Provisional base:** `work/v018-integration-bcd` at
`e445b12c9a66541ba13bfb10ee6bc0007078c24b`.
PR #29 remains independent/draft; merge decisions belong to coordinator A.

## Why the extra signal matters

The round-1 guard compares the *number* of coordinate-welded boundary and
nonmanifold edges. Moving the central opening of an eight-triangle square
frame can preserve its outer bounding box, centroid, triangle count, and **all
eight open boundary edges**. A centroid/extent/count-only matcher then has a
zero heuristic score despite altered inner-opening geometry.

## Implemented conservative guard

`cbdk.glb_part_match.suggest_spatial_part_matches` now temporarily
reconstructs each part's observed open-boundary *line segments* with the
existing `local_boundary_segments` helper.

For an otherwise comparable best-scoring candidate **with equal nonzero
observed boundary counts**, it:

1. Subtracts each part's own world-AABB center (whole-part translation
   alone is not treated as an altered contour).
2. Uses the larger of the two part-AABB diagonal lengths to scale the
   comparison, while retaining physical extent differences.
3. Checks each segment's two endpoints and midpoint against the nearest
   geometric *segment* of the opposite contour, **in both directions**.
   A nearest-vertex-only test would falsely flag some equivalent
   re-triangulations.
4. Marks `boundary_spatial_layout_mismatch` when a sampled distance exceeds
   **0.2% of that local scale**. For more than **256 boundary edges** in a
   compared part, returns `boundary_layout_budget_exceeded` and **demotes
   rather than asserting a clean match**. It does not perform an unbounded
   quadratic search.

Both codes extend the existing ordered `topology_review_reasons` list.
The original `topology_review_required` and `status` fields remain;
`suggested` becomes `ambiguous` if this guard observes a discrepancy or
hits the bounded scan budget. The prior numeric boundary/nonmanifold guards,
mutual-best and minimum-margin rules are not relaxed. The visual JSON
validator permits the new bounded reason categories while rejecting
contradictory booleans, unknown or repeated codes.

**Important:** A different location of observed open-boundary lines is not
proof that an actual physical hole moved. Coordinate welding, GLB import,
visible surface limits, coincident geometry, and nonmanifold meshes all
affect this signal. Equal layout observations are NOT topology/identity
proof, nor a proof of no internal cavity. Thin undetected features remain
possible. In particular, an additional boundary vertex that changes the
number of edge segments is still handled by round-1's conservative
count-mismatch rule, even if the outline is geometrically equivalent.

## Synthetic evidence and negative controls

The Python tests create square-frame surfaces (8 triangles / 8 boundary
edges) with a stable outer box; inner opening offset and width can vary
independently. Tests assert:

- Same shape, flipped face winding, flipped internal quad diagonals, and
  mirror of a truly symmetric opening: retain the heuristic `suggested`.
- Whole-part translation with reordered anonymous parts: retain
  plausible `suggested` candidates, without claiming identities.
- Equal counts but shifted opening and changed opening width: mark
  `ambiguous` with `boundary_spatial_layout_mismatch` despite a coarse
  normalized score of zero.
- 270-edge case: `boundary_layout_budget_exceeded` without an expensive
  full contour comparison.
- Invalid, contradictory or duplicated serialized reason codes: rejected.

`scripts/blender_surface_inventory_smoke.py` independently exports the
same five CBDK synthetic variants to GLB, reimports in actual Blender,
checks 8 triangles and 8 open edges after roundtrip, original GLB
SHA256 unchanged, and verifies both negative and positive matcher results.
It logs aggregate classification and elapsed milliseconds only; no private
geometry or original addon source is uploaded.

## Verification

```sh
python -m unittest discover -s tests -p 'test_glb_part_match.py' -v
python -m unittest discover -s tests -p 'test_glb_diff_visualize.py' -v
python -m unittest discover -s tests -v
```

The repository Blender CI calls `scripts/blender_surface_inventory_smoke.py`
on Blender 4.4.3, 4.5.15 and 5.2.1. Confirm **actual successful workflow
runs for the R2 PR commit** before describing them as passed; do not
reuse round-1 or base commit results. Windows GUI, private/user GLBs,
true semantic part correspondence, fine internal openings, and exhaustive
resource/performance guarantees are not verified.

Only GLB-owned modules/tests/synthetic smoke and this scoped documentation
may change in Team B. Shared STATE/HANDOFF/PROGRESS, CI, main, other teams'
code, Notion, release status and license approval are coordinator-owned.
