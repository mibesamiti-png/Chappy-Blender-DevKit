# Team B R7 — adversarial GLB contour and fast-path safety

**Task:** NEXT-008. **Status:** team B draft, subject to exact-HEAD CI and
A's separate integration gate. Developed from `feature/v0.18-shape-diagnostics`
at `a857e1c2e4cc3e0d61b274cf7984625dcac5d40a`; this is downstream of
A's R6 integrated code `e2f09e593d9c7bdff66695c7e8972eea98e160ca`
(PR #56). Seven workflow families on that merged SHA were verified green
before R7 started. Old R1–R6 individual PRs are historical, not source bases.

## Reason and safety invariant

R6's in-memory exact, order-independent undirected boundary signature
bypasses the *quadratic* R2 nearest-segment scan only when the observed
contours have exactly the same normalized segments. R2's original scanner
**skips zero-squared-length opposing segments**, and R3 separately checks
the observed open-boundary graph's connected-component count. A contour
signature must therefore never skip R2 for line segments its scanner
would discard. This is not a proof of a hole or identical GLB part.

**Actually reproduced R7 regression:** A direct private-helper fixture
with one **zero-length open-boundary segment on both sides** is identical
under the R6 signature but has no valid opposing segment. On the initial
R7 test-only head `fff82a6d67e6b531d5f9da6244a3e91bc1f5522d`,
[Python CI run #42412713718](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42412713718)
reported `test_direct_zero_length_boundary_guard_equals_original_r2`
**FAILED**, because R6 returned `None` while forced old R2 returned
`boundary_spatial_layout_mismatch`. The other seven R7 test methods
were green in the inspected Python 3.11 job. This was an intentional
negative-first validation; **red is not completed evidence**.

**Minimal fix in `cbdk/glb_part_match.py`:** Before allowing the exact
shortcut, require every normalized segment on both sides to have the
same strictly positive squared length condition used by the original
R2 `within_any` scanner. If any segment is degenerate/underflows,
use the **unchanged original R2 fallback**. The existing 256-open-edge
per-part budget runs first, so this is a bounded O(E) check (up to
512 total segments for one pairing), not a new unbounded mesh pass.
The R3 component count, heuristic confidence, topology reason enums,
`auto_apply=false`, and `cross_file_part_identity_proven=false` are
unchanged.

**Reachability limit:** public `local_boundary_segments` already
ignores triangles collapsed after coordinate welding; the zero-length
case was reproduced at the *private boundary guard API*, not from an
actual imported GLB. Do not mislabel it as an exploitable user-file
vulnerability. The defensive precondition preserves backward
conservative semantics even if a future caller supplies degenerate
segments.

## Test matrix

`tests/test_glb_match_adversarial_r7.py` contains eight independently
authored bounded tests:

1. Five-triangle square fan with **five boundary edges** and different
   collinear bottom-edge subdivision positions (0.30 vs 0.70). Both
   have the same contour despite unequal exact signatures. R6 must
   use R2 fallback and remain `suggested`; the R3 component guard
   must execute. Distinct edge subdivision is not part identity.
2. Same face and edge counts, but shallow inward notch 0.03 on one
   contour: `ambiguous` with the preexisting
   `boundary_spatial_layout_mismatch`, tested in both directions.
3. Float32-packed coordinates and micro-notch 0.0001 with face/
   winding changes: deterministic `suggested`, not a certificate
   of physical equality.
4. Direct zero-length guard fixture must match forced R2 fallback
   as described above.
5. Geometrically nonzero 2e-8-width triangle that collapses under
   the scene-relative coordinate weld stays `ambiguous` with
   `weld_collapsed_triangles_observed`. Exactly degenerate
   triangles are rejected by input validation.
6. R3 gap versus exact point contact, both directions and
   float32 face reorder: `ambiguous` with
   `boundary_component_count_mismatch`, same as baseline.
7. A 64-part / 512-triangle scene containing **two spatially
   coincident motifs**: only these two must remain `ambiguous`
   and unpaired. Other separated motifs may retain review-only
   suggestions, never auto-apply.
8. 255/256 edge cases must evaluate the bounded canonical
   signature; 257 edges **must not** call it and must fail closed
   with `boundary_layout_budget_exceeded`. An authored 256-edge
   *nonexact* perturbation requires R2 full-scan fallback. Compare
   reports to patched R2 baseline, measure three paired matcher-only
   medians and peak `tracemalloc` heap under a 32 MiB cap.
   Timing is an observation, **not a brittle CI pass threshold**.

`tests/test_glb_regression.py` gains one R7 facade test proving
neither a collinear split nor a changed notch promotes the top-level
GLB regression result to file-identity approval. This is mocked IO
Python coverage, not a native Blender R7 fixture. It is a GLB-owned
file in the existing Blender workflow paths, allowing **existing**
Blender 4.4.3/4.5.15/5.2.1 regression and synthetic GLB export/
reimport smoke to run on this R7 HEAD without touching A-owned
workflows or shared smoke scripts.

## Exact-HEAD acceptance and remaining limits

Required: Python 3.11/3.12/3.13 full suite, Windows PowerShell
3.11/3.13, Blender 4.4.3/4.5.15/5.2.1 full jobs, Chromium and
durable Handoff successful at **the same final R7 commit**. Kit and
Skill count only if triggered on that commit. A's future combined
R7 SHA requires its own independent CI and release decision.

Measurements use synthetic inputs only. There are no private user
GLBs, source-derived coordinates, personal paths, external addon
execution or data export. Public diagnostic output must never include
raw vertices or canonical signatures. Real arbitrary GLBs, very large
or hostile nonmanifold meshes, end-to-end renderer performance,
Windows desktop UI/Undo, license clearance and official Blender
Extensions approval remain unverified.

R7 does not change `main`, public v0.17.0, A-owned shared
STATE/HANDOFF/PROGRESS, Notion, CI/smoke or other team source files.

**Proposed R8 for coordinator A, design only:** Explore the bounded
R2 nearest-segment fallback under equal-count but different vertex
subdivision, extremely shallow notches and repeated symmetric
motifs. Profile a few pathological but legal 256-edge synthetic
contours, without increasing the 512-face/64-part budget or
weakening `ambiguous`. If repeated real bottlenecks are proven,
assess a conservative bounded spatial index/pruning approach
against full old R2 outcome and R3 connectivity checks. Do not
create R8 work without A's new authorized base and queue.
