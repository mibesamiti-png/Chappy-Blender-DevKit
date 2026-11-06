# GLB-020: 3D sampled-difference visualization (work in progress)

Last updated: 2026-11-07. **Unreleased / draft PR #25.** Initial feature is partial, with Blender 4.4.3/4.5.15/5.2.1 CI verified on synthetic GLB fixtures at code SHA `91e8b6a2`.

## Goal

Display *where* the two local GLB surfaces differ, not just report a global number. This headless implementation produces **two independent, color-coded GLBs with selectable anonymous mesh objects** for opening in Blender or another GLB viewer; it is **not yet** an interactive, linked in-app comparison UI.

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
- `review.json` — aggregate face counts per color **and per anonymous imported mesh part**, sampled maximum distances, thresholds, and limits. **It contains no source mesh names, vertices, original input paths or user addon code.**
- `compare_viewer.html` — **local-only, self-contained two-view 3D comparison**; both canvases share the same orbit, pan and zoom. Each side can filter anonymous parts independently and hide grey faces. The HTML deliberately embeds the derived mesh geometry (unlike the aggregate-only JSON), so never upload or send private versions.

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
- The latest iteration exports **a separate selectable object for each nonempty imported mesh**. Names such as `CBDK_Reference_Part_001` / `CBDK_Candidate_Part_001` are newly generated and anonymous; the original name is not copied. Each input is capped at **64 mesh objects**, 512 triangles, and its output contains the same number of nonempty parts.
- **Part numbers do not establish correspondence across two GLBs.** `part_001` on the reference and `part_001` on the candidate may be unrelated. No code path in GLB-020 infers a matched part or automatically approves a repair. A preliminary local HTML split viewer with synchronized 3D orbit/pan/zoom and independent part filters exists, **but real browser interaction testing, true cross-file part matching, unknown/unmeasured region highlighting, robust depth occlusion and large-mesh support remain TODO**.
- Failure or skipped large data is not treated as an all-clear or geometry match. The feature must not promote any parameters to automatic fixes.

## Verification gates

- Python unit tests: `tests/test_glb_diff_visualize.py` (same faces, winding, medium/high offsets, source order, rejects invalid input, launcher privacy/overwrite refusal).
- Blender 4.4.3 / 4.5.15 / 5.2.1 CI: **success** at code SHA `91e8b6a2` ([run 42264413844](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413844)). `.github/workflows/blender-smoke.yml` invokes `glb-diff-visualize` on CBDK-authored synthetic hole and equivalent-surface fixtures, checks JSON, reimports both colored GLBs and checks materials. Python ([run 42264413533](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413533)), Windows ([run 42264413685](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413685)), kit ([run 42264413982](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413982)) and handoff ([run 42264413923](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413923)) also succeeded for the same tested code SHA.
- Release decision: do **not** mark GLB-020 fully implemented until this proves robust and the remaining interaction/uncertainty aspects are addressed.

Related: [GLB-019 to GLB-022 roadmap](GLB_ROADMAP.md), [project state](project/STATE.json).

## Per-mesh review in Blender (development branch)

1. Import `reference_diff.glb` into a scene, inspect each `CBDK_Reference_Part_###` item in the Outliner, and hide unrelated parts to review a suspect area.
2. Import `candidate_diff.glb` into a separate scene (or collection if desired) and inspect its `CBDK_Candidate_Part_###` items. Both exports retain original world-space coordinates.
3. Read the respective `review.json` `parts.reference` and `parts.candidate` arrays for anonymous per-part color counts. Their ordering is deterministic within each imported GLB, but **not an established reference↔candidate identity mapping**.
4. Treat every grey triangle as **24 measured samples below the configured threshold**, not as a fully observed region. This version does not map unobserved areas into a separate color.

