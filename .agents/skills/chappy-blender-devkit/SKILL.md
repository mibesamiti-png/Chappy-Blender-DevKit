---
name: chappy-blender-devkit
description: Use for CBDK (Chappy Blender DevKit) Blender add-on development, Codex continuation, AST/GLB diagnosis, authored UI or Extension preflight changes, and evidence-based GitHub/Notion milestone delivery. Not for unrelated Blender modeling.
---

# CBDK development workflow

Use this skill for a **repeatable workflow**, not as permission to run private
source, merge, release, approve licensing, or assume CI passed. `AGENTS.md` and
the live repository state remain authoritative; this file deliberately does not
freeze a task count, a release, or test metrics.

## 1. Resume from the repository, not the chat

1. Identify the repository `mibesamiti-png/Chappy-Blender-DevKit`. Read
   `AGENTS.md`, `docs/project/STATE.json`, `docs/PROJECT_HANDOFF.md`,
   `docs/V018_COMPLETION_GATES.md`, `docs/DEVELOPMENT_PLAN.md` and
   relevant code/tests. Confirm the active branch and PR **before editing**;
   inspect both `main` and the development branch. Do not assume a past chat
   accurately reflects the present HEAD.
2. Check `pyproject.toml`, `docs/PROJECT_SPEC.md` and recent actual workflow
   runs for the commit being discussed. Distinguish formal release, draft PR,
   approved future plans, and active tasks. Do not activate a future phase
   merely because its roadmap was approved.
3. Choose the highest-value **existing** unfinished deliverables that can be
   safely automated. Group related work into one coherent change, keeping
   failure diagnosis and tests local first. Avoid repeated full matrices for
   trivial changes, but never omit required gates to save time.

## 2. Implement with reviewed CBDK parts

- Search `parts/`, `catalog/` and current tests before writing a new helper.
  For an authorized local private source, use AST-only `scan`,
  `python -m cbdk search`, and review-only extraction; never import/execute
  scanned addon code or commit `input_sources_private/`.
- For safe Blender API changes, preflight Object/Edit context, selection,
  active mesh, topology, side effects, rollback and native Undo boundaries.
- Build only CBDK-authored preview features through the explicit
  `--preview-unapproved` gate. Unknown operators, executable UI snippets,
  unreviewed parts or arbitrary ZIP modules are not automatically permitted.
- For `UI-001`, `BUILD-001`, `EXT-001`, `GLB-019` to `GLB-022` and
  `NEXT-008`/`NEXT-009`, inspect the **current** modules and acceptance gates.
  `extension-preflight` checks readiness but **does not** create an approved
  Blender Extension. A GLB visual match does not prove exact geometry,
  true part identity, or causal property registration.
- Consult [CLI runbook](references/WORKFLOW.md) for exact commands.

## 3. Verify evidence, including visuals when relevant

- Run focused Python regressions first, then
  `python -m unittest discover -s tests -v` when the change warrants it.
- For trusted authored part changes, review `catalog/authored_parts.json`,
  run `python -m cbdk verify-parts` against a trusted Blender if available,
  and use `evidence-status` to detect stale evidence. Neither proves approval.
- For Blender/Windows/browser changes, inspect `.github/workflows/blender-smoke.yml`
  and the actual GitHub Actions workflow results and version matrix
  *on the matching code commit*. The repository
  currently maintains Python, Windows, Blender, kit, handoff, and Chromium
  workflow families; do not assume all six ran merely because one passed.
- For GUI behavior, a headless Blender `Panel.draw` or Undo smoke is **not**
  a Windows mouse/keyboard test. Mark GUI verification pending unless tested.
- Use only CBDK-authored **synthetic** geometry for public screenshots.
  Label real Chromium screenshots separately from Blender render PNGs;
  do not fabricate captures or upload GLB-derived private HTML.
- Check [quality gates](references/QUALITY_GATES.md).

## 4. Commit, hand off, mirror

- Work on the current development branch, keep the PR draft unless the user
  explicitly authorizes a different workflow. Never merge `main`, publish,
  install from GitHub, adopt unreviewed source or grant license approval
  just because CI is green.
- Update `docs/project/STATE.json` with what was *actually verified*;
  regenerate `docs/PROJECT_HANDOFF.md` using
  `python scripts/project_handoff.py --write` and then `--check`.
  Update relevant specs, gates, `docs/PROGRESS.md` and known issues.
- Compare recorded CI links and code SHA with observed runs. Separate
  current proof from historical `last_verified` entries.
- Follow [milestone delivery and Notion sync](references/MILESTONE.md) at
  meaningful checkpoints; the Notion mirror is **not** permanently automatic.
  If unavailable, report sync as pending instead of successful.
- Report changed files, feature/task IDs, real test outcomes and run links,
  remaining blockers, current branch/PR status and what to do next. A pull request may remain draft after successful tests.

## Further references

- [CLI runbook](references/WORKFLOW.md): scan, build, GLB and review commands.
- [Quality gates](references/QUALITY_GATES.md): CI, Blender GUI, evidence and
  approval boundaries.
- [Milestone workflow](references/MILESTONE.md): batched implementation,
  GitHub handoff and optional Notion mirror.
- [Trigger examples](references/EXAMPLES.md): when to invoke this skill.

**Do not** change code only to inflate test counts, fake evidence, mark a
human-only requirement as done, or conceal blockers before phase transition.
