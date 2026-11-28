# Team B R8 — conservative AABB broad-phase for nonexact GLB contours

**Task:** NEXT-008, A-authorized R8 after integrated R7 `687b2acdc920253d69eda8c5e9c1c102d02aaef3`.
**Source:** then-latest `feature/v0.18-shape-diagnostics` commit
`ad785551b3b08b37ec036b3610dfb7e1d1b500cc`.
This is a new B-owned R8 branch targeting the development branch,
not a stack of old R1–R7 individual PRs. Seven independent integrated
R7 CI families passed before R8 was started.

## Why and what changes

The R6 exact undirected contour shortcut accelerates *strictly identical*
observed contours. Nonidentical segment lists still require the bounded
R2 bidirectional endpoint/midpoint nearest-segment scan; R7 measured
~300–613 ms on one authored 256-edge example. R3's observed boundary
connected-component guard and the R7 positive-length precondition stay
mandatory.

The new helper `_outside_expanded_boundary_segment_box` is a **cheap
broad-phase rejection only**, evaluated before the original R2
point-to-segment squared-distance predicate on each target segment.
For an axis-aligned segment box B and any point p within Euclidean
distance t of that segment, p's distance from each coordinate interval
of B cannot exceed t. Thus a point outside the box expanded by **2t**
along any axis *cannot* be within the existing R2 tolerance t.
The 2t padding is deliberately more conservative than the theoretical
t necessary, giving additional floating-point guard room. When the
AABB says "potentially close", the pre-existing R2 closest-distance
formula still runs *unchanged*. AABB never returns "same part",
replaces a topology reason, or changes the R2 acceptance threshold.
If the AABB fails to exclude an irrelevant segment, that costs
performance only, not correctness.

The helper sees already bounded part-local finite normalized
coordinates after the 512-face and per-part 256-edge limits.
A truly degenerate segment remains protected by R7's existing
positive-length exact-path precondition and by the R2 distance
scanner's own zero-length guard. The R3 boundary-graph check is
independent; `auto_apply=false`,
`cross_file_part_identity_proven=false` and review-only status
remain unchanged. Never emit input coordinates, segment boxes,
signatures or private GLB provenance to logs/reports.

## Synthetic evidence and negative controls

`tests/test_glb_match_pruning_r8.py` forces the original unpruned
R2 scanner by patching *only* the new AABB helper to return False.
It compares the **entire result dictionary** against the optimized
call for eight bounded methods:

- Exhaustive small deterministic examples of 3D axis-aligned,
  diagonal, reversed and zero-length segments with 135 nearby
  shifted points per segment: any genuine within-tolerance point
  must **not** be pruned. Far targets may be skipped.
- Same geometric contour with altered collinear subdivision,
  actual shallow notches, float32 quantization and very small
  notches, true moved openings and alternate internal
  triangulations. Unchanged underlying R2 classifications
  expected; the R3 component guard separately retains
  point-contact vs sub-tolerance gap ambiguity.
- 255/256/257 edges including a *nonexact* 256-edge workload;
  overbudget 257 edges must remain `ambiguous` and skip
  AABB and signature work entirely.
- 64 anonymous parts / 512 faces with both distinct and
  duplicated motifs; 513 triangles / 65 parts rejected before
  matching; uniform scale 0.01, 1 and 100.
- Synthetic 256-edge warmed **three paired samples** of
  forced-unpruned versus pruned matcher-only elapsed time,
  `tracemalloc` peak with hard 32 MiB cap, and complete
  dict-equality assertion. Timings are **observations**, not
  a brittle CI performance pass threshold or whole Blender
  GLB benchmark.

One GLB-owned mocked facade regression in
`tests/test_glb_regression.py` verifies that no shortcut
promotes an anonymous candidate to an approved file identity.
The file is in the existing Blender runtime workflow triggers;
the actual Blender 4.4.3/4.5.15/5.2.1 jobs validate existing
self-authored GLB export/import smoke. The new R8 AABB negative
fixtures are Python-only, **not native Blender fixtures**.
No A-owned shared CI/smoke edits are made.

## Accept or revert decision

Accept a product-level AABB helper only if **all old and new
classification tests pass** and a repeatable, useful speedup
appears in the synthetic nonexact 256-edge comparison. If not,
remove the product optimization and retain B-owned tests/design
with an explicit negative result, to avoid extra complexity
without reward. For every change, verify exact R8 HEAD
Python 3.11/3.12/3.13, Windows 3.11/3.13,
Blender 4.4.3/4.5.15/5.2.1, Chromium and Handoff.
Skill/Kit count only if they ran on this HEAD. Any subsequent
A combined/post-merge SHA requires separate CI.

R8 cannot prove actual physical holes, semantic cross-file
identity, arbitrary private user GLB accuracy, Windows GUI/Undo,
license clearance, formal Extensions approval, or public
v0.18 release. A alone updates canonical STATE/HANDOFF/
PROGRESS/Notion, shared CI, main and the R9 queue.
