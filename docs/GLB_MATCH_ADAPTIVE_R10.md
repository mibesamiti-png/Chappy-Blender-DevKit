# Team B R10 — adaptive, bounded R2 AABB-filter bypass

**Task:** GLB NEXT-008, coordinator A formally assigned R10 after R9 integration.
**Branch base:** `feature/v0.18-shape-diagnostics` at
`3675320fbc4a4879d73e649903f6fdb7c1f396dc`, verified to
descend from R9 integrated code `914f1c8ab8cf8dfe104f46054bfd4c84fc101e61`.
A's R9 integration PR #81 and R10 authorization PR #82 were merged;
the seven *independent* post-integration CI workflow families were
confirmed green before the new B branch was created. Do not
restack/remerge historical B R9 PR #78.

## Why

R8's conservative segment AABB prefilter helps sparse 256-edge
synthetic contours, but R9 demonstrated that 128-segment overlapping
boxes cause almost all candidates to survive the R8 filter:
49,280 probes, only 128 removed (0.26%). In a matched two-sample
synthetic Linux benchmark, always using R8 AABB instead of
the original unpruned R2 scanner was 1.33–1.56x slower across three
Python versions. These are **matcher-local** observations, not a
measurement of complete GLB import or all real meshes.

## Bounded R10 selection and safety proof

Inside `cbdk/glb_part_match.py`, only in the R2 **non-exact**
bidirectional nearest-segment fallback, sample the first
**64 segment-box checks**. If at least **8** of these reject a
segment, retain R8's conservative 2x-tolerance padded AABB
prefilter. Otherwise, for every remaining segment this
contour-pair scan, skip the AABB *prefilter* and run the
**original R2 closest-point squared-distance predicate**
without any other rejection.

This is an **adaptive work scheduling choice**, **not a
geometry classification heuristic**. A box can reject a
segment only when its expanded axis-aligned envelope cannot
contain any point within the R2 distance tolerance. Thus
choosing either branch preserves the exact truth of
`within_any`; the remaining R2 distance formula is
unchanged. Disabling the prefilter computes distances for
*more*, not fewer, segments, and cannot create a false
mismatch or suppress an actual mismatch. The decision does
not alter part scores, confidence, reason strings, output
schema, candidate order or `review_only`. It also does not
skip the R6 exact undirected contour equality check,
R7 positive-length guard, R3 independently observed graph
component count, or 256 boundary edges/part, 512 faces and
64 parts. It is limited to one bounded contour-pair
comparison; state never persists across files or candidates.

The first-64 sample may not predict the rest of a
complex mesh or adversarial ordering. In that case there
might be no benefit or an even slower scan, but **the
decision cannot weaken the conservative review result**.
No percentage/counter, coordinate, edge signature, private
source name or caller path is added to public reports.

## R10 negative and performance evidence

`tests/test_glb_match_adaptive_r10.py` exercises seven
self-authored synthetic methods, including:

1. Decision threshold values around 7/8 of the 64 sampled
   boxes, and necessary-condition checks for R2's safe
   expanded segment AABB.
2. Dense high-overlap 128-segment helper fixture from R9:
   AABB should stop after exactly 64 checks, while
   `boundary_spatial_layout_mismatch` must agree with
   both forced static-R8 and original unpruned R2.
3. Sparse 256-boundary-edge changed contour: the first
   sample should retain R8 pruning; full report dictionaries
   must match forced static R8 and forced unpruned R2.
4. Retriangulated equal outline, moved/resized opening,
   collinear subdivisions, real 0.03-depth notch and
   float32 0.0001 shallow notch: exact report-dict parity
   across all three variants.
5. R3 point-contact vs sub-tolerance gap in both directions,
   the R7 private-helper zero-length input, no false
   promotion beyond `ambiguous`.
6. 255/256/257 boundary budget, 64-part/512-face
   distinct/coincident motifs, 513-face and 65-part
   rejection, uniform scales .01/1/100; all outputs
   conservative and equal.
7. Paired **three warmed sample** medians on both R9 dense
   128 and R8 sparse 256 fixtures, Python-traced peak
   with 32 MiB cap, benchmark aggregate-only output.
   **No CI pass/fail assertions on wall time** due to
   runner variation; actually observed wins and regressions
   will be separately recorded for each Python version.

An existing GLB-owned regression facade test file now has
one R10 case verifying that suggested/ambiguous contour
candidates do not become file identity proof or automated
approval. The R10 fixture is Python with mocked IO, not
a new native Blender GLB export/import case. This file
is a known existing trigger for Blender smoke on the R10
PR exact SHA; shared scripts/workflows remain A-owned.

R9's historic dense workload test in
`tests/test_glb_match_stress_r9.py` was updated to **force
the original static R8 prefilter** during its 49,280-probe
selectivity and original performance benchmarks. This
retains the historical negative evidence instead of
silently changing R9's meaning after R10 activates
the adaptive bypass. These are not tests of private
real user models.

## Adoption and release gates

Keep the product selector only if **all parity and
conservative controls pass**, the dense 128 case gains
meaningfully over forced static R8 on three Python
versions, and sparse 256 does not exhibit an intolerable
repeatable regression. If this acceptance fails,
remove the selector code and retain regression evidence
with explicit results. Comparisons are runner-specific
not formal production SLAs.

For the exact final R10 SHA, run actual GitHub Actions:
Python3.11/3.12/3.13, Windows3.11/3.13,
Blender4.4.3/4.5.15/5.2.1, Chromium and Handoff.
Kit/Skill count only when triggered on that SHA;
A's future combined R10 code and post-squash SHA
need their **own separate CI**.

B changes only `cbdk/glb_*` and B-owned
GLB tests/docs. A owns shared STATE/Handoff/PROGRESS,
Notion, common CI and smoke, `main` and release.
No user/private GLBs, actual Windows GUI/Undo, huge
nonmanifold scene, native/process heap, true physical
hole/part identity, copyright/Blender Extensions
redistribution/license or official v0.18 release
is proven by these experiments.

**Possible R11, design only:** demonstrate whether
first-64 selection fails on adversarial ordering of
sparse-late or dense-late contours; check deterministic
review results and maximum slowdown before proposing
a bounded second sampling window or any production
switch. Coordinator A must explicitly authorize
R11's owner, latest integrated base, paths and
CI gate before starting new specialist work.
