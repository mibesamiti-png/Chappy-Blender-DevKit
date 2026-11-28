# Applied02 simple — scoped closure (2026-11-25)

Owner direction: default to lightweight, recognizable, editable visual models; exact reference reconstruction, functional hinge, print/fit and manufacturing design are bespoke tasks only when explicitly requested. This is a research workflow decision, not an implemented CBDK quality-mode UI. Applied02B and Applied03 evidence preserved unchanged.

## Measured lightweight candidate

Source/workflow head b20e5f0f0639e8c3d20e1a5faffbad48d80d144a. [Native Blender and independent audit job 138945846437](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45536943027/job/138945846437) completed success. Official Blender 4.4.3 cache restored, pinned SHA verified. [Artifact 14987382648](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45536943027/artifacts/14987382648), retrieved 999256 bytes; ZIP CRC clean, eight expected files, three PNG renders inspected. No separate local Blender reopen.

- 257 base mesh vertices + 11 Bezier points = 268 editable controls, previous 292. 1292 evaluated mesh vertices counted from raw arrays (includes curve cap duplicates; not a welded or export vertex count).
- 2444 evaluated triangles vs 5656 in B, 56.79% reduction; 81.37% fewer than initial 13116 triangle direct-mesh design (not a controlled decimation comparison). Frozen candidate <=4524 passed.
- 11/11 per-object closed/oriented/nondegenerate/CGAL-self-intersection checks passed after audit-only weld for curves. 22/22 native rigid pose checks; max error 2.15931e-8 m. Unrelated objects fixed per pose. Exact native save/reopen arrays. Mirror/Solidify/Bevel retained. Three straight cross-section bounds per side unchanged within each temple, measured delta 0; 28 base vertices/26 quads per temple retained.
- Open-state nonexempt moving-related surface contacts 0/24 pairs. No certification of static-static, exempt interfaces, containment or continuous/folded clearance.
- Subjective render review: recognizable oval eyewear in front and three-quarter views, bridge and material transition retained, folded-right view shows independent temple rotation. Faceted rim, angular temple end, pale/opaque-looking lens remain visible limitations. Accept as scoped visual proxy, not photorealistic or a finished print/game asset. No independent artist/user visual approval, UV or optics test.

## Applied03 diagnostic closure (not adopted)

[Placement job](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45535373258/job/138940610640): 48 baseline contact poses of 84; rear6=16; depth stagger=15; vertical3/combined=6.
[Axis job](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45535662595/job/138941587435): baseline 48 reproduced, rear6 16, vertical3 6, vertical4/5 4 each, vertical6 5, tilt2/4/6/8 7/5/7/12, tilt-4/-8 5/12. No candidate demonstrated zero sampled contacts. These are rigid-motion diagnostics with unchanged fixed hinge interfaces, not real hinge designs. No further mechanical search for this visual task. No threshold rewriting or prior evidence deletion.

## Decision

Scoped visual candidate complete for research purposes; approved=false, no automatic CBDK adoption, no main/ABCD/DIL/shared state changes, no private assets published, no automatic next task. Stop eyewear optimization unless owner requests improvements. Retain prior version for detail comparison. Historical R19 failed research gate and unrelated CI results remain distinct. Documentation commit CI not yet verified; above evidence is for the frozen implementation head.
