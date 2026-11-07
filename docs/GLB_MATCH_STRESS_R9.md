# Team B R9 — AABB non-benefit contour stress and parity evidence

**Task:** NEXT-008. New B-only branch from then-latest
`feature/v0.18-shape-diagnostics` HEAD
`e022bda7575997cbfbe1477fa8b71b84e1ccc6e2`.
Coordinator A merged R8 source B/C/D in PR #73 as development code
`ded947f85f46fb8cce0943314d6e1a9fb41717ef`, separately
verified **seven post-merge CI families green**, and merged the
R9 assignment PR #74. The newest dev head was checked to be a
descendant of that R8 integrated SHA. Do not restack/remerge old PRs.

## R9 question and conservative baseline

R6's exact order-independent boundary-segment tuple skips costly R2
distance checks only for exactly equal *observed* contours.
R7's zero-length guard prevents that fast path from accepting
segments the original R2 scanner ignores.
R8's bounded padded AABB broad-phase scans each candidate segment
and excludes a segment only if its box is more than **2× R2
tolerance** from the tested point on at least one axis. This
cannot discard a genuine nearest-segment match inside the
original Euclidean R2 tolerance; a potentially close segment still
uses the original closest-point calculation. R3's independent
boundary-graph component guard still decides observed contact
differences. None of these are physical holes or identity proofs.

R9 deliberately tests when the R8 box check is **not selective**:
many long diagonal segment bounding boxes cover the same 3D
point region, while the actual segment interiors are far from a
horizontal probe line. Broad-phase checks still run, but can
exclude very few candidates. A small 128×128 private-helper-only
synthetic test puts a compatible candidate near the *end* of the
candidate list, so the R2 fallback must inspect many
nonmatching but AABB-overlapping diagonals before finding it.
The opposite scan must report a spatial-layout mismatch for
the additional diagonals. This does not model one watertight
mesh and is not a physically meaningful real-user GLB; it
isolates the bounded matcher predicate's worst behavior.

## R9 authored tests

`tests/test_glb_match_stress_r9.py` contains seven methods:

1. Synthetic 3D segment boxes, reversed endpoints and degenerate
   zero-length segments. For many offset points at/inside the
   R2 Euclidean tolerance, prove the padded box does not reject
   a valid point; clearly outside points can be rejected.
2. Dense, overlapping AABB segments (128 per direction) measured
   with only aggregate candidate checks/rejection percentage.
   The new R8 prefilter must match a test-only forced-unpruned
   R2 scanner exactly, including `boundary_spatial_layout_mismatch`.
   No coordinates or paths printed in Actions.
3. 255/256/257 open-boundary edge cases preserve the exact
   R2/R3 review result; >256 returns the old
   `boundary_layout_budget_exceeded` and remains unpaired.
4. Float32-packed triangulated fan with the same outline but
   different collinear edge division, tiny shallow notches
   near tolerance, and a changed notch: R8 result equals
   the unpruned scanner's entire output dictionary and is
   deterministic across repeated calls.
5. Point contact versus a 0.0002 gap, each direction, and an
   almost welded triangle: R3's `boundary_component_count_mismatch`
   and conservative `weld_collapsed_triangles_observed`
   continue to prevent confident approval.
6. Anonymous 64-part/512-triangle arrangements, with and
   without a duplicated spatial motif; over-limit 513-face
   and 65-part inputs still fail closed.
7. Two paired warmed private-helper synthetic 128-segment
   unpruned/pruned medians with a 32 MiB `tracemalloc`
   Python-heap cap and complete reason equality. The
   timer is only for relative information—**no brittle
   wall-clock test failure condition**. This benchmark is
   matcher-local, not full GLB import or Blender rendering.

All inputs are independent CBDK-authored Python arrays, not
private user GLB assets. The test outputs contain only
synthetic aggregate timing, rejected-candidate percentage,
Python-traced peak and status, no raw geometry, source path,
user name, private report or hashed private contour key.

## Ownership and adoption decision

R9 is **negative-first**, so its intended first deliverable
is GLB-specific tests plus this document, **not a speculative
new precomputed AABB cache or spatial index**. If measurements
demonstrate a meaningful, repeatable performance improvement
and a mathematical no-false-prune safety argument for a
minimal B-owned production change, that can be proposed
separately after verifying all R2 parity, R3 topology,
256-edge/512-face/64-part budget and `review_only`.
If the workload yields little/no benefit, accurately record
that result and do **not** increase complexity.

All R9 edits remain in GLB-owned tests and documentation;
A alone owns common CI/Blender smoke, STATE/HANDOFF/PROGRESS,
Notion, other teams, main and formal release. Existing
Blender CI may not trigger from this new R9 test alone;
if that happens, **do not mark Blender R9 verification green**.
Instead report the gap and request that A wire a dedicated
GLB R9 smoke, or extend a specifically A-approved
GLB-only test trigger. Historical R8 Blender smoke remains
separate evidence and cannot substitute exact R9 SHA.

Required per final R9 HEAD: Python 3.11/3.12/3.13 full
suite, Windows PowerShell 3.11/3.13, Chromium, Handoff;
Blender 4.4.3/4.5.15/5.2.1 and Kit/Skill only marked
successful if those actual workflows run on the exact
head. A's later combined R9 SHA and post-squash seven
workflow CI are separate acceptance gates.

**Unverified**: real private GLBs, arbitrary pathological
nonmanifold geometry, full native heap, interactive Windows
GUI/Undo, structural hole/part identity, licensing, official
Blender Extension publication or v0.18 public release.

**Possible R10, design only:** investigate an alternative
bounded early-out/scanning order that demonstrably reduces
R2 near-tolerance clustered workloads *without* changing
R2's any-within-tolerance truth value. Preserve 256-edge
ceiling and anonymous candidate caution. Require A's
formal new base/queue before any R10 branch or code.
