# CBDK Team B R4 — GLB contour match resource and regression boundaries

**Task ID:** NEXT-008 (R4). **Type:** verification-first implementation of
new Python regression tests and real Blender-authored GLB fixtures.
**Development base:** `feature/v0.18-shape-diagnostics` at
`8c93a45dae6ad57b0b6e3197ef407df1c0eddce6`, descending from
A's merged R1–R3 integration `12ddcfeef935a805f7316ffb3698c141328aac88`
([PR #38](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/38)).
All previous specialist draft stacks are historical; no re-merge.

## Goal

Do not replace or inflate the R2/R3 conservative geometric evidence merely
to increase a unit-test count. Exercise tight boundaries of the existing:
- **256 open-boundary edges / part** nearest-segment scan limit.
- **512 total input triangles** and **64 anonymous parts**.
- R2 different openings and equivalent re-triangulation.
- R3 connected-component differences for a gap smaller than the R2 layout
  sampling tolerance, across three **uniform two-sided** scene scales.

No real user GLBs, private paths, addon source or coordinate dumps are used.
No additional reason code should be introduced if existing guards already
handle the cases.

## Reproducible CBDK-only synthetic matrix

| Input | Observed structure | Expected review-only result |
| --- | --- | --- |
| 85 isolated triangles | 85 faces, **255** open edges | unchanged `suggested` |
| 84 isolated triangles + 2 triangles forming a quad | 86 faces, **256** open edges | unchanged `suggested` |
| 84 isolated triangles + 3 triangles in a pentagon fan | 87 faces, **257** open edges | fail-closed `ambiguous`, `boundary_layout_budget_exceeded` |
| 64 distant 8-face annular meshes arranged in a 4×4×4 grid | **512 faces** in **64 parts** | reversing part order yields anonymous review suggestions with correct reordered candidate IDs |
| 513 input faces / 65 parts | invalid input limits | reject **before** attempting candidate matching |
| R3 disconnected vs exactly point-touching triangle pair | both 2 faces / 6 edges / same AABB | `ambiguous`, `boundary_component_count_mismatch` both directions |
| Same graph under face-order and winding changes | same geometry | no new topology review reason |
| R3 point-contact pair scaled on *both* sides by 0.001, 1, 1000 | same relative gap | retain ambiguous for changed graph and suggested for identical graph |
| R2 aperture moved vs same contour with alternate triangulation (scales 0.01, 1, 100) | 8 faces/8 open edges | moved opening ambiguous; same contour still suggested |

`tests/test_glb_match_budget_r4.py` checks all cases, including a generous
**32 MiB traced Python heap peak** for a 64-part / 512-triangle match.
Only aggregate elapsed seconds/bytes may be reported; do not publish the
geometry or source-derived names from real files. A hard wall-clock assertion
is avoided because runner performance varies; actual observed timings are
reported from Python/Blender CI instead.

`scripts/blender_surface_inventory_smoke.py` exports and re-imports four
fresh authored GLBs: 255/256/257-boundary one-part meshes plus one 64-part
512-triangle test. For each, verify SHA-256 unchanged, face/edge/part
counts and aggregate matching outcomes. Prior R2/R3 GLB fixture coverage
remains in the same smoke. A distinct 513-face GLB is unnecessary because
the built-in validator rejects the over-limit *face soup* in focused Python.

## Resource semantics

For two parts with 256 edges each, the existing nearest-segment tests sample
three points per segment in both directions; each scanned point visits up to
256 opposite segments. This yields a finite, per-comparison worst-case of
`2 * 3 * 256 * 256 = 393216` point-to-segment probes. However, total runtime
also depends on per-scene part counts, audits, welding, import and Python
allocation. The observed 257-edge case must skip the quadratic layout scan
before it starts and demote the candidate; 255/256 must not be incorrectly
flagged as over-limit. Do not assert that synthetic results are an arbitrary
large-file performance guarantee.

**Decision rule:** If these synthetic cases expose a false suggestion,
incorrect fail-open, unbounded resource allocation or actual R3 regression,
make the smallest B-owned matcher fix and rerun all CI. Otherwise preserve
the existing production matcher unchanged and deliver independently useful
boundary coverage plus measured evidence.

## What R4 does not prove

Anonymous spatial suggestions never establish physical hole location,
watertightness, semantic part identity, equal internal cavities, or license
approval. `auto_apply=false` and `cross_file_part_identity_proven=false`
remain unchanged. Blender GLB exporter/importer may reorder triangles and
use float32; exactly count/compare observed post-import geometry, and note
any version-specific changes honestly. Private/user GLBs, Windows GUI, and
arbitrary addon code execution are out of scope.

**Test command:** `python -m unittest discover -s tests -v`.
**Runtime:** actual Blender 4.4.3 / 4.5.15 / 5.2.1 CI at R4 final SHA.
A alone owns common STATE/HANDOFF/Notion/shared CI and integration into
the v0.18 development branch. No main merge or formal release.