The report explicitly sets `cross_file_part_identity_proven=false` and `part_id_scheme=anonymous_sequential_by_imported_object_name`. It records no source object labels or raw geometry. The exported GLBs do contain geometry and should remain private. A multi-part synthetic test with intentionally private-looking source labels checks both GLBs and their imported material colors in the CI matrix. Code SHA `7365828b287e08046d66d62fc01c5fcfc2457fed`: [Python 42265921528](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921528), [Windows 42265921533](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921533), [Blender 4.4.3/4.5.15/5.2.1 42265921506](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921506), [kit 42265921516](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921516), [handoff 42265921493](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921493): **all five completed/success**. These test results apply to this SHA, not to later documentation-only commits.


## Offline side-by-side viewer (GLB-020 development preview)

After running the command above, open **`compare_viewer.html`** from the newly generated output directory in a modern desktop browser. It works as a standalone local file and does not fetch external scripts, libraries, assets or models. It has a Content-Security-Policy that disallows network connections.

- Drag either canvas to rotate **both** 3D model views together; Shift+drag moves the pair, mouse wheel zooms the pair, Reset restores the initial view. Keyboard arrow keys rotate the focused canvas; both remain synchronized.
- Use the separate **Part** dropdowns for each side; select the part independently. Hide grey faces to focus on the observed medium/high error.
- Both models use a shared coordinate center and world-space scale, avoiding automatic separate model normalization that would disguise positional differences.
- Each side is drawn with a bounded software triangle painter in Canvas 2D using a 3D camera projection, **not** a full WebGL depth buffer. Occlusion can be imperfect where triangles overlap; this is a review aid, not precision inspection.
- This initial viewer only uses previously validated triangles (512/GLB and 64 parts/GLB). The embedded coordinates are **private model geometry**; `review.json` remains aggregates-only. Keep all generated outputs local and exclude private viewer files from GitHub, Notion and CI upload artifacts.
- The HTML is static code from CBDK plus sanitized numeric-only shape data. It does not execute source addon Python or require network access.
- A successful Python test/Node syntax check/Blender file-generation CI **does not prove actual browser interaction works**. Browser GUI tests and additional compatibility review are still pending.

## Linked-view CI evidence (2026-11-07)

実装・テストSHA `b5d1d27f5e7834fa22faeefb02792091c1ac87d0`：Python [42268089086](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268089086)、Windows [42268088883](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088883)、Blender 4.4.3/4.5.15/5.2.1 [42268088779](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088779)、Windowsキット [42268088823](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088823)、引き継ぎ [42268088869](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088869) **全成功**。これはHTML生成とJS構文のCIであり、ブラウザ実機の操作試験ではない。

ブラウザGUIでの操作試験、WebGL相当の精度保証、別GLB間の部品対応や内部未測定部分の表示は未完了。HTMLの派生三角形は機密扱いし、`review.json`の集計データとの違いを維持する。

## Spatial part suggestions and real-browser smoke (GLB-020 phase 4)

