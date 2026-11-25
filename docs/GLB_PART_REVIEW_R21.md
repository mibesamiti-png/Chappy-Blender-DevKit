# R21 / F019-02 — bounded part-surface review candidate

Base 59270db35c68ebc94e4cfdb861cce21ee8edf3de, #125 revision 10.
Opt-in API: `run_glb_surface_review(..., profile="expanded_2048_parts")`.
Schema 3 wraps the unchanged R20 expanded whole-scene comparison and a separate
anonymous part review. Existing legacy and expanded schema 1/2 paths retain
their defaults; A owns the shared CLI hook. No viewer or GL research change.

- Reuse existing spatial AABB-midpoint/extent/count ranking, bidirectional
  margins and boundary guard. Never promote, rerank or prove part identity.
  Each reference row retains at most two candidates. Fixed world-space
  bidirectional 24 samples/triangle, relative to the larger local AABB
  diagonal; >max(1e-6, 0.002*local scale) demotes a spatial suggestion.
  This is a review threshold based on the existing boundary tolerance,
  not a calibrated physical error bound. Adaptive comparison is global
  R20 only; no part-local adaptive claim.
- Per scene: 2048 triangles/64 nonempty parts; ordered anonymous counts
  distinguished from size-ranked inventory. Original per-part boundary
  256-edge guard retained. New conservative reservation: 6*left_edges*right_edges
  per eligible best-pair boundary scan, cumulative 2M potential checks,
  not measured actual checks. Exhaustion remains ambiguous.
- Separate R20 global and R21 local budgets: each 131872 started samples,
  8M node pops, 4M precise triangle evaluations. Combined maximum
  263744 samples, 16M node pops, 8M precise evaluations, 130 BVH builds
  (2 global + up to 128 cached per side/part). Local pair attempts <=128,
  candidate ranking <=64*64 cheap scores, no full precise Cartesian product.
  Boundary reservation cap 2M, existing 24MiB/100000 vertex-reference
  preflight, 1MiB output cap and 180s default parent timeout retained.
  No user-configurable work ceilings. Budget exhaustion discards partial
  pair distances; completed unrelated pairs remain review-only.
- Synthetic controls: closed complementary tetrahedra same AABB/count/boundary
  but different surface (legacy suggestion vs new demotion), coincident
  competition, retessellation/order, known motion, missing/extra,
  split/merge, degenerate/empty/invalid layouts, 2049/65 caps, forced small
  query budgets, forged aggregate/ID/flags. Reuse old 256/257 native guard tests.
  Native smoke adds genuine 64-part/2048-face GLB parent roundtrip,
  reversed anonymous IDs, retessellation, warmup+3 timing, SHA invariant,
  cap and global budget skip. Actual results pending CI.
- No claim of arbitrary part identity, hidden cavities, native memory,
  general 2048/64 performance or speedup. Private data not used.
  Stop after exact-head 5CI and native measurements, or report blockers.
