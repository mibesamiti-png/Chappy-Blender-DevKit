# R13A — form-first modeling research and evaluation reset

## Evidence and decision (2026-11-28)
R12K HEAD 7facbdefb92e3be897b78293118d334551322c15: CI 4/4, 95 unit tests, 10/10 integrated/separate roundtrips of 20 actual OBJ files, five native Blender 5.0.1 surface/Solidify/reopen passes. Source OBJ coordinate roundtrip max 7.86e-13; exact reconstruction of parsed OBJ. Shell detailed nonincident pairs 156152, zero detected contacts, grid controls 3/3, BVH 2/3 (coplanar miss). Shared-index pairs excluded. Native artifact 15247900444, run 46105287920.
User inspected the output and judged it still substantially inadequate. Visual acceptance failed; engineering gates remain valid but are not a proxy for shape quality. No specific visual failure location was supplied in that feedback; do not assume crotch taper is the only issue. Freeze R12J/K as a numeric baseline and end incremental taper tuning.

## External methods surveyed
- Blender Studio, Creating Clothing Basemeshes: https://studio.blender.org/training/stylized-character-workflow/5d7f7fc5db37a94301d88ff9/ . Base surface extraction/shrinkwrap before subsequent topology cleanup.
- Blender Studio, Clean Retopology: https://studio.blender.org/training/stylized-character-workflow/chapter/5d384edea5b8f5c2c32c8507/ . Dedicated garment retopology after form work; separates form and mesh layout.
- Blender 5.0 Shrinkwrap: https://docs.blender.org/manual/en/5.0/modeling/modifiers/deform/shrinkwrap.html . Nearest or projected surface attachment, offset options. Need constrained region selection near branching surfaces; nearest point alone can choose wrong side.
- Blender 4.5 mask extraction: https://docs.blender.org/manual/ja/4.5/sculpt_paint/sculpting/editing/mask.html . Extract region, optional additional boundary loop and smoothing; useful baseline, not automatically good topology.
- Blender 5.0 proportional editing: https://docs.blender.org/manual/en/5.0/editors/3dview/controls/proportional_editing.html . Broad falloff editing for intentional shape changes before dense topology.
- ETH IGL computational pattern making: https://igl.ethz.ch/projects/computational-patternmaking/ . 3D form precedes segmentation and 2D parameterization in their inverse pipeline; manufacturing goals differ from static character models.
- EASE (2026 preprint): https://arxiv.org/abs/2606.29419 . Body-surface representation with local ease control; investigate the geometric representation only, not physics/flattening. No reproduction or claim of comparative performance.
- ETH GarmentCodeData: https://igl.ethz.ch/projects/GarmentCodeData/ . Potential source of paired shape/design evidence; category suitability and license not checked, no assets downloaded or copied.

## Existing capability inventory
- R4 fitting.py: independent radial reference with analytical oracle, but single-valued torso cross sections; cannot handle branching thighs.
- R11 pelvis_field.py: synthetic branched field, linear extraction residual misses gate; bracketed extraction fixes vertex residual but misses normal-jump gate. Not a qualified body target. Do not treat field values as Euclidean distances.
- Applied07 V8: report of stylized mannequin geometry, closed topology and local normal metrics, anatomy unverified; actual assets not confirmed available on this branch.
- R12: independent outline, seams, split/reimport, quality and native validation usable downstream, not design objective.
- Existing depth-tested previews can support visual comparison. Need fixed scale, camera and reference alignment, no framing changes that hide poor shape.

## Hypotheses and bounded experiment order
1. Form-first extraction: choose a known, independently constructed neutral reference mesh; extract a design region, create offset, adjust broad shape. Compare raw extraction to boundary-smoothed/reprojected variant. First validate on non-garment branching sleeve/Y shell or other generic fitted cover, then garment. Reference must be qualified or clearly synthetic and not anatomy certified. No arbitrary body dataset generation to inflate progress.
2. Sparse control cage: manually specified sparse anchor curves (waist, two openings, front/back profiles) over the reference surface; Catmull-Clark and regional projection. Preserve landmarks; permit topology changes while developing form. Compare against R12 baseline at matched scale.
3. Retopology only after a visual choice: quad layout and panel labels on selected form, then independent geometric/native checks. Projection should use region labels/ray direction or constrained neighborhoods when near branches. Report projection misses and wrong-side control cases.
4. Pattern-first remains useful for separate panels/manufacturing but no cloth simulation, folds, sewing optimization or flat pattern solver in this pilot.

## Evaluation contract
- Distinguish intended target, surface fit, mesh quality, and visual acceptance. Never count topology pass as visual pass.
- Before generation, freeze reference geometry/target contours, normalized camera positions (front, back, sides, 3/4), scale and landmark positions. If no reference target exists, label shape error unmeasurable rather than selecting a self-generated target.
- Compare silhouette overlap and contour distances only against independent targets. Use per-view reporting, not an average that conceals a bad side; include localized curve deviations and signed/unsigned sampled surface distances separately. Calibrate metric on known displaced or distorted controls. A silhouette match alone cannot establish 3D correctness or aesthetic quality.
- Report actual previews and editable meshes for user preference review, with a fixed baseline alongside candidates and no tuning on evaluation holdout.
- Geometry safety checks remain mandatory; use native readback/Solidify where relevant and existing explicit collision limitations.
- Limit next pilot to two generation candidates plus baseline on one generic branching test reference; stop for visual/metric review before expanding to garment or tuning. No product integration or automatic R13B. This is a literature and repository review, not a new measured shape experiment.
