# R12 — Boundary-pinned UV charts with explicit interior seams
Date: 2026-11-11 JST. **Scoped synthetic research gate PASSED; product adoption NOT approved.**

## Experiment and interpretation
- R11 preserved source UVs but deliberately left 0.20–0.25 UV mismatch at original boundary edges of split UV islands. On a shared 3D vertex, incompatible source face-corner UVs cannot be globally continuous without an explicit seam/transition.
- One research-only R12 candidate reads *actual* Blender Edit Mode source loop UVs for both endpoints of each boundary edge and subtracts R11 cylindrical base UV. It accepts ONLY constant UV translation per source face-edge (no scale/rotation/shear). It pins that source translation to the adjacent bridge triangle and assigns labels to other triangles with deterministic multi-source BFS along the face-dual graph. Each triangle gets a uniform UV offset. When different labels meet, an **explicit interior UV seam** is generated.
- This does NOT remove UV discontinuities, optimize seam placement, guarantee non-overlap, pack texture islands, preserve painted textures, or repair normals. Original source UV/3D/material/face arrays remain untouched. The original R10 geometry and R11 baseline UV projector were frozen.
- 4 **seen R11 development** shape/UV conditions, then 8 **new author-generated synthetic holdouts** (3 continuous, 3 alternating, 1 block, 1 multi chart). 2 arms each: R12 new UV charts vs R11 fixed baseline. **24 Blender 4.4.3 complete Edit Mode meshes**, standalone strips and complete joined meshes independently checked via Python3.12+CGAL. No user/private models.
- Before first holdout, a development-only Blender smoke revealed stale BMesh index lookup; source-face handles were then stabilized. The independent evaluator was also made fail CI if generation or acceptance gate fails. Development-only 4/4 succeeded before fresh full run, and there was **no algorithm/fixture retuning after the first fresh holdout**.

## Actual new-holdout measurements
| Case | UV source | Baseline edge gap | R12 boundary edge gap | R12 internal UV seam edges | Internal seam share |
|---|---|---:|---:|---:|---:|
| r12_cont_circle | Continuous | 0 | 0.0000000123 | 0 / 246 | 0% |
| r12_cont_lobed | Continuous | 0 | 0.0000000075 | 0 / 275 | 0% |
| r12_cont_ellipse | Continuous | 0 | 0.0000000075 | 0 / 253 | 0% |
| r12_alt_circle | Alternating | 0.25000006 | 0.0000000059 | 116 / 290 | 40.0% |
| r12_alt_ellipse | Alternating | 0.25000006 | 0.0000000298 | 84 / 260 | 32.3% |
| r12_alt_lobed | Alternating | 0.25000006 | 0.0000000596 | 118 / 330 | 35.8% |
| r12_block_lobed | Blocks | 0.20000005 | 0.0000000149 | 37 / 282 | 13.1% |
| r12_multi_circle | Multi-chart | 0.25000006 | 0.0000000298 | 126 / 304 | 41.4% |

R12 candidate **8/8 new cases** met the preregistered boundary matching, preservation, seam-budget, and independent CGAL gate; seen development **4/4**. The R11 baseline also correctly met its own *comparator protocol*, including revealing a mismatch on all 5 new noncontinuous cases. That does **not** mean R11 achieved boundary UV continuity in those five cases.

### Full independent evidence
- 24/24 standalone strips and 24/24 assembled meshes were checked. **0 CGAL self-intersections** in both scopes, 0 oracle-unavailable. All 12 candidate R10 strips met the previous geometric quality rubric.
- Every source face (XYZ coordinates, original per-corner UV and material assignment) preserved in both arms; no Blender scene/object/material leak. Every bridge material index remains 2, joined geometry exactly equal in both arms.
- Independent evaluator recalculated boundary gap using recorded real source/new UV corner pairs, all actual internal UV seams from per-face-corner coordinates, and signed triangle UV area. New faces underwent only per-face UV translation: signed UV triangle area remained equal to the baseline (tolerance 1e-5).
- 3 continuous new cases: no seams. 5 separate-chart new cases: internal seams remain, 13.1–41.4% of interior edges. This is a **tradeoff**, not true seamless UV editing.

## Limitations and next research
- Maximum new-case seam count **126 internal edges** and max seam share **41.4%**. Nearest chart propagation is not minimal seams and not minimum visual distortion. These cuts will generally remain visible or complicate texture painting.
- Works only for uniform translational UV chart offsets and favorable synthetic collars constructed from R10 output itself. If original source charts have affine rotation/scaling/shear or inconsistent constraints, the implementation rejects them; no real assets, .blend file import, multiple UV layers, painted materials, shape keys, Undo, custom split normals, shading continuity, or arbitrary-orientation 3D contours were tested.
- R11 already showed adjacent face-normal mismatches up to ~56 degrees on new cases. R12 does not smooth them or improve 3D geometry.
- Research results do not establish production operation or artist-quality texture continuity; team A approval would still require independent real-world validation.

## Evidence and reproduction
- First full frozen benchmark: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42925218978 ; development-only CI: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42925018451 .
- GitHub Actions artifact geometry-lab-r12-* retains raw and evaluated JSON, source SHA256 and all 24 generated synthetic joined meshes for 14 days.
- Frozen source SHA256: uv_charts.py=75acfaaff8963cfe9a0ecdfb2ad16bc1f82363625dd5e4077fe07d24c3a17e6a ; r12/fixtures.py=1f9be7006701233d436a0aa69f3c2484909169beefc953448816326c85083c18 ; r12/blender_run.py=5b53c7670a6858051d3b45f339803b4de32dbf388c344163355e59edfb44d67d ; r12/evaluate.py=166ca2022e31d215ba1f1702c211fdb19a8bf00772ec5fadc6927dd7a8ff34a2 .
- Verified official Blender 4.4.3 archive SHA256=8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946; external CGAL 6.0.1.
- Reproduction from research/geometry_lab with verified Blender4.4.3:
    blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r12/blender_run.py -- --output runs/new-r12-raw.json
    python -m cycles.r12.evaluate --input runs/new-r12-raw.json --output runs/new-r12-eval.json
- Related technical references: https://libigl.github.io/libigl/tutorial/ (boundary constraints, UV charts and seams) and https://developer.blender.org/docs/features/objects/mesh/bmesh/ (UV per-face-corner loops).

**R12 complete with the scoped gate met, approved=false, Draft PR #114 unmerged.** No R1–R11 source/data, ABCD, DIL PR#115, main, shared STATE/Handoff or private models changed. Team A need not act now. No automatic R13. Future: separately preregister internal seam-layout optimization or real authorized mesh import / normal tests.
