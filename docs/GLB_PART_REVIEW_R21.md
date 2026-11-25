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


## A integration candidate

B exact HEAD `96b3bf3c6037f8b567ea498a7fc8e9a2e95ae38b` independent review of specialist 5CI: Python45572009684, Windows45572009717, Blender45572009882, Chromium45572009721, Handoff45572009823. Actual native jobs139060683474/139060683053/139060683389: 2048/64 reverse-order candidates all64 suggested, complementary closed shapes old false suggestion 1->0, tie ambiguous, separate 65-part skip, 2049 and dense global skip, SHA unchanged. Parent warmup+3 median 5.581/9.171/6.205s. Global counts 131232/2230944/1049856, local 98304/491520/786432, 64 attempted of 128 max, 128 local BVHs, 98304 boundary reservation of 2M. Synthetic scoped evidence; no arbitrary identity, native memory, threshold calibration or native local exhaustion claim. The near-small/far-large contrast is not separately established, and motion/split/merge controls are Python only.

A exposes `python -m cbdk glb-surface-review ref.glb cand.glb --blender <trusted-executable> --profile expanded_2048_parts --output review.json`. Existing default and R20 profiles remain unchanged. Schema3 stdout separates global status and part_status/part_reason, counts unmeasured candidate observations; exit2 if the requested part review is skipped even when global measurements exist. Exit0 for a review-only report (including ambiguous/unmeasured candidates); never automatic identity approval. Native CLI checks real 64-part, closed-shape and 65-part fixtures, source SHA. Candidate CI pending; no merge/release, no GL adoption or viewer expansion.
