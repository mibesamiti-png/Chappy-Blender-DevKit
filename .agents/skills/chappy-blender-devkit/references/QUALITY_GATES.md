# CBDK verification and release gates

Do not confuse tests, analysis, permission and release.

| Evidence layer | Verified fact | Never infer |
| --- | --- | --- |
| AST / static review | Parsed source, candidate dependencies, hashes | Runtime behavior, equivalent semantics |
| Python unit suite | Test cases passed in a specified Python version | Blender context and GUI |
| Trusted Blender CI | CBDK-authored fixture/recipe passed on a named Blender version and matching commit | Other versions, private addons, manual GUI |
| Chromium smoke / screenshot | Browser displayed and interacted with a synthetic local viewer | Blender GUI behavior or private model accuracy |
| Headless `Panel.draw` / Undo probe | Recorded Blender invocation under test conditions | Windows clicks, Ctrl+Z/Ctrl+Shift+Z or real-world crash recovery |
| Extension preflight | Legacy ZIP integrity and missing release requirements | Valid Extension ZIP or license/owner approval |
| Human approval | Explicit reviewed rights and adoption decision | Permission to auto-merge or release without separate authorization |

## Required checks for code changes

1. Inspect `AGENTS.md` and the live status. Check for a compatible
   helper in `parts/`, `catalog/` and the recipe/test matrix before adding
   code. Record affected requirements and an acceptance criterion.
2. Run focused negative and regression tests (invalid context, duplicate
   registration/IDs, ZIP traversal, skipped visual assertions, etc.) for
   the changed capability. Retain pre-existing behavior and error controls.
3. Run the relevant actual local/CI matrix. The baseline is Python 3.11,
   3.12, 3.13; Windows 3.11/3.13; Blender 4.4.3, 4.5.15, 5.2.1; kit;
   handoff; Chromium. **This can change**: read current workflow YAML
   instead of treating this list as a guaranteed run.
4. Capture test result and exact code SHA, real Actions URL, source/hash
   scope and failed/skipped/unverified rows. Distinguish green CI from
   actual feature or user-geometry testing.
5. Confirm no private `input_sources_private/`, real GLBs, derived HTML,
   auth tokens, machine paths or reports leak into public repository
   commits, public artifacts or Notion.
6. Preserve ``preview_only=true`` and `approved=false` where required.
   Pass `--preview-unapproved` only for an explicitly requested local
   CBDK-authored development preview, never as a release bypass.
7. Do not merge draft PRs, release, grant licensing, auto-install, or
   start future phases before current gates and separate approvals.

## Visual evidence accuracy

- Reference **real** screenshot or render artifacts from the exact
  synthetic fixture and code SHA. Label their origin and limits.
- Keep `screenshot_gallery` of Blender-produced PNGs distinct from
  `browser_screenshot_gallery` of real headless Chromium UI screenshots.
- A passed JavaScript/browser smoke proves only the tested interactions,
  not a full graphics or accessibility certification. Do not guess
  unseen image details from filenames.
- Make user-model screenshots **private/local only** without new explicit
  permission. Do not upload GLB-derived viewer HTML from private sources.

## End-of-task report

State: changed feature IDs and concrete results; commit/PR and merge
state; actual Python/Windows/Blender/browser successes and failures;
Notion sync attempted/succeeded/pending; unknown GUI/license/real-data
claims; remaining tasks, prioritized next action and next-phase gate.
