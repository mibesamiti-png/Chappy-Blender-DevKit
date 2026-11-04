# CBDK CLI runbook

Run commands from the CBDK repository root with Python 3.11+. Use `python -m cbdk --help` and the current implementation as the authoritative CLI description.

## Source inventory and reusable-helper search

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk search "選択 頂点" --catalog reports/latest/catalog.json
python -m cbdk triage --catalog reports/latest/catalog.json --duplicates reports/latest/duplicates.json --output reports/latest/review_queue.json
```

Run the scan only if the user authorized access to a **local, private** source directory that exists. Do not create dummy source files just to pretend a scan succeeded. A scan parses AST; never import/run the inspected add-ons.

## Inspect candidates before any extraction

```bash
python -m cbdk isolate --catalog reports/latest/catalog.json --candidate CND-REPLACE --source input_sources_private/example.py
python -m cbdk bundle --catalog reports/latest/catalog.json --candidate CND-REPLACE --source input_sources_private/example.py
python -m cbdk crossfile --catalog reports/latest/catalog.json --candidate CND-REPLACE --source input_sources_private/pkg/main.py --sources-root input_sources_private/pkg
```

Replace placeholders with real candidate IDs and source paths from the catalog. First use the inspection mode (without `--output`). If blockers are clear, manually review provenance/license and create a **new** file with `--output reports/latest/extracted/helper.py`. The output is not an approved component. Fail closed on AST ambiguity, changed source hashes, cyclic dependencies, unsupported globals, aliases or external API calls.

## Blender-specific review and tests

```bash
python -m cbdk audit-blender --catalog reports/latest/catalog.json --output reports/latest/blender_audit.json
python -m cbdk contracts --audit reports/latest/blender_audit.json --output reports/latest/blender_contracts.json
python -m unittest discover -s tests -v
python -m cbdk verify-parts --blender blender --output reports/latest/parts_evidence.json
python -m cbdk evidence-status --evidence reports/latest/parts_evidence.json
```

On Windows use `run_blender_tests_windows.bat` for one-click testing after verifying its source. If Blender is not on PATH, provide its exact trusted executable to `--blender`.

Cloud integration: `.github/workflows/blender-smoke.yml`, triggered for matching PR file paths or manually via GitHub Actions. Check the **actual run's** status, supported version, part-level evidence and any failed steps. It currently verifies only three authored parts.

## Manual registry workflow

```bash
python -m cbdk register --catalog reports/latest/catalog.json --registry reports/latest/registry.json --candidate CND-REPLACE --part-id GEO-001 --name "Example" --purpose "Reviewed candidate" --origin self_owned --license-id LicenseRef-Proprietary --license-evidence "Owner-reviewed record" --reviewer "Owner"
python -m cbdk decide --registry reports/latest/registry.json --part-id GEO-001 --decision hold --reviewer "Owner" --reason "Blender behavior unverified"
python -m cbdk parts --registry reports/latest/registry.json
```

Never auto-fill license evidence with invented facts. Prefer `hold` until verified. `selected` means a human selected the candidate; it does not mean `approved`.

Generated catalogs, registries, original sources and private review reports belong outside version control by default.
