# EXT-001 / Blender Extensions compatibility preflight (development only)

This is a **static readiness audit**, not a Blender Extensions release builder.
CBDK's current private previews use legacy ZIP layout and the authored part
catalog explicitly lacks formal redistribution approvals and reviewed license
evidence. Therefore this command always reports **blocked_for_extension_release**.

## Command

Create a local legacy preview ZIP in the usual explicit opt-in workflow:

```shell
python -m cbdk build-addon \
  --recipe recipes/modular_all.json --preview-unapproved \
  --target-blender 4.5.15 --output reports/latest/modular_preview.zip
python -m cbdk extension-preflight reports/latest/modular_preview.zip \
  --output reports/latest/extension_readiness.json
```

The JSON includes an integrity result, safe known metadata, missing
manifest fields, current permission/approval blockers, and future steps.
It does not contain Python source or GLB data, does not execute source,
does not install anything, and does not emit an Extension-compatible ZIP
or `blender_manifest.toml`.

- The preflight rejects unexpected package identity, path traversal,
  duplicate members, untrusted flags, mismatched file SHA-256,
  oversized members, symlinks, and invalid metadata.
- Existing project/source licenses remain unresolved. Never infer SPDX
  terms from public GitHub visibility or from passing CI.
- Fields requiring owner review (`version`, `maintainer`, `license`)
  are deliberately **null** in the JSON-only draft. Incomplete manifests
  must not be emitted as if Blender accepted them.
- The report is a blocker inventory, *not* license clearance.
  A tamper-resistant checksum is not a code audit or legal approval.
- The command won't overwrite an existing report and will not convert
  arbitrary third-party or private ZIPs into trusted assets.

## Official Blender workflow after explicit approval

Blender's [official Extensions manual](https://docs.blender.org/manual/en/5.2/advanced/extensions/getting_started.html)
requires a `blender_manifest.toml` with an add-on at the extension
root (or a documented nested package), valid type/name/id/version/license/
maintainer/tagline/min-Blender information. The next approved development
stage will build a **separate** extension package and run:

```shell
blender --command extension validate <new-approved-extension.zip>
```

That command has **not** been run by this preflight.
A successful future validator result alone cannot authorize publishing,
private source execution, Blender GUI Undo/Redo guarantees, or reuse
of components without reviewed licensing.

The existing `build-addon` legacy preview packaging path and its
`--preview-unapproved` safeguard remain unchanged. EXT-001 is
**partial** only for structural preflight; formal Extensions release
is not implemented or approved.

## 2026-11-08 JST: bounded manifest structure review

`manifest_structure_review` now lists missing required fields separately from
field-specific invalid values. It checks schema/id, SemVer, printable owner
metadata, tagline length/suffix, minimum Blender 4.2+, and SPDX-prefix **syntax**.
Unsupported optional fields require official validation; this is a bounded
subset, not a complete SPDX registry/compatibility or Blender manifest validator.
`blocker_categories` separates metadata, approval, packaging and verification.
Missing license/owner input remains null and blocks release. No license is chosen.

The ZIP audit also checks exact part dependency IDs and helper/file closure,
rejecting invented/duplicate parts or undeclared files even if hashes agree.
`source_authenticity_verified=false`: self-consistent hashes do not authenticate
source origin. Packaged Python is never executed by this preflight.

`scripts/verify_extension_manifest.py` invokes the **official** Blender
`--command extension validate` on three disposable, synthetic manifest cases:
a valid subset, a missing license, and invalid tagline punctuation. The sample
SPDX value belongs only to validator test data; it is not a license declaration
for CBDK or its components. The fixture's Python raises if imported and is never
loaded. No real Extension ZIP is built, installed, approved or released.
The real preview report's official-validation flag remains false.

Rules were checked against the [Blender 4.5 manual](https://docs.blender.org/manual/en/4.5/advanced/extensions/getting_started.html)
and the locally installed Blender validator. Target-version evidence is recorded
in STATE after CI, separately from local Blender 4.3.2.
