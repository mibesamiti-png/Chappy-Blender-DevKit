# R7 — non-planar boundary loft, research preregistration

## Research decision (before testing holdout)

1. **Problem.** R5 Radial Loft in R6 passed 5/5 new planar cases versus the best Blender 3-cut option 3/5, but it rejects even mild non-planarity; for modeling, boundaries frequently slope and undulate.
2. **Existing limits.** R5 `radial_loft` requires constant Z on each loop. Blender `bridge_edge_loops` can bridge nonplanar loops, but source loops may be lost in extreme offset cases. No claim that native is universally worse.
3. **Comparator.** Official Blender 4.4.3 native `number_cuts=3, interpolation='LINEAR'` and `number_cuts=0, interpolation='PATH'` with the same float32 XYZ input. 3-cut is the primary comparator; no smoothing/profile hyperparameter sweep. Original R5 is only a rejection/reference contract, not forced to generate nonplanar input.
4. **Single hypothesis.** A *mildly nonplanar, Z-monotone* variant of R5: XY-radial alignment, retain the 3D endpoint Z values when sampling both polygon loops, 3 internal rings linearly interpolated in XYZ, original input boundary edges untouched. No tangent or normal fitting, no global remeshing, no AI inference. Invalid/multivalued XY rays rejected.
5. **Quality & data.** Freeze 4 development and 6 new holdout synthetic cases in `cycles/r7/fixtures.py`; no holdout-driven tuning. Each: 3 repeats + warmup. Strict original boundary vertices **and edges**; CGAL self-intersections=0; Euler=0, connected, nonmanifold=0, min triangular quality≥0.1. Independently measure analytic 3D loft error to a dense known parametric surface (reference uses equal parameter angles and need not match the XY-radial mapping of the candidate): RMS≤0.12 and max≤0.28. These RMS/maximum checks have inherent interpolation/reference bias and do not measure artist preference. Must satisfy *all* to pass.
6. **Pre-set advantage gate.** On 6 new holdout cases: proposed R7 ≥4/6 passed **and** ≥1 more passed than native 3-cut LINEAR, without any CGAL intersection or topology violations on its successfully generated output. If not, record rejection or limitation, do not optimize. A matched nonzero failure means not passing, not an oracle outage.
7. **Budget and stop.** 10 shapes × 3 methods × 3 repeats + warmup, up to 10 s/generation, one official Blender 4.4.3 environment + independent Python3.12 CGAL. One measured cycle; no model revisions after holdout. If environment/oracle cannot run, stop with blocker. A new R8 requires a distinct instruction.

## Implementation contract

- Each loop 3..48 finite XYZ vertices, simple boundary with star-shaped XY projection and angularly monotonic edge order; all of lower loop strictly below all of upper loop by positive Z separation. This is **not arbitrary tilted 3D topology** or a general geometric repair engine.
- The original boundary vertex coordinates and exact boundary edges must be present. Interior triangulation is a proposal `approved=False`; scene state is not touched outside temporary test objects.
- Oracle is CGAL `self_intersections` run outside Blender; use same mesh quality implementation as R6, with a new 3D parametric error metric that samples the authored analytic loft. This is a geometric comparison on synthetic meshes, not end-user validation.
- Verify Blender archive with published SHA256 as in R6. Existing R1–R6 files and results are immutable. Keep workflow owned under `.github/workflows/geometry-lab.yml`, not shared CI. PR #114 remains Draft and unmerged; PR #115/ABCD/main/STATE/HANDOFF untouched.
- Research rationale: Blender operator documentation includes planar/nonplanar bridge tools with native interpolation options: https://docs.blender.org/api/4.5/bpy.ops.mesh.html#bpy.ops.mesh.bridge_edge_loops . Reuse native before developing generic topology algorithms.

## Repro

In `research/geometry_lab`, after installing the same verified Blender 4.4.3 and `requirements-oracle.txt`:

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r7/blender_run.py -- --output runs/r7-raw.json
python -m cycles.r7.evaluate --input runs/r7-raw.json --output runs/r7-eval.json
```

No private models or images may be used; all meshes are generated from constants above.
