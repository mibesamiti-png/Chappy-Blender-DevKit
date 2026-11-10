# Team B R3 — near-touching boundary connectivity guard

**Task:** NEXT-008 (rolling queue); review-only GLB candidate safety.
**Stack:** `work/v018-glb-analysis-r3` onto `work/v018-glb-analysis-r2`.
**Required ancestor:** R2 green commit `ef6163e58f6d1f7b124074557641caeb273c52f7`
(PR #31). This is not permission to merge the R2 stack or release v0.18.

## Concrete R2 false negative

CBDK's existing coordinate-welded edge audit counts open edges; the R2
boundary-layout guard measures nearest distances between open-boundary
*segments* with a part-diagonal relative threshold of 0.2%.

Two open triangles may be (1) truly separated by a narrow gap, or
(2) in exact point contact. Both observations have two faces, six
open edges, identical world AABBs, identical coarse matching scores,
and almost identical sampled segment locations. With the gap chosen
as 0.0002 units in a [-1,+1] synthetic fixture, the point positions
differ less than R2's layout threshold, but by much more than the
coordinate-welding tolerance (~2.8e-7 units). R2 returns `suggested`
for the pair despite a change from two to one observed boundary
graph connected components.

## Minimal R3 guard

`cbdk.glb_part_match` counts connected components in the *observed,
coordinate-welded open-boundary endpoint graph*, using bounded local
segments reconstructed by the existing R2 helper. No new model
coordinates, object names or source paths enter the aggregate report.
Only if a candidate has equal nonzero edge counts, and R2 has **not**
already emitted a spatial mismatch/budget reason, the connected-component
counts are compared. Any mismatch demotes an otherwise `suggested`
association to `ambiguous` with the additive reason
`boundary_component_count_mismatch`. No confidence score is increased,
and `cross_file_part_identity_proven` and `auto_apply` remain false.

The 256-open-edge-per-part budget from R2 still applies before the
graph scan; bounded graph traversal is O(V+E). Only the reason enum
and targeted GLB-owned code, tests, Blender synthetic smoke and this
document change. The `review.json` validator checks the new reason
in canonical order, rejects invalid/duplicated/conflicting reasons,
and keeps legacy optional-field compatibility.

**Limitations:** Observed boundary graph components are *not*
topological equivalence of solids or proof of actual holes, inside/
outside, geometry continuity, or true semantic part correspondence.
A close-but-real gap may be within R2 distance tolerance, so this
comparison is deliberately conservative. Genuine connected components
can split because of exporter quantization, degenerate geometry or
the approximate coordinate weld. Fine changes that do not alter
connectivity remain potentially undetected.

## Synthetic fixture and acceptance

Python tests inspect two-triangle surfaces with exact point contact
versus a near-but-not-touching corner, including reverse direction
and face order/winding changes. Boundary edge count remains 6,
normalised coarse score 0, R2 spatial check explicitly returns no
issue, but the new graph check marks only the real component mismatch.

The existing self-authored square-frame tests continue to cover
moved holes, resized holes, symmetric reflection, alternate
triangulation and whole-part translation. The Blender smoke exports
and re-imports four new self-authored GLBs through actual Blender,
checks six open edges and two triangles, unchanged input GLB SHA256,
and both negative and positive graph cases. Only aggregate test
observations and timing are logged.

## Verification gate

Run `python -m unittest discover -s tests -v` and actual repository
Blender matrix (4.4.3, 4.5.15, 5.2.1) at **this R3 PR's final SHA**.
Record all workflow conclusions and detailed measured outcomes in
the R3 PR body after they complete; do not reuse R2 #31 results.
Windows GUI, user/private GLBs, arbitrary addon execution and
large-model performance remain unverified. No common STATE/HANDOFF,
shared CI, Notion, main or formal release changes belong to Team B.
