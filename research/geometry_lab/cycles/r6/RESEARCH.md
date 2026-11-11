# R6 — Blender standard Edge Loop Bridge vs R5, preregistration

## Decision before running the new comparison

- **Problem:** R5 radial loft passes 4/5 new synthetic cases, but the R4 BMesh bridge baseline lacks the GUI operator's `number_cuts` and interpolation. The prior claim of a general advantage is not supported.
- **Existing limits:** Direct BMesh bridge has no cuts argument. R5 adds 3 internal rings with more vertices. It is restricted to parallel star-shaped planar loops. R5 is not edited in R6.
- **Comparator:** Blender 4.4.3 `bpy.ops.mesh.bridge_edge_loops`, candidates `cuts=0, interpolation=PATH` (no-cuts reference), `cuts=3, interpolation=LINEAR`, `cuts=3, interpolation=PATH`, `cuts=3, interpolation=SURFACE`. Same float32-rounded 2-loop input, same evaluation thresholds and CGAL oracle. Smoothness=1 and profile factor=0 for all.
- **Independent candidate:** frozen R5 `radial_loft(a,b,cuts=3)`, no implementation changes, measured inside Blender as Python generation. This is **not** a new algorithm and there is no parameter search.
- **Data split:** the 10 R4 and 5 R5 cases are *previously seen*, so only diagnostic/regression. Five new R6 fixtures are reserved fresh synthetic holdout. All were authored by the same researcher, not third-party blind models. Holdout parameters are frozen in `cycles/r6/fixtures.py` before first run.
- **Metrics:** original boundary vertex/edge preservation, Euler/topology/CGAL intersections, minimum triangle quality, analytic centroid-loft RMS/max, triangle and vertex counts, 3 warm runs of generator wall time per case (report native bpy operator overhead separately; never call directly equivalent API costs), Blender version/build, source SHA256, deterministic vertices/faces.
- **Pass gate:** same R4/R5 geometry gate (minimum triangle quality >=0.1, RMS<=0.08, max<=0.2, zero CGAL crossings, topology and original boundaries). For *advantage*: on fresh R6 5 cases, R5 must exceed **the best single Blender 3-cut method's** passed count by >=1 with no more serious topology/CGAL violations; if tied/behind, **no demonstrable basis** to replace Blender native. Assess per-method counts separately, do not select the best operator *per test case* as a predeclared single baseline.
- **Budget:** 20 total synthetic cases × 5 methods × 3 timed repeats + 1 warmup each, 1 Blender version 4.4.3. Blender generation job 12min max (including official executable download). Python CGAL evaluation 6min max. 20k triangles/60k vertices per output, individual generator at most 10s. Do not optimize after holdout.
- **Stop:** one full comparable run and independent oracle suffices. If official executable/network or CGAL cannot run, record infrastructure blocker and stop; do not claim an outcome. R6 is research-only and not an approval for CBDK integration.

## Reproducibility and isolation

Use the official Blender 4.4.3 Linux binary in a research-only GitHub Actions job; verify its publisher-provided SHA256 checksum before execution. Run `--background --factory-startup --disable-autoexec --python-exit-code 1`; manipulate only temporary research-generated objects. The test script restores/removes all temporary objects/meshes. Snapshot vertex arrays+triangulated faces and pass them to external Python3.12 + CGAL evaluation without bringing CGAL into Blender.

The Blender operator is part of `bpy.ops.mesh`, unlike `bmesh.ops.bridge_loops` used in R4: [Blender 4.5 operator API](https://docs.blender.org/api/4.5/bpy.ops.mesh.html#bpy.ops.mesh.bridge_edge_loops). Results must not be described as direct GUI mouse workflow timing. R5's output can have a different triangle count; include complexity to expose this.

No private mesh/images. No changes to ABCD, Development Intelligence Lab PR #115, main, STATE/HANDOFF or shared workflows. Only `research/geometry_lab/**` and dedicated `.github/workflows/geometry-lab.yml` are owned. Draft PR #114 stays Draft and `approved=false`. Next cycle not automatically launched.
