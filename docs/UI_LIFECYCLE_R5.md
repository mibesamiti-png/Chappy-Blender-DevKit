# Team C R5 — native Blender lifecycle probe (UI-001 / BUILD-001)

**Scope:** One small specialist R5 task for the five CBDK-authored modular-preview features and existing six recipes. Based on the v0.18 development HEAD after Team A's merged [R4 PR #43](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/43) and R5 allocation [PR #44](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/44). Do not merge old R1–R4 PRs a second time.

## Why a dedicated fixture?

Existing A-owned `scripts/blender_modular_addon_smoke.py` already tests real Blender enable/disable, Object/Edit operations, mode guards, partial registration failure recovery, typed XYZ inputs and a foreign-property *pre-registration* collision for all six generated modular recipes on Blender 4.4.3/4.5.15/5.2.1.

R5 additionally requires a repeated **register → mode switch → operator refusal → unregister → re-register** sequence and synthetic foreign-property *replacement after registration*, with actual Blender RNA object identity rather than only a fake Python class.

Team C is **not authorized** to edit the A-owned script, shared workflow, or canonical STATE/HANDOFF. Instead:

- New **C-owned** `tests/blender_ui_lifecycle_r5.py`: a standalone, factory-startup Blender-only probe. It accepts **only** an explicitly built local `modular_all` preview ZIP and checks the fixed feature allowlist / preview-only provenance before extraction.
- It cycles Object → Edit Mesh → Object three times; with zero selected vertices, confirms the XYZ editor remains enabled, nudge and wrong-mode Object operator return `CANCELLED` without geometry/result changes; then disables, performs four real register/unregister rounds, tests foreign `Scene` property collision, and substitutes a new controlled Blender RNA declaration while registered to ensure CBDK unregister doesn't delete the replacement.
- A fixed `CBDK_R5_UI_LIFECYCLE_PASS` JSON line is printed **only after every assertion succeeds**. This is real **headless Blender** evidence, not GUI hotkey or human mouse proof.
- New `tests/test_ui_lifecycle_r5.py` adds synthetic missing-token/inherited-foreign safety regression plus both-owned-name replacement, and validates the optional probe/ZIP allowlist contract. This test runs in normal Python CI but **must not be counted as a native Blender pass**.
- `templates/modular_preview/__init__.py` refuses to treat a missing descriptor token and a missing class-dictionary entry (`None is None`) as authorization to delete an inherited/foreign property. This keeps the existing R3 identity guard but makes it fail closed when ownership evidence is absent.

## How to run the additional native fixture (requires A orchestration)

On an isolated checkout of the R5 branch with trusted CBDK source and an installed official Blender binary:

```sh
python -m cbdk build-addon --recipe recipes/modular_all.json --target-blender 4.5.15 --preview-unapproved --output /tmp/cbdk-r5-modular-all.zip
"$BLENDER_PATH" --background --factory-startup --disable-autoexec --python-exit-code 7 --python tests/blender_ui_lifecycle_r5.py -- /tmp/cbdk-r5-modular-all.zip
```

Repeat with target Blender 4.4.3 / 4.5.15 / 5.2.1 and a **fresh** output ZIP for each version. Require exactly one `CBDK_R5_UI_LIFECYCLE_PASS` JSON record, zero Blender process exit code, and the expected fixed check names. This test imports **only CBDK-generated authored code**, never scanned/private or arbitrary third-party Python. The foreign add-on is simulated by **controlled property declarations on the actual Blender Scene type**; it is not a real third-party addon.

**Important:** The existing GitHub Blender matrix invokes the A-owned shared smoke, **not this new file**. Without A wiring the new fixture into that matrix (or an A-run standalone CI job), its results must be labeled **native-probe not run**, even if standard Blender workflow is green. This distinction is deliberate. Request Team A to add an explicit step under `Build and test six modular recipe combinations in real Blender` after building `CBDK_modular_all_Preview.zip`:

```sh
"$BLENDER_PATH" --background --factory-startup --disable-autoexec --python-exit-code 7 --python tests/blender_ui_lifecycle_r5.py -- reports/ci/CBDK_modular_all_Preview.zip
```

The shared workflow is reserved for A; this C PR does not change it. Blender version-matrix execution must be verified on the *exact combined SHA* after wiring before promoting native coverage. If the probe reveals Blender RNA identity differences, record the actual traceback and reproduce with disposable synthetic Scene data, then fix in a specialist-owned branch.

## Safety and completion boundary

The R5 specialist PR can verify ordinary Python tests, full existing Blender suite, Windows launchers, Chromium, Handoff, and any actually triggered Kit/Skill tests. **Do not claim the new native fixture ran unless the log explicitly includes its pass sentinel on each Blender version**. Unverified: real Windows GUI, GUI Undo shortcuts, real foreign third-party addon interference, private source data, license clearance, formal Extension distribution or main release. All remain partial.
