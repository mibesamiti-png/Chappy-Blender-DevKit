# EXT-001 — Team D archive integrity and validator diagnostic hardening

This is a **development-only** quality improvement to CBDK's existing
legacy-preview preflight. It neither produces a Blender Extension ZIP nor
certifies authorship, redistribution rights, source safety or runtime behavior.

## Separate failure classes

`inspect_preview_archive(path)` retains fail-closed behavior and raises
`ValueError` on malformed or untrusted inputs; the more precise
`PreviewArchiveError` subclass now carries `category` and `code`.
The additive `diagnose_preview_archive(path)` API returns sanitized JSON:

| Example | status | failure_category | failure_code |
| --- | --- | --- | --- |
| Valid CBDK-authored legacy preview | blocked_for_extension_release | n/a | n/a |
| Missing ZIP | invalid_preview_archive | archive_structure | missing_or_unsafe_input |
| Prepended/trailing data or ZIP comment | invalid_preview_archive | archive_structure | zip_envelope |
| Unsafe member mode/compression | invalid_preview_archive | archive_structure | unsafe_member |
| Corrupted member CRC or unreadable ZIP | invalid_preview_archive | archive_integrity | corrupt_or_unreadable |
| Mismatched source hash | invalid_preview_archive | archive_integrity | hash_mismatch |
| Duplicate provenance JSON key | invalid_preview_archive | provenance | duplicate_metadata_key |
| Untrusted approval bit | invalid_preview_archive | provenance | unsafe_approval_flag |
| Invalid dependency inventory | invalid_preview_archive | dependency_closure | part_ids |

An invalid ZIP **never** becomes a merely license-blocked result. The usual
`extension-preflight` CLI still refuses invalid archives and never writes a
successful readiness report for them. Classified errors never echo source
contents, input paths or untrusted member names. ZIP mode checks also reject
non-regular special files, encryption and unsupported compression.

The report's display name is fixed rather than copied from unauthenticated
build metadata, and `minimum_blender` is bounded to numeric Blender versions.
Provenance hashes are **self-consistency only** and are not signed origin proof.

## Official diagnostics and manifest scope

`observe_official_validation` keeps only known field identifiers and
statuses. Unknown/duplicated `missing` or `key ... invalid` lines, other
explicit error markers, and malformed success markers now yield
`unclassified`; they cannot be counted as complete agreement just because
some expected diagnostics matched. This is a bounded log parser, not an
authentication mechanism or a complete replacement for Blender's validator.

The existing `extension-manifest-review` parses TOML without executing addon
code. Missing owner fields remain distinct from invalid values and unknown
optional syntax. `scripts/verify_extension_manifest.py` exercises the real
Blender `--command extension validate` on **six data-only fixtures** with
deliberately unimportable Python. No part license is chosen by these fixtures.

## Test and safety boundaries

Focused tests: `tests/test_extension_preflight.py` and
`tests/test_extension_manifest.py`. The pre-existing Blender Actions workflow
runs the authored ZIP preflight and six official validator cases for its supported
Blender matrix; observe the PR run before stating that it passed. Python
`unittest discover` also executes the new regressions.

No source scanning or unapproved add-on import, no public Extension build,
no automatic source/license adoption, no release, no merge and no user data
are introduced by this change.

**Still blocked for release:** rights/compatibility review of every part,
owner-selected SPDX license and maintainer/version metadata, explicit adoption
and redistribution authorization, a separate approved Extension build path,
actual approved package validation/install/removal tests, and final publication
approval.

Blender specifications: https://docs.blender.org/manual/en/4.5/advanced/extensions/getting_started.html

## R3 rolling lane — validator log classification (synthetic only)

The R2 ZIP layout/provenance audit is unchanged. The R3 change tightens only
`observe_official_validation`: the entire bounded output must consist of
recognized field diagnostics, one consistent TOML status header, optional
Blender startup/shutdown markers, or blank lines. Previously ignored
free-form output is now **unclassified** rather than implicitly harmless.

**Allowed fixture classes (not authorization):**

| Source | Classification | Notes |
| --- | --- | --- |
| Real official validator, synthetic `valid_subset` | accepted / agreement | Required fields only; no approval |
| Real official validator, five synthetic invalid/missing-field cases | rejected / agreement | Each known diagnostic matches reviewed field |
| Synthetic optional Blender version banner / clean exit | same as core observation | Version banner is not evidence of authentic logs |

**Rejected synthetic log classes** (only labels and expected states recorded;
never copy validator paths, free-form values, emails or source snippets):

| Case | Expected observation |
| --- | --- |
| Unknown failure detail or unknown post-diagnostic line | unclassified |
| Missing and invalid for the same required field | unclassified |
| Success marker plus error header (either order) | unclassified |
| Success marker plus unknown warning / nonstandard line | unclassified |
| Duplicate generic error header | unclassified |
| Duplicate known field, malformed or repeated success marker | unclassified |

