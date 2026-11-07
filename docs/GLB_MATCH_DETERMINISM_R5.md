# GLB R5 — Deterministic anonymous boundary candidates (Team B)

**Scope:** NEXT-008; developer-only verification (not public release approval).
**A-authorized origin:** `feature/v0.18-shape-diagnostics`, SHA
`af7a5f0436bce631cb7cddbd81b10d2d0c932619`, descending from
R4 merged dev SHA `a9a0a76a963ab4ae41b68126f419546b80871e2b`
(PR #43). R5 is an independently based **draft**; historical R1–R4 PRs
must not be re-merged or overwritten.

## R5 problem selection: deterministic boundary observations

The review-only spatial matcher observes boundary-edge counts and the
relative layout of coordinate-welded open edges. For compatible
nonzero counts it can report `boundary_spatial_layout_mismatch`,
`boundary_layout_budget_exceeded` (more than 256 edges in a part),
or `boundary_component_count_mismatch` (a graph contact changed).
These are conservative *review signals*, not proof of a geometric hole,
watertight solid, or part identity.

R4 measured 255/256-edge equal-contour candidate checks at roughly
286–506ms in its Blender Linux CI. A correct boundary algorithm must
remain deterministic for reordering triangle faces, flipping winding,
cyclically rotating triangle vertices, and small float32 perturbations.
A changed physical opening or contact graph must still mark the
association `ambiguous`; a 257-edge case must skip the quadratic
segment comparison. No confidence boost or automatic file edit is
permitted.

## CBDK-authored Python fixtures and gates

`tests/test_glb_match_determinism_r5.py` adds:

1. **255/256/257:** valid CBDK-authored 85 isolated triangles, 84
   isolated triangles+connected quad, or 84 triangles+pentagon fan.
   Reverse triangle order, flip some windings, rotate other triangle
   vertex orders; check exact boundary counts and repeat identical
   anonymous results. 255 and 256 remain `suggested`, while 257
   is `ambiguous` with only existing budget reason.
2. **256 float32 / tiny world translation:** round every vertex
   through IEEE float32 packing, reorder faces, and translate by
   0.0001 world units. Allow a review-only `suggested` heuristic;
   no equality/identity proof or hidden coordinate output.
3. **Micro opening vs material change:** shift the inner opening of
   an 8-triangle square frame by 0.00004 world units versus 0.24,
   after float32 rounding and face reordering. The former should
   remain an approximate candidate; the latter must be `ambiguous`
   with R2's existing spatial-layout reason. All repeated results
   must be byte-for-byte equivalent as Python dicts.
4. **R3 gap / contact, including reversed face order:** the 0.0002
   world-unit synthetic gap vs an exact point contact stays
   `ambiguous` due to changed boundary graph component count,
   even though its segment locations are within R2's relative
   sampling threshold. Check both directions.
5. **64 coincident anonymous parts / 512 triangles:** impossible to
   know part identity from matching coarse centers; keep all parts
   `ambiguous`, each with at most two review candidates, with the
   full unpaired inventory and deterministic ordering.
6. **64 separated, reversed parts / 512 triangles:** preserve
   corresponding anonymous candidate IDs, with an enforced
   `tracemalloc` Python heap peak below 32MiB, no auto apply, and
   repeated deterministic outcomes.
7. **Five warmed 256-edge samples:** log only the median elapsed ms
   (runner-dependent, **no brittle CI wall-time gate**); ensure the
   257-edge budget still fails closed. Test aggregate numbers are
   synthetic and reveal no private geometry.

Existing R4 tests still check 513-triangle and 65-part rejection,
R2 aperture/retessellation, and uniform-scale R3 near-contact.
Tests use CBDK-owned coordinates *only inside synthetic code*; no
user/private source, GLB, model name, paths or geometry/HTML are
serialized into diagnostic output. Timings/heap are aggregate
observations only.

## Production-code decision rule

**Verification first:** If all new negative/positive controls pass,
do not change `cbdk/glb_part_match.py`, reason codes, threshold or
review schema solely to make a performance number look better.
If a reproducible false suggestion, non-determinism or unsafe budget
case appears, introduce only the smallest B-owned correction, add
a failing-before/fixed-after test, then re-run the exact-HEAD CI.
An order-independent exact-contour fast path remains an *R6
candidate*, not an R5 acceptance condition. Even with a fast path,
R3 connectivity checks and fail-closed 256-edge limit must remain.

## Evidence boundaries

Run `python -m unittest discover -s tests -v` for Python 3.11,
3.12 and 3.13. Verify Windows 3.11/3.13, the existing GLB
export/import and smoke matrix in Blender 4.4.3/4.5.15/5.2.1,
Chromium and durable handoff on the **exact R5 head commit**. The
Python R5 fixtures do **not** themselves constitute an additional
Blender export/import fixture; the Blender CI validates the existing
R1–R4 real GLB regressions, while direct R5 float32 and permutation
cases are Python-only. Shared Blender smoke and common CI scripts
are A-owned, so do not edit them without a separately authorized
scope. Skill/Kit results are reported only if that R5 SHA triggers
those workflows.

No true semantic part identity, real-user GLB, physical hole proof,
user Windows GUI/Undo, commercial license, Blender Extension release
or formal v0.18 release is validated by this test suite.
Coordinator A alone handles STATE/HANDOFF/Notion/shared CI,
combined-branch merge and the next R6 queue/base.
