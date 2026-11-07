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
