# Team B R6 — exact undirected contour fast path (NEXT-008)

**Implementation source:** fresh `feature/v0.18-shape-diagnostics` HEAD
`5ea9b687d74fe5d6713b9f235e0e27b881b30991` after A's R5
integration `a1c2f84715acce1f8cd33abaf003556708c13c07`
([PR #49](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/49)).
That integrated SHA's independent seven CI families were verified before
starting. R6's draft PR targets the development branch directly; old R5
draft branches are historic and must not be force-pushed or re-merged.

## What changed and why

R4/R5 measured a few hundred milliseconds for one 255/256-open-edge
pair because R2 compares endpoints and midpoints of every boundary edge
against every opposing segment. The existing R2 guard caps each part at
256 edges and fails closed for 257+; R3 independently counts the
observed boundary graph's connected components.

R6 adds `_exact_undirected_contour_signature` in
`cbdk/glb_part_match.py`. It forms an **exact collision-free canonical
tuple**, not a lossy hash, from the existing in-memory part-local,
scene-scale-normalized boundary segments. It sorts each segment's
endpoints (direction-free) and then sorts segments (order-free), while
preserving multiplicity. **No coordinates or signatures are serialized
to public diagnostic reports**, action logs, or any external service.
The signature is derived only after existing input validation and the
**per-part 256-edge budget check**; at most 256 bounded segments per part.

Identical canonical tuples imply every point sampled by the current R2
nearest-segment layout guard lies on an exactly matching opposing
segment; therefore the R2 result is known to be `None` without a
quadratic nearest-segment scan. This is a different implementation of
the same R2 invariant, **not an unconditional skip of the spatial
safety guard**. If the exact tuples differ, *regardless of how small
the difference is*, the old R2 bidirectional endpoint/midpoint distance
scan runs unchanged. That fallback avoids treating ordinary float32
rounding, scaling, translated positions, modified openings, or changed
edge segmentation as either automatically equal or definitely
different. The R3 boundary-graph connected-component guard in
`suggest_spatial_part_matches` still runs on the same branch after
this check.

Neither `METHOD`, `MAX_SCORE`, `MIN_MARGIN`,
`BOUNDARY_LAYOUT_RELATIVE_TOLERANCE`, the 256-edge ceiling, the
reason enums, anonymized candidate ordering, nor any report schema
or `auto_apply=false`/`cross_file_part_identity_proven=false`
contract changes. A matching signature is **not** proof of semantic
part identity, watertightness, physical holes, or future approval.

## Tests: actual fallback equivalence + resource evidence

`tests/test_glb_match_fastpath_r6.py` includes a baseline test helper
that patches *only* the new exact-signature routine to return a
different sentinel per call. This forces the original R2 quadratic
distance algorithm to run, without copying a second production
implementation. Regression tests compare the entire review dict
under the shortcut and forced fallback:

- 255/256 open edges with reversed face order, flipped winding and
  rotated vertex order (same outputs, shortcut actually invoked);
  257 edges fail closed before **any** signature computation.
- Direct signature tests verify order/direction invariance and that
  extra segments or changed coordinates are distinguishable, with no
  lossy fingerprint collisions.
- R3 component counter still called twice even on the *exact* fast
  path; point contact versus a 0.0002 gap is `ambiguous` in both
  directions, including reordered triangles.
- 8-triangle annulus cases for equivalent retessellation, moved
  opening, resized opening, very small offset, simulated GLB float32
  packing, small translation, and 0.01/1/100 uniform scene scales.
  Any changed exact key exercises unchanged R2 fallback.
- 64 synthetic 8-face rings (512 triangles), reversed anonymous
  part ordering; 513 faces and 65 parts are rejected.
- Warmed 256-edge synthetic matcher calls compare three paired
  elapsed-time samples on the exact same inputs, and measure
  `tracemalloc` peak for the optimized path; hard cap 32MiB.
  **No brittle CI wall-time assertion**. The published test log
  prints only aggregate medians, ratio, peak memory and count.
  Test timing is matcher-only, not whole Blender GLB import/export.

A GLB-owned non-authoritative facade test in
`tests/test_glb_regression.py` verifies equal/moved geometry through
the public review-only return contract, and activates the existing
Blender CI on this branch. **That additional Python test is mocked IO**;
real Blender validation is separately the repository's existing
R1–R5 synthetic GLB export/reimport and smoke suite for versions
4.4.3, 4.5.15 and 5.2.1. No shared smoke/CI files were changed,
and R6's precise 256-edge speed measurement itself runs in Python
CI, not inside Blender.

## Acceptance and limits

- Exactly identical observed contours can take the fast path without
  modifying R2/R3 **outcomes**, while all changed contours and budget
  exceedances retain the conservative original review-only outcomes.
- Verify *the exact R6 PR HEAD* on Python 3.11/3.12/3.13,
  Windows 3.11/3.13, Blender 4.4.3/4.5.15/5.2.1,
  Chromium and durable handoff. Skill/Kit success can be claimed only
  if those workflows really ran for this SHA; R5's integrated green
  results are not a substitute for R6-specific verification.
- A is responsible for combined integration HEAD CI and canonical
  STATE/HANDOFF/PROGRESS/Notion updates. No shared CI/smoke,
  private data, other team code, main, or formal release changes.
- Still unverified: arbitrary or private user GLBs, pathological
  nonmanifold meshes, giant scenes outside limits, actual Windows GUI
  interaction, correct physical topology/identity, licensing,
  approved Blender Extensions, and v0.18 formal release.

If observed improvement is insignificant or any safety regression
reproduces, do not ship a new heuristic: revert the shortcut and
retain scoped regression evidence. Exact contour equality is a
fast **non-negative observation**, never an identity certificate.
