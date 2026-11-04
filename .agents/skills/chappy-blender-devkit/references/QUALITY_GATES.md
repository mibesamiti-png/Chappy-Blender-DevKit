# CBDK verification / release gates

Separate evidence from approvals. Treat missing evidence as **not tested**, not as success.

| Level | Evidence | What it does NOT prove |
|---|---|---|
| Static inspection | AST inventory, dependency closure, hash consistency, API audit | Correct runtime behavior, legal redistribution |
| Python unit tests | Actual test logs with Python version and pass/fail count | Blender API integration |
| Blender smoke | Actual official/tested Blender version, CI run or local evidence JSON, part/check IDs | Compatibility across versions, all addon behaviors |
| Manual review | Documented behavior, edge cases, performance and ownership review | Automatically granted redistribution permission |
| Approved reusable part | Explicit project-approved provenance, license clearance, compatibility evidence and necessary tests | Future unchanged behavior after code changes |

## Implementation review checklist

- Identify existing helpers by searching `parts/`, `catalog/` and private catalog when accessible.
- Document function arguments/outputs, explicit context needs, side effects, supported Blender version and error handling.
- Distinguish selected Object/Edit mode and single/multi-mesh Edit Mode. Test empty/missing selections and problematic meshes.
- Keep old source behavior unchanged unless requested, with regression tests for known bugs.
- Do not execute untrusted import-time Python. Inspect with AST first; test newly authored, reviewed code in a disposable scene.
- Never silently combine similar/identically structured functions; analyze external state and compatibility.
- Update source and test evidence together; changing the source invalidates previous SHA-based verification.
- Review data/rights before sharing: original addons, source-derived reports, proprietary functions and third-party licenses.

## CI and status rules

- Local unit-test success is distinct from GitHub Actions success.
- The repository's cloud Blender workflow uses Blender 4.5.15 LTS and checks BLCTX-001, BLCTX-002 and BME-001 only, unless the workflow/tests are extended.
- A green job without checking the target commit or changed paths is not sufficient evidence.
- `catalog/authored_parts.json` may still say `blender_runtime: not_recorded` despite a separate CI run; don't silently rewrite approval state. Cross-reference evidence explicitly.
- Missing Blender locally means `not_run`, not `failed` or `passed`.
- Never report arbitrary extracted code as Blender-tested because the three built-in helpers passed.

## End-of-task report template

1. **Implemented:** feature IDs, affected files and what behavior changed.
2. **Checks:** Python tests, Blender runtime run URL/version, what was not run.
3. **Privacy/provenance:** whether original source files or reports stayed uncommitted.
4. **GitHub:** branch/PR/commit and whether merged into `main`.
5. **Remaining:** limitations, open risks and next useful task.

Do not fabricate test counts, CI URLs, measured performance or version claims. Obtain them from the actual tools/logs.
