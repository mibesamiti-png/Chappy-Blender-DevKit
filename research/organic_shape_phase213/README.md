# Phase 213 — Organic shape capabilities

Base: Phase212-L, efe0f9d356c97ee4c85cec1b13ec8925cde20660 (seven regression workflows passed). Keep the mechanical branch unchanged. R1–R6 are reusable capabilities, R7 is a static shorts garment fixture, R8 variation/holdout. No cloth dynamics, stretch, tension, fine wrinkles, or production/manufacturing claims.

## R1: boundary on a curved surface
Input: synthetic ellipsoid axes, 4–32 cyclic latitude control values, bounded outward normal offset. Output: periodic C2 chart curve and closed equal-arc sampled polyline, with base point and normal evidence. Controls are spline control points, not interpolated landmarks. Scope is a single longitude-monotone closed loop; branching, arbitrary meshes, and actual human geometry are not solved.

Frozen pilot: sphere, oval, asymmetric latitude band; 96 vertices each. Check implicit surface residual, normal offset, arc-spacing ratio <=1.1, sampled turning <=20 degrees and winding. Test local editing, seam and knot continuity, invalid inputs and negative measurement controls. No native Blender needed for this round. OBJ preview is a polyline only.

## Sequence
R2 bounded surface patch construction; R3 branching and smooth joining with three boundary loops; R4 fitting to synthetic body-like surfaces; R5 mesh topology and refinement; R6 edge band and thickness; R7 static garment; R8 independent variations. Freeze gates before experiments, stop after useful evidence, use native Blender for selected integration trials. No repeated mechanical CI on the new PR diff where path filters permit. Prior apparel implementation was not located by the initial commit/branch search; do not claim it was reused. Revisit earlier research if its location becomes available.