The official validator log **is observed, not authenticated**. This parser
must not convert a successful synthetic TOML run into permission to distribute
an Extension or claim a license. Blender's six data-only cases run through the
existing A-owned smoke workflow; neither the workflow nor the fixture script
is modified by Team D. Changes are limited to Extensions-owned code, tests
and this document.



## R4 — positive compatibility and fail-closed regression matrix

Base: current v0.18 development line after A's combined R1–R3 integration,
not the obsolete stacked R2/R3 preview branches. This round prioritizes
**not rejecting authentic CBDK development previews**, without weakening
previous structural security checks or granting release authority.

### Authored ZIP matrix (offline, no addon execution)

The Extensions preflight tests build **two independently generated**
archives for each of seven allowlisted authored recipes:

- Legacy: mesh_inspector
- Modular: modular_all, modular_combined, modular_edit,
  modular_geometry, modular_nudge, modular_objects

For every recipe the bytes must be deterministic; both
inspect_preview_archive() and diagnose_preview_archive() must agree and
return blocked_for_extension_release. The audit must confirm canonical ZIP
layout, hash inventory and source file count **without** setting
source_authenticity_verified, executing bundled Python, issuing a formal
Extension ZIP, or claiming owner/licensing/redistribution clearance. Each
recipe also has a negative control with appended bytes that must return
invalid_preview_archive with a sanitized error code. Input paths and
synthetic marker bytes must not appear in any report.

### Official validator observation matrix

The Extensions manifest tests use three observed version-banner formats:
4.4.3, 4.5.15 LTS and 5.2.1 LTS, with the same **six purely synthetic TOML**
cases as the A-owned real official validator fixture script. For each case:

- Expected clean accepted / known-field rejected observation must remain
  agreement for the local bounded subset, with
  complete_diagnostic_agreement=true **only for these synthetic inputs**.
- The same output with one unknown note must instead be unclassified,
  with complete_diagnostic_agreement=false.
- Free-form log text and fixture paths must not propagate to normalized JSON.

The repository's existing Blender CI runs the **actual official**
--command extension validate against six data-only fixtures in each
supported Blender version. This test suite contains no official program
invocation of its own and does not edit the A-owned verifier or CI YAML.
R4 should modify only tests if these positive and negative cases pass;
actual previously missed false rejections require a small, evidence-backed
change before adding any parser allowance.

**Always excluded:** real user addons, source execution, trademark/owner
identity authentication, SPDX license selection, redistribution approval,
formal Extension build/install/uninstall, Windows GUI confirmation and
publication. EXT-001 stays partial until the owner and A resolve those gates.


## R5 — versioned official-validator observations and sanitized failures

This is a development-only regression extension of R4's seven-recipe ZIP
positive/negative matrix. There are no changes to the production ZIP or
manifest parser unless an actual false acceptance/rejection is reproduced.

### Data-only official-log fixture comparisons

- A **3 × 6 × 2** matrix uses versioned Blender 4.4.3, 4.5.15 LTS and
  5.2.1 LTS startup banners; the six existing official-validator manifest
  categories (one valid and five known rejected); and LF/CRLF line endings.
  Optional blank lines, startup and clean shutdown markers must not cause
  false rejections. These are synthetic log fixtures, not executed addons.
- A **3 × 9** matrix checks complete agreement versus partial diagnostic
  agreement, known mismatch, duplicate fields, missing/invalid contradictions,
  unknown field diagnostics, mixed success/error headers and unknown warnings.
  Only the exact complete known pair may return complete agreement.
- A position matrix injects an unknown value-bearing log line before, between
  or after otherwise accepted output. The official observation must become
  unclassified at every position and must not serialize the line, path or
  synthetic marker.
- Recognized field diagnostics may contain free-form official reasons.
  Diagnostics keep only the allowlisted field identifier and code; they never
  echo reasons or filesystem paths. A returned agreement is consistency
  **only**, not proof of log authenticity, legal ownership or release approval.

The existing Blender CI continues to execute the actual official Blender
extension validator on six synthetic data-only manifest cases for each of
the three supported versions. R5's new Python tests are **additional** and
are not evidence of an executed official validator by themselves.

### Unchanged constraints

R4's all-seven authored preview tests and R2 ZIP envelope/provenance failures
remain unchanged. Valid preview archives still return
blocked_for_extension_release. Unexpected validator log lines never become
complete_diagnostic_agreement=true. R5 neither chooses a license/maintainer,
creates an Extension ZIP, installs code, modifies shared CI/scripts/STATE,
nor authenticates source or authorizes publication. EXT-001 remains partial.
