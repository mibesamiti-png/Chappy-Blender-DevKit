# R9 — Conservative interior diagonal flips (frozen before new holdout)

## Research question / pre-commitment

R8's density taper helped 15/16 old synthetic shapes but `r8_slender_opposite` still fails with minimum triangle quality **0.078598** (<0.1), despite 0 CGAL self-intersections. A triangle-quality rescue that **does not move original boundary vertices, change boundary edges, add vertices, or increase triangle count** is worth investigating.

### Exactly one candidate

1. Generate frozen R8 `tapered_radial_loft`.
2. Collect only **internal** edges shared by exactly two oppositely oriented triangles. Never touch an input boundary edge.
3. Evaluate changing that diagonal to the other diagonal of its four-vertex quadrilateral. Only when: proposed edge not already used, old face normals compatible (dot cos >=.2), new triangles nondegenerate and oriented near old mean normal (cos>=.15), new two-face normals compatible (cos>=.2), and local minimum mean-ratio triangle quality increases by >.0001.
4. Process candidate flips in ascending old local quality and descending gain, no shared-face flips within a pass. Restrict proposals to pairs whose old minimum quality <.30. Rebuild edge graph between passes; **maximum 3 passes**.
5. Preserve XYZ vertex array exactly, triangle count exactly, and all original boundary edges. This proposal is a local, non-global edge-flip heuristic. A candidate's local normal checks **do not prove no global intersections**: independent CGAL must evaluate ALL outputs. Reject research adoption on any candidate CGAL intersections, topological inconsistency, boundary changes or new holdout failure against gates.

### What was used to choose this hypothesis

Already-seen **R7 10 + R8 6 = 16 development fixtures** (not a new holdout). Offline NumPy/quality exploratory run on prior R8 raw artifacts showed 15 R8 previously passing fixtures keep geometric-quality pass; old reverse slender `r8_slender_opposite` improves **q 0.078598 -> approx 0.12718** in 3 passes. This exploratory check did **not** run CGAL and is not a blinded result; the precise hypothesis is now frozen.

### Fresh holdout / comparators

New, never-used synthetic R9 cases in `cycles/r9/fixtures.py`: **6**, authored by the same researcher and frozen before first CI. All 16 previous cases are `development`. Compare exactly: frozen R8 `tapered_r8` and fixed R9 `flipped_r9`, plus Blender 4.4.3 official 3-cut LINEAR as an independent native reference. Same float32-rounded XY-star-shaped, Z-separated nonplanar loop inputs, 3 timed repetitions +1 warmup per method. Blender scene must be restored. CGAL oracle runs in a separate Python3.12 environment.

### Pre-registered hard gate

- Prior failure `r8_slender_opposite` must **pass all** existing R7/R8 geometry criteria with R9 and reach minimum triangle quality >=0.1.
- All **15 prior R8 full passes** must remain full passes. Any resulting CGAL hit or boundary/topological violation on **any** R9 generated mesh fails the research gate.
- On fresh R9 6 holdout: R9 >= **4/6 full passes** and >= frozen R8 pass count; >= **2 of 6** with minimum triangle quality improvement **>=0.02** over frozen R8. No per-case tuned choice.
- Geometry rubric = exact original input vertex/edge boundary, connected topological annular strip, nonmanifold edges 0, Euler 0, CGAL intersections 0, min triangle quality >=.1, analytic 3D loft sampled RMS<=.12 and maximum error<=.28. This analytic target is researcher-authored, not visual artist validation.
- Fixed max 3 face-flip passes, 10s per generation budget and <=60000 vertices/20000 faces. One run on Blender 4.4.3, independent CGAL 6.0.1 and full new holdout; no holdout-driven retuning. If gate fails, explicitly mark unadopted. R10 not auto started.

### Boundaries and limitations

This is a local research-only heuristic, not guaranteed to improve global minimum quality, manifoldness, or artist shape. Existing R8's XY-star-shaped and globally separated Z boundary assumptions remain. No real/private meshes, UV, normals, materials, Blender edit mode integration, arbitrary plane orientation or third-party blind shapes. Report CGAL collisions honestly and do not skip errors. PR #114 Draft and `approved=false`; no modifications outside Geometry Lab-owned research files and dedicated CI.
