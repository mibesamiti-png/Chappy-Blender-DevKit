# 3D制作ノウハウのCBDK取り込み手順（研究提案）

Status: **proposal / documentation only / not implemented**
Updated: 2026-11-10 JST
Owner for eventual integration: **A coordinator**, subject to active assignment.
Scope: generalizable modeling algorithms and synthetic test techniques only.

## Why

Use isolated Blender modeling experiments to discover reusable techniques, while keeping the actual private references and derived meshes out of this public repository. A successful local model is **not** evidence that a reusable CBDK feature exists. This document establishes a handoff protocol, not automatic adoption.

## Evidence pipeline

| Stage | Evidence needed | What is *not* proved |
| --- | --- | --- |
| DISCOVERED | Authoritative URL, source/author, retrieved date, license status, relevance | Functionality |
| DESIGNED | Minimal algorithm description, inputs/outputs, bounds, likely failure modes | Executability |
| LOCAL_PROTOTYPE | Private local Blender script and result on an explicitly permitted test file | Generality or safe publication |
| SYNTHETIC_VERIFIED | Clean-room, CBDK-authored synthetic geometry test, exact Blender version, input parameters, reproducible output and runtime | Real user project correctness |
| REVIEW_READY | Candidate stable ID, threat model, regression tests, source/provenance review, ownership and integration impact | Approval or redistribution rights |
| INTEGRATED | A-approved PR into active development branch, matching-SHA CI, catalog/recipes/tests/STATE/Handoff updates by authorized owners | Main release or universal Blender support |

Stages must be recorded independently; they are not a numeric score. A failure or missing evidence must never be promoted by inference.

## Mandatory record

Each experiment records: stable research ID; date; technique/category; cited source URL and retrieval date; source license and asset license separately; input/outputs; private-vs-public data classification; Blender version; baseline and revised algorithm; parameters; base cage face/vertex counts; evaluated mesh counts and Subdivision level; triangle/quad/n-gon distribution; shape/edge quality; viewport/render observations; performance with comparable hardware; reproduction command; exact tests/results; known failure case; confidence; next owner/action.

Use docs/research/EXPERIMENT_HANDOFF_TEMPLATE.md. If information is unavailable, mark **not measured / unknown**, not zero or pass.

## Candidate lanes

- RND-TOPO-001: low-density quad cage + non-applied Catmull-Clark Subdivision. Measure editability on a small, synthetic quad surface before a whole character.
- RND-FAB-001: parametric curved fabric panel with independently editable contour, support loops and non-destructive thickness. Compare modifier order.
- RND-STRAP-001: centerline and swept cross-section for a ribbon/strap; preserve controllable width, thickness, curvature.
- RND-TRIM-001: edge trim geometry vs shader-based fine detail. Evaluate actual geometry requirements and performance.
- RND-QA-001: base-vs-evaluated mesh audit, five orthographic/angled views, local modification regression, side-effect checks.

These are **research candidates**, not registered CBDK parts/requirements. Do not silently create entries in catalog/authored_parts.json, catalog/addon_features.json, current STATE or release plan.

## Private-to-public transfer barrier

Keep user-provided reference images, screenshots, .blend/.glb files, private addon code, output renders, local personal paths and derived geometry **local only**. No upload to GitHub, GitHub Actions, Notion, releases, or an external AI/image service without separate explicit permission. Do not publish private dimensions, distinctive patterns, filenames, screenshots or any reversible representation of the private model.

Only general algorithms, wholly new synthetic examples and citations to already-public resources may be proposed in a public draft PR. A person must review whether the supposedly generic summary still reveals user data.

Third-party code is untrusted. Analyze externally published code as reference; never run/import it in trusted CBDK CI, copy it into CBDK, auto-register a feature, or bypass license review on the strength of its GitHub availability. Record the license of code, datasets and assets separately.

## Integration gates aligned with CBDK

1. Check latest AGENTS.md, docs/PARALLEL_DEVELOPMENT.md, docs/project/STATE.json, current development HEAD and open PRs.
2. A assigns a narrowly scoped task and allowed files; do not overlap B/C/D specialists.
3. Before writing a helper, search existing parts/, catalog/, tests/ and current recipes for equivalents.
4. For an accepted algorithm, implement only an independently written CBDK-authored synthetic candidate behind existing safety limits, with explicit context/mode preflight. No arbitrary external code ingestion.
5. Test on synthetic fixtures locally then on required Python/Windows/Blender version matrix, preserving precise SHA-matched CI evidence. Check user-mode GUI separately when needed.
6. A reviews behavior, negative tests, licensing, provenance, shared-file implications and dependencies. Only A updates shared STATE/Handoff/Notion at the appropriate milestone.
7. Keep any draft PR unmerged until review. No main merge, public release or automatic installation without separate authorization.

## First bounded pilot

Test **one generic curved quad panel and one swept strap**, without human-body meshes or copyrighted reference art. Compare subdivision 0/1/2, edited control-cage stability, evaluated mesh count, mesh continuity, basic UV/material feasibility, and modifier ordering. Do not try to build a complete garment or a full-body character at this stage.

**Completion means a reproducible synthetic experiment report**, not a production modeling feature. After the pilot, file an A-reviewed handoff proposing the smallest useful helper, or record why existing Blender operations are sufficient.

## Current integration boundary

This proposal adds only research documentation. No Blender MCP remote tool, package dependencies, runtime helper, auto-ingest, licensing approval, synthetic verification or CI pass is claimed. Changes to the existing repository skill/AGENTS and any implementation are deferred to a separately scoped integration PR.