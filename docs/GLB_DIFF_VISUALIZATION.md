# GLB-020: 3D sampled-difference visualization (work in progress)

Last updated: 2026-11-07. **Unreleased / draft PR #25.** Initial feature is partial, with Blender 4.4.3/4.5.15/5.2.1 CI verified on synthetic GLB fixtures at code SHA `91e8b6a2`.

## Goal

Display *where* the two local GLB surfaces differ, not just report a global number. This initial headless implementation produces **two independent, color-coded GLBs** for opening in Blender or another GLB viewer; it is **not yet** an interactive, linked in-app comparison UI.

## Explicit local opt-in

Run from CBDK's repository root with a trusted Blender installation:

~~~sh
python -m cbdk glb-diff-visualize reference.glb generated.glb \
  --blender /path/to/trusted/blender \
  --output reports/latest/glb_diff_visualization
~~~

The output directory **must not exist**. This avoids overwriting previous results. It contains:

- `reference_diff.glb` — each reference triangle is colored by its sampled distance to the candidate.
- `candidate_diff.glb` — each candidate triangle is colored by its sampled distance to the reference.
- `review.json` — aggregate face counts per color, sampled maximum distances, thresholds, and limits. **It contains no source vertices, original input paths or user addon code.**

The two colored GLBs **do contain derived geometry by design** and must remain on the user's machine, not in the public repository/Notion/CI artifacts for private models. Inspect both views: a missing surface can be obvious in the reference direction even if the candidate direction is mostly grey.

## Color legend and metric

- **Grey (low)**: maximum of 24 sampled point-to-opposite-surface distances on the triangle is below 1% of the **combined world-space AABB diagonal**.
- **Yellow (medium)**: sampled error is at least 1% but below 5% of that diagonal.
- **Red (high)**: sampled error is at least 5% of that diagonal.

Thresholds and units appear in `review.json`. The deterministic triangle-sample/BVH implementation uses the same conservative geometry bounds as GLB-019. This **does not prove exact correspondence or an actual defect**: grey means no sizeable difference was *observed at the sampled locations*, and sampling may miss narrow openings and cavities. Scene alignment and identical units are prerequisites.

## Safety and limitations

- The input GLBs are static-preflight scanned; external URIs, invalid structures, large inputs (>24 MiB or excessive accessor references) are rejected. Each imported GLB has a strict 512-triangle cap.
- Blender starts from factory startup with Python auto-execution disabled. CBDK imports only its own fixed scripts. The original user addon is **never imported, executed, rewritten or approved**.
- No network upload and no changes to the input GLBs. Output is an explicitly requested new directory. Report is restricted to aggregate statistics; only local GLB overlays contain geometry.
- Blender importing untrusted 3D data cannot be guaranteed risk-free. Use only files you are willing to open locally in a patched Blender.
- The first iteration combines triangles into a single derived mesh in each output, so **original per-object identity, linked camera view, live side-by-side UI, unknown/unmeasured region highlighting, and large-mesh support remain TODO**.
- Failure or skipped large data is not treated as an all-clear or geometry match. The feature must not promote any parameters to automatic fixes.

## Verification gates

- Python unit tests: `tests/test_glb_diff_visualize.py` (same faces, winding, medium/high offsets, source order, rejects invalid input, launcher privacy/overwrite refusal).
- Blender 4.4.3 / 4.5.15 / 5.2.1 CI: **success** at code SHA `91e8b6a2` ([run 42264413844](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413844)). `.github/workflows/blender-smoke.yml` invokes `glb-diff-visualize` on CBDK-authored synthetic hole and equivalent-surface fixtures, checks JSON, reimports both colored GLBs and checks materials. Python ([run 42264413533](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413533)), Windows ([run 42264413685](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413685)), kit ([run 42264413982](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413982)) and handoff ([run 42264413923](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413923)) also succeeded for the same tested code SHA.
- Release decision: do **not** mark GLB-020 fully implemented until this proves robust and the remaining interaction/uncertainty aspects are addressed.

Related: [GLB-019 to GLB-022 roadmap](GLB_ROADMAP.md), [project state](project/STATE.json).
