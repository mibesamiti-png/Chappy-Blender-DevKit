# Geometry Lab R13 — Interior UV seam layout optimization

Date: 2026-11-11 JST. **Preregistered limited synthetic research gate PASSED, candidate NOT production-approved.**

## Objective and design

R12 produced < 1e-5 UV edge mismatch between existing synthetic collars and new Blender bridge faces, but created internal seams on as many as 41.4% of internal triangle edges. R13 tests one bounded improvement in **internal seam count and 3D seam length**, keeping R12's source boundary UV pins, source faces and 3D triangulation untouched.

The research-only `cbdk_geometry.seam_opt.optimize_uv_charts` operates on the face adjacency graph:
- Two chart labels: exact constrained binary minimum cut (pure Python Dinic) using count, length and normalized hybrid seam costs.
- Three or more labels: deterministic bounded ICM local minimization (not global optimality).
- R12 baseline also enters the frozen set of candidates. Reject any result that increases either seam *count* or physical 3D seam *length*. Among non-worsening choices prefer minimum length, then count.
- Only the UV offsets of **new bridge face corners** change. The original source UV/material/XYZ, new face signed UV area, bridge vertex coordinates/triangle indices and materials are preserved. Deliberate UV seams remain; the algorithm **does not produce globally seamless UV**.

## Frozen test and provenance

- Four previously seen R11/R12 development cases and **eight new author-designed R13 holdouts**, registered before first holdout execution: three compatible continuous UV charts, three alternating split cases, one block and one multichart case. Prior exploration on seen R12 data is NOT new evidence.
- **12 geometry+UV cases × 2 arms = 24** actual Blender4.4.3 Edit Mode BMesh assembled meshes: R13 graph optimizer vs frozen R12 nearest-label baseline. Pre-holdout development smoke on the 4 seen cases passed before testing the new 8.
- Official Blender4.4.3 archive publisher checksum SHA256: `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`. Independent Python3.12+CGAL6.0.1 inspected each **standalone bridge strip AND entire collar+bridge mesh**, with **zero CGAL self-intersection pairs for all 24 cases in both scopes**.
- The independent evaluator recomputes UV seams and their physical length from actual saved per-face UV corners, rather than accepting the optimizer's internal scores. Original source UV corners and exact arm-to-arm XYZ/face geometry were compared; no dropped records, no source mutations, no oracle outages, no Blender scene state leak. No post-holdout retuning of the algorithm or the fixtures.

## New holdout results (independently verified)

| New R13 synthetic case | UV labels | R12 seams | R13 seams | R12 seam length (3D units) | R13 seam length | Count reduction | Length reduction |
|---|---|---:|---:|---:|---:|---:|---:|
| r13_cont_circle | Continuous | 0 | 0 | 0 | 0 | — | — |
| r13_cont_lobed | Continuous | 0 | 0 | 0 | 0 | — | — |
| r13_cont_ellipse | Continuous | 0 | 0 | 0 | 0 | — | — |
| r13_alt_circle | Alternating | 119 | **56** | 32.448 | **15.902** | **52.9%** | **51.0%** |
| r13_alt_ellipse | Alternating | 86 | **47** | 29.032 | **16.828** | **45.3%** | **42.0%** |
| r13_alt_lobed | Alternating | 131 | **62** | 37.804 | **18.547** | **52.7%** | **50.9%** |
| r13_block_lobed | Blocks | 45 | **34** | 13.719 | **9.501** | **24.4%** | **30.7%** |
| r13_multi_circle | Four UV charts | 125 | **110** | 35.050 | **30.241** | **12.0%** | **13.7%** |
| **Split source aggregate** | **5 cases** | **506** | **309** | **148.053** | **91.019** | **38.9%** | **38.5%** |

All eight new candidate cases passed the full preregistered research audit; both comparator arms passed geometry/UV-integrity oracles, but R12 had longer *intentional internal seams*. Both R12 and R13 preserved max source-to-bridge UV mismatch at ~`5.96e-8`, well below 1e-5, all 8 cases. Three continuous charts retained zero seams. **5/5 new noncontinuous cases** improved *both count and length* by at least 10%, exceeding the pre-registered >=4/5 requirement. No seam count/length regression on any of 12 cases.

