# 外部3Dモデリング資料の参考台帳（リンクのみ）

Status: **source catalog / researched; not incorporated or executed**
Checked: 2026-11-10 JST

This catalog links to public information. It is not permission to copy code, datasets, art assets, tool outputs or whole documentation pages into CBDK.

| Source | Technical lesson worth investigating | Source license/access | CBDK disposition |
| --- | --- | --- | --- |
| [Blender Python API](https://docs.blender.org/api/current/) | Mesh, BMesh, curves, modifiers, context and Object/Edit modes | Official reference; check actual page/license as needed | Authoritative API reference, version-specific verification required |
| [Blender Subdivision Surface](https://docs.blender.org/manual/en/4.5/modeling/modifiers/generate/subdivision_surface.html) | Low-resolution cage, Catmull-Clark, support loops, creases, non-applied modifier | Official Blender manual | Candidate RND-TOPO-001; not a guarantee of good topology |
| [Blender Solidify](https://docs.blender.org/manual/en/4.5/modeling/modifiers/generate/solidify.html) | Parametric garment thickness; scale and modifier-order caveats | Official Blender manual | Candidate RND-FAB-001 |
| [Blender Curve to Mesh](https://docs.blender.org/manual/en/4.5/modeling/geometry_nodes/curve/operations/curve_to_mesh.html) | Editable centerline with custom cross-section profile and caps | Official Blender manual | Candidate RND-STRAP-001 |
| [GarmentCode / PyGarment](https://github.com/maria-korosteleva/GarmentCode) | Parametric 2D panels, seam interfaces, garment components, procedural pattern design | MIT license reported by repository; verify individual dependencies/assets before use | Read design concepts first; **not** bundled, executed or a bra-specific library claim |
| [Blender Studio: Stylized Character Workflow](https://studio.blender.org/training/stylized-character-workflow/) | Retopology, garment basemeshes, topology strategy, outfit iteration | Some lessons paid; do not redistribute instructional media or project assets | Human modeling process reference, not executable software |
| [opensew-2](https://github.com/MarcelloMorettoni/opensew-2) | Flat pattern, quad panel topology, sewing and cloth modifier ordering | GPL-3.0-or-later as reported by its repository; third-party code | Study public design and test ideas only; do not copy or run in CBDK CI |
| [pytest-blender](https://github.com/mondeja/pytest-blender) | Headless Blender pytest execution | BSD-3-Clause; compatibility with CBDK's exact matrix unverified | Optional tooling investigation, not a dependency decision |

## Findings to test rather than assume

1. For a smooth editable garment surface, comparing **base mesh** with **evaluated modifier mesh** is essential; otherwise polygon counts conflate the two.
2. A modifier that looks correct in isolation may change visible geometry when its ordering changes; measure Subdivision/Solidify ordering rather than prescribing one universal stack.
3. Curve/Profile or quad-panel surfaces can be more editable than distorting primitives, but this is a hypothesis until synthetic A/B comparisons quantify edits, visual output and runtime.
4. Cloth/sewing simulation is a later optional pathway. It can require a fitting avatar or additional collision settings. The **first panel-and-strap pilot requires no avatar and no cloth solver**.
5. A general framework for clothes does not automatically cover specialized undergarment cup geometry. Any such extension needs explicit algorithm and validation.

## License and provenance rules

Source repository license ≠ every dependent package's or asset's license. GPL tooling is not automatically safe to integrate into a differently licensed repository. MIT/BSD code still requires license and attribution handling if actual code is adopted. Do not promote any source to "approved" from a URL, CI pass, AI response, similarity score or source hash.

Log date and exact version/commit if a future experiment depends on a specific revision. If a link is unavailable or documentation changes, record verification failure, do not silently substitute scraped copies.

## Current state

All sources here are **references only**. No compatibility or behavior has been measured on Blender 4.4.3 / 4.5.15 / 5.2.1 by this document; no new package is installed; no source code is vendored.