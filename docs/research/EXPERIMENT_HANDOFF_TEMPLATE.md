# 3D研究 → CBDK 引き継ぎテンプレート

Copy this template for **one** experiment. Keep original private experiments local, and prepare a separately redacted public handoff only after privacy review.

## Identity

- Research ID: RND-...
- Title:
- Date / recorder:
- Stage: DISCOVERED | DESIGNED | LOCAL_PROTOTYPE | SYNTHETIC_VERIFIED | REVIEW_READY | INTEGRATED
- Intended CBDK owner / assigned branch: **unassigned** by default
- External reference URL, author, retrieval date, pinned version/commit:
- Code license / dataset & art asset licenses (separate):
- Allowed use: study only | original implementation proposal | license review needed

## Problem and algorithm

- Problem solved:
- Existing CBDK part/catalog/recipe search results:
- Baseline method:
- Proposed algorithm / pseudocode in own words:
- Input / output schema:
- Preconditions (Object/Edit mode, modifiers, scene state):
- Side effects / data mutation / undo plan / bounds:
- Explicit non-goals:
- Failure and rollback behavior:

## Reproducible evidence (no guesses)

- Blender executable/version and OS:
- Test fixture: **synthetic and authored** | permitted private local (never upload)
- Script/test SHA-256 and repository commit (if any):
- Exact command (with no private path/secret):
- Parameters:
- Base vertices/edges/faces; quad/tri/n-gon ratios:
- Evaluated faces at Subdivision 0/1/2:
- Mesh continuity; boundaries; manifold/nonmanifold; normal quality:
- Modification edit test and changed/unaffected regions:
- Material/UV or display checks:
- Timings, CPU/RAM and hardware/conditions:
- Front/side/back/angled visual check: measured | manually judged | not checked
- Tests passed/failed/skipped, with direct evidence links or **local only**:
- Known counterexample and why:
- Unverified / unable-to-check:

## Safety and ownership review

- Private references, patterns, screenshots, scripts and derived meshes excluded from this handoff? yes/no
- Third-party code imported, run, copied or embedded? yes/no (default **no**)
- Licensing/attribution disposition:
- Unexpected write, file/network access, dynamic code execution risk:
- Compatible with current safety caps / no arbitrary third-party execution?
- Which existing CBDK tests, catalogs, interfaces and workflows could be affected?
- Which of A/B/C/D is authorized to own any production implementation?

## Proposed next step

- Reusable outcome: documentation only | test fixture | authored helper candidate | defer
- Smallest proposed public synthetic fixture and negative test:
- Measurable acceptance criteria:
- Required CI (Python/Windows/Blender versions/other as applicable):
- Human GUI or real-user test still needed:
- Risk of scope creep / duplication:
- A coordinator review decision: pending | accepted for scoped implementation | rejected | deferred
- Link to scoped issue or draft PR:
- Next action and stop condition:

**Never equate a generated demo, an agent assertion or a local private render with an approved reusable CBDK part.**