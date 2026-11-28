# GLB part matching — boundary incidence review (Team B)

**Scope:** v0.18 draft, CBDK-owned synthetic geometry only. The anonymous
`cbdk/glb_part_match.py` heuristic remains a **review suggestion**, not
cross-file identity proof, automatic geometry repair or addon setting approval.

## Failure mode addressed

Before this change, the matching guard compared only whether *any*
boundary or nonmanifold edge existed. A candidate could remain `suggested`
when two meshes shared the same world-space AABB, face count, and coarse
centroid/extent score but had **different numbers of open edges**, or
different numbers of nonmanifold edges while both were already nonmanifold.

The matcher now compares the **numeric coordinate-welded edge-incidence
counts** of its tentative best pair. It demotes an otherwise strong
`suggested` pairing to `ambiguous` if the counters disagree. Existing
weak match and mutual-best/margin checks remain unchanged.

`topology_review_reasons` is an additive per-reference-part list with
at most these safe, aggregate-only diagnostic codes:

- `boundary_edge_count_mismatch` — different numbers of observed open edges
- `nonmanifold_edge_count_mismatch` — different observed 3+-incidence edges
- `weld_collapsed_triangles_observed` — one or both sides collapsed triangles during coordinate welding

The reasons apply **only to the tentative best-scoring candidate**, not
every candidate listed for manual review. `topology_review_required`
is true precisely when that list is nonempty. Existing JSON consumers
continue to use the original method name and conservative boolean;
the visual report validator accepts old reports without the optional
list and checks canonical reason codes when present.

## Synthetic regression coverage

`tests/test_glb_part_match.py` now exercises:

1. Same-bounds, two-face squares with 4 versus 6 observed boundary edges,
   both having `observed_boundary=true` and a score of zero: **ambiguous**.
2. Six-face surfaces with 2 versus 1 nonmanifold edges, both having
   `observed_nonmanifold_edge=true` and the same bounds: **ambiguous**.
3. Spatially close, topology-compatible triangles retain an empty reason
   list and remain *suggested* for review (never confirmed identity).

`tests/test_glb_diff_visualize.py` checks that unknown, duplicated,
boolean or flag-inconsistent reason data is rejected while the optional
field is absent from a legacy schema-v1 review.

Run focused tests via:
```sh
python -m unittest discover -s tests -p 'test_glb_part_match.py' -v
python -m unittest discover -s tests -p 'test_glb_diff_visualize.py' -v
```

## Evidence boundaries and handoff

These counts use approximate coordinate welding relative to **each
input scene's scale**. Matching counts do **not** prove equal topology,
the same hole position, closed internal cavities, correct part identity
or equivalence after retessellation. A mismatch can warrant review
rather than prove a defect, especially for different triangulations,
LOD or scene transforms. The surface sampler and BVH may still miss
small features. Do not infer that `suggested` implies an exact match.

Only the CBDK-authored synthetic tests are authorized here. Private
user GLBs, original addons, and derived geometry remain local.
Blender runtime/Windows GUI tests require separate evidence on the
matching commit. **The parallel-work coordinator** should record this
change in common STATE/HANDOFF after review; Team B has not edited them.