The optional in-memory heuristic in \`cbdk/glb_part_match.py\` compares anonymized per-part world-space bounding-box **centers and dimensions**, with a small penalty for differing triangle counts. It checks mutual-best and minimum-margin requirements before displaying a single **suggested** candidate. A tie, several similarly plausible parts, or a weak spatial match becomes **ambiguous** or **unmatched**; none is automatically approved. It is not a reliable identity proof after large movements, reordering of geometry, rescaling, rotation, retessellation or complex edits.

The offline viewer now displays the reference part's tentative spatial candidate. The **候補を右側に表示** button only changes the candidate-side part filter after a user click; it never changes any mesh, addon parameter, or original file. For ambiguous or unmatched cases the button is disabled. Original object names, private paths and raw vertices remain excluded from the *JSON report*. The HTML still embeds local/private geometry.

The report and viewer include \`part_match_candidates\` and \`part_suggestions\` respectively, with explicit \`cross_file_part_identity_proven=false\` and \`auto_apply=false\`. Candidate scores are dimensionless heuristic observations, not geometrically conclusive.

A dedicated GitHub Actions browser smoke workflow (\`.github/workflows/glb-viewer-browser.yml\`) uses a real headless Chromium browser to test local synthetic HTML: both canvases repaint on a keyboard orbit and wheel zoom, reference part selection does not auto-link, the review-only candidate button works, hide-grey works, reset runs, and no runtime errors or HTTP requests are observed. The Ubuntu runner is pinned to 24.04 to avoid unsupported Ubuntu 26.04 in the older fixed Playwright dependency.

The browser test uses **only a CBDK-generated synthetic, permuted two-part fixture** and uploads no HTML artifact. Successful browser smoke will prove those tested interactions on that synthetic fixture only, not accuracy of arbitrary user model geometry, internal holes, or reliable part identity.

## Confirmed phase-4 CI evidence (2026-11-07)

コードSHA `72e9bd4e4ad2cb9b9716ee0cb5ea10de60cd779e` では、[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183982)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184368)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184086)・[Windowsキット](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184021)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183990)・[Chromium実ブラウザ操作](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183979)が**全6系統success**。

The headless Chromium smoke ran the same offline HTML viewer code with a synthetic permutation of two mesh parts and checked browser interactions. This verifies operation in that tested environment only. Both `suggested` and `ambiguous` are review-only heuristic states, and no shape identity or self-repair is proven. Browser support outside this test configuration and private large meshes require separate validation.

## GLB-020 phase 5 — supplemental sampling sensitivity (development preview)

CBDK now uses an additional **24 disjoint deterministic Halton points per triangle** after the existing 24-point surface-distance color classification. The primary red/yellow/grey colors **remain based on the initial 24 samples**. If the additional probes reveal a materially larger nearest-surface difference (at least **0.5% of the shared scene AABB diagonal**) or cross a displayed color threshold, the local viewer flags the triangle with a **purple outline**. The outline has an independent on/off checkbox.

This is an **observed sampling-sensitivity indicator**, not a map of all unseen regions. A triangle with no purple outline is **not** proved fully examined, and subtle holes, enclosed cavities, thin structures and semantic defects may remain undetected.

- `cbdk/glb_sampling_audit.py` performs bounded local BVH point-to-triangle checks (24 additional points per triangle, up to 512 input triangles per GLB).
- `review.json` stores **aggregate-only sensitivity counts**, per-anonymous-part counts and method/limit flags, never raw source vertices, original object labels or paths.
- `compare_viewer.html` carries the original local geometry and **per-face Boolean sensitivity flags** for the purple overlay; like the derived GLBs, this private HTML is **local only**.
- `unobserved_regions_verified=false` and `complete_surface_equivalence_proven=false` stay explicit. This first step does **not** localize every unsampled area or upgrade grey into a guarantee.
- Python unit tests cover identical surfaces, a synthesized missed-corner probe, malformed thresholds/geometry and per-part count validity. Headless Chromium tests toggle the outline in a synthetic fixture, and the Blender CI checks the new JSON method and count consistency. Record the test SHA and successful run IDs only after GitHub Actions completes.

## Phase-5 verified CI and remaining gaps (2026-11-07)

コードSHA `38057b1da49eeb61020664c4923ced2b2bad8406`： [Python 42279824321](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824321)、[Windows 42279824307](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824307)、[Blender 4.4.3/4.5.15/5.2.1 42279824378](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824378)、[Windows kit 42279824398](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824398)、[引き継ぎ 42279824427](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824427)、[Chromium GUI 42279824304](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824304) **全6系統success**。

The browser test uses CBDK-owned synthetic geometry and injects an explicit synthetic flag for *visual-toggle testing*; it does not claim that the test fixture independently demonstrated discovery of a previously missed hole. Python separately validates the numerical probing rules. A purple edge indicates only a new observed increase, not proof that the entire triangle or internal volume was inspected.
