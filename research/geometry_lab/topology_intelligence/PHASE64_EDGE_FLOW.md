# Phase 64 — Semantic edge-flow planning and Y-loop grammar

Research only; approved=false. No private reference assets or measurements. Prior native run 45697528975 succeeded; independent validation 45697528982 failed. No product changes.

## Sources and design decisions
- https://igl.ethz.ch/projects/ddq/ — artist-derived patch patterns and user-specified flow; do not equate with autonomous character generation.
- https://la.disneyresearch.com/publication/sketch-based-generation-and-editing-of-quad-meshes/ — patch curves, subdivision compatibility, singularity control.
- https://igl.ethz.ch/projects/animation-aware-quadrangulation/ — pose-aware direction guidance.
- https://www.jstage.jst.go.jp/article/jamdsm/6/3/6_3_354/_article/-char/en — skeleton-driven structure and junction fields.

Separate semantic landmarks and loop paths, topological compatibility, surface fit, and deformation/quality validation. Curvature is a supporting signal rather than an anatomical design specification.

## Independent synthetic Y pattern (local experiment)
Split a trunk loop of n edges into paths a,b; a shared crotch path of c edges completes left/right roots L,R. Solve a+b=n, a+c=L, b+c=R. This particular grammar needs integral a,b,c >=2; a rejected boundary combination may admit other patch grammars.

Local results: three accepted loop combinations (16,12,12), (24,16,16), (24,14,18), each at three seam depths .12/.24/.36. 9/9 connected orientable quad-only open surfaces, Euler -1, exact intended three boundary loops, welded seam, valid vertex links and charge identity; 18/18 triangulated audits had zero nonincident contacts, degenerate triangles or incident flags. Three incompatible boundary combinations rejected (28,12,12), (24,15,16), (8,4,4). All nine layouts failed the existing 15-degree minimum triangle angle requirement (range 8.7339–10.9221 degrees).

Preview (24,16,16), depth .12: 195 vertices, 364 edges, 168 quads; interior valences 137 of degree 4 and two of degree 6. Minimum triangle angle 9.8153 degrees, max quad edge ratio 5.5383, dihedral P95 33.3519 degrees, max 115.8377 degrees; 1819 incident pairs per triangulation, all shared_only. Earlier Phase62 topology had four degree-3 and eight degree-5 interior poles. Different loop counts and geometry prohibit a matched geometric quality comparison. The new topology concentrates index at two branch endpoints; reducing pole count is not necessarily better.

For an orientable quad mesh with boundary, sum interior(4-valence)+sum boundary(3-valence)=4 Euler characteristic. For this open genus-zero three-boundary surface, the sum is -4; all regular boundary vertices contribute zero. Two degree-6 poles or four degree-5 poles can supply -4, among other possibilities.

## Next bounded test
Keep the direct split grammar as a structural baseline only. Compare a manually specified landmark/patch layout distributing branch index among degree-5 poles, using matched boundary loops and common guide surface. Judge edge paths relative to landmarks, face angles, dihedrals, editability and posed collisions; do not optimize the number of poles alone. Local synthetic scripts/results are not native Blender proof; no anatomy or reference-model topology has been copied. No production adoption.
