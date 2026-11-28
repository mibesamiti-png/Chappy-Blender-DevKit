# CBDK CLI runbook — inspect current help before executing

Run from the CBDK repository root with Python 3.11–3.13. These examples
illustrate safe workflows; `python -m cbdk --help` and actual code are
authoritative. Never assume untracked private files are available.

## Source inventory (authorized local source only)

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk search "選択 頂点" --catalog reports/latest/catalog.json
python -m cbdk triage --catalog reports/latest/catalog.json --duplicates reports/latest/duplicates.json --output reports/latest/review_queue.json
python -m cbdk audit-blender --catalog reports/latest/catalog.json --output reports/latest/blender_audit.json
```

`isolate`, `bundle` and `crossfile` can inspect conservative dependency
closures. Verify candidate ID and source SHA first; use review mode without
`--output` initially. Never import, execute, publish or auto-approve
untrusted or extracted addon source.

## Trusted feature planning / preview-only ZIP

```bash
python -m cbdk feature-list
python -m cbdk addon-plan --recipe recipes/modular_all.json --target-blender 4.5.15
python -m cbdk build-addon --recipe recipes/modular_all.json --target-blender 4.5.15 --preview-unapproved --output reports/latest/modular_preview.zip
python -m cbdk extension-preflight reports/latest/modular_preview.zip --output reports/latest/extension_readiness.json
```

The catalog has five CBDK-authored preview features and seven authored
parts *at the inspected v0.18 baseline*; re-check the repository if this
changes. An `addon-plan`, verified preview ZIP, or `extension-preflight`
does not grant redistribution permission or create a Blender Extension.
Unknown modules and arbitrary UI Python may not be accepted automatically.

## Blender / Python and synthetic GLB

```bash
python -m unittest discover -s tests -v
python -m cbdk verify-parts --blender blender --output reports/latest/parts_evidence.json
python -m cbdk evidence-status --evidence reports/latest/parts_evidence.json
```

For GLB diagnose and visualization, inspect
`python -m cbdk glb-diff-visualize --help`,
`python -m cbdk glb-inspect --help` and
`docs/GLB_DIFF_VISUALIZATION.md` before selecting flags.
Never send private GLBs, their derived HTML, or user add-on source to
public GitHub Actions. Public CI may use only repository-authored
synthetic fixtures.

CI workflow: `.github/workflows/blender-smoke.yml` runs
Blender 4.4.3 / 4.5.15 / 5.2.1 at the inspected baseline and
tests six modular preview recipes. Other workflows cover Python,
Windows PowerShell, kit packaging, durable handoff and browser smoke.
Read live workflows for the present matrix; report success only for
completed runs on the matching commit.

On Windows, inspect `run_blender_tests_windows.bat` before use.
Local headless Blender does not prove Windows GUI interactions or native
keyboard shortcuts. Preserve original files and previous results.

## Durable development handoff

```bash
python scripts/project_handoff.py --write
python scripts/project_handoff.py --check
python scripts/package_skill.py --output-dir dist
```

The packaged skill is a reusable **instruction artifact**. Passing its
self-tests does not mean the generated add-on passed runtime smoke.