### Seen development (not fresh evidence)
| Previously seen synthetic case | R12 seam count → R13 | R12 3D length → R13 |
|---|---:|---:|
| r11_split_circle | 95 → 43 | 27.635 → 13.080 |
| r11_split_lobed | 108 → 52 | 40.099 → 20.031 |
| r12_alt_circle | 116 → 52 | 32.575 → 15.479 |
| r12_multi_circle | 126 → 113 | 34.899 → 31.558 |

## Important interpretation and limitations

1. This is **topological seam edge-length optimization**, **not** a guarantee of improved textured appearance, fewer visible artifacts, better island packing or artist-chosen seam location. A shorter 3D seam may be visually more conspicuous. The UV charts and texture itself are not assessed, and original source faces are favorable synthetic collars derived from the generated strip.
2. For two labels, the fixed count/length objectives are exact min cuts of their *discrete graph objectives*. Multi-label ICM is only a local heuristic. The Pareto filter prevents the selected candidate from *regressing on those two measured metrics*, not other UV/geometry metrics.
3. R13 only supports R12's **per-edge constant UV translation** constraints; chart rotation, scale, shear, complex painted UV, multiple source material/UV layers, real imported .blend or scans, Undo, modifiers, normals/custom split normals, vertex groups and arbitrary 3D orientations are unverified.
4. Algorithm performance was **not a pass gate**. Recorded pure-Python optimizer time averages ~**13.1 ms** per new fixture on this CI host, not end-to-end Blender task time. No general speed claims.
5. Existing R10 geometry constraints (XY-star-shaped projected loops, strict Z separation and 3–48 input vertices per loop) still apply. R11 face-normal discontinuity and separate texture-painting problems remain unresolved.

## Reproducibility and governance

- First frozen holdout run: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42928487532 — R13 Blender+independent CGAL job **SUCCESS**. Prior development-only smoke: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42928283628 — SUCCESS.
- GitHub Actions artifact `geometry-lab-r13-*` contains `ci-r13-raw.json` (per-face UVs, both joined and strip meshes) and `ci-r13-eval.json` (independent per-case seam counts/lengths/CGAL and source SHA); standard CI retention 14 days. Synthetic data only.
- Verified source SHA256:
  - `cbdk_geometry/seam_opt.py`: `4d80dfd9b357f0d70bc55153f5618f665100edc0c0a493903c10f35383643404`
  - `cycles/r13/fixtures.py`: `1e71cf40cf3f3354a658c21ad086af4a100fa1b158648041980a601cb80fc96e`
  - `cycles/r13/blender_run.py`: `c5cd5496f30bd1e19f243df4c146aedfbd392c13a84c9fd3ec4cb11099eefc46`
  - `cycles/r13/evaluate.py`: `6feb9a0e3897c5d3a473bd974d168e26e8bcd91846f550bf0a82191ce7e41037`
- Reproduce from `research/geometry_lab` with checksum-verified official Blender4.4.3 and independent Python3.12/requirements-oracle.txt:
  ```bash
  blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r13/blender_run.py -- --output runs/loc-r13-raw.json
  python -m cycles.r13.evaluate --input runs/loc-r13-raw.json --output runs/loc-r13-eval.json
  ```
- Only Geometry Lab `research/geometry_lab/**` and dedicated `.github/workflows/geometry-lab.yml` touched. R1–R12 source/fixture/results left intact; CBDK A/ABCD, Development Intelligence Lab PR#115, main, STATE and HANDOFF untouched. **Draft PR#114 remains unmerged**, `approved=false`, no A action requested.
- **R13 complete, R14 not auto-started.** A separate future round could independently verify real imported meshes, UV texture distortion/stretch, normals and artist-perceived seam quality. R13 holdout is now seen and must not be reused as a blind R14 test.
