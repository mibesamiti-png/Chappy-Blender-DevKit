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


## R6 — bounded ZIP budgets and official-log size boundary

R6 extends the existing R4 seven-recipe positive suite and R5 3-version
official synthetic-log suite without executing user source or broadening
Blender's official-validator output allowlist. The goal is to verify the
**existing budgets**, not to claim a new Extension release capability.

The R6 Python negative fixture suite uses only CBDK-authored previews and
generated, tiny synthetic ZIPs. For large logical sizes it edits only
ZIP central-directory **size fields**; it never materializes or decompresses
the alleged large entries. It also checks sparse-like local temporary
files at the full-archive limit, which are rejected by the stat/envelope
guard before any ZIP content inspection. All tests use temporary paths.

- Archive physical bytes: 16 MiB minus one, exactly 16 MiB, and one over.
  Under/equal malformed synthetic files are invalid ZIP envelopes; above the
  hard cap fails as `archive_too_large` before opening the archive.
- Entry size: 2 MiB minus one, exactly 2 MiB, and one over, by central
  record metadata only. At/under the cap, intentionally forged local-vs-
  central sizes fail the canonical-layout check; above cap fails the
  `unsafe_member` guard before any payload decompression.
- Aggregate declared uncompressed bytes: eight empty entries each claiming
  2 MiB (equal to the 16-MiB budget), versus nine (exceeding the budget).
  At the cap, forged sizes are rejected by structural checks; above it,
  `uncompressed_budget` rejects before any content read.
- Member count: 63, 64 and 65 tiny synthetic entries. The former two
  proceed to provenance checks and fail for lack of a real CBDK inventory;
  65 is rejected by `duplicate_or_count` before deeper work.
- Canonical headers: a valid authored modular preview is a positive control;
  corrupt local-version, central-marker and directory-length variants must
  remain `invalid_preview_archive` with sanitized failure details.
- Official-validator observation: the parser's 200,000-character limit
  accepts harmless whitespace padding just below/at the limit, rejects
  oversized input with a controlled exception, and classifies a late
  unknown value-bearing line as unclassified rather than successful.

Budget thresholds are part of a **read-only static preflight**, not a
permission to create oversized input, authenticity proof, SPDX decision,
Extension ZIP or installable release. CI timing variability is not evidence
of a CPU-performance guarantee; these deliberately bounded fixtures are
small except the stat-only temporary file. No private paths/strings are
returned in report JSON. The only official CLI executions remain the six
A-owned data-only fixtures on Blender 4.4.3, 4.5.15 and 5.2.1 in CI.
Owner/redistribution approval, real GUI and real user addons remain outside
the scope. EXT-001 stays partial.


## R7 — bounded TOML manifest-file review and private-value non-disclosure

This stage is **data-only compatibility testing**, not approval of a real
Blender Extension or license. Source files are generated synthetic TOML under
temporary directories; the tests never import or execute any bundled source.

The R7 fixture suite tests these exact existing limits:

- Maximum **32 KiB input bytes**: syntactically valid TOML with long comments
  is reviewed at 32 KiB minus one and exactly 32 KiB, and is rejected one byte
  over. Comment bytes are harmless padding, not real confidential data.
- Maximum **64 top-level TOML fields**: 63 and 64 known/unknown synthetic keys
  are structurally reviewed, 65 is rejected before review output. Unknown key
  identifiers are replaced with generic `unsupported_field`; nested unknown
  TOML table names and source paths must not escape into reports.
- Duplicate keys/tables/dotted-key definitions, malformed UTF-8 and malformed
  TOML fail closed with no partial report, private values or absolute path in
  the normalized error message. The underlying TOML exception can still be
  retained as Python diagnostic context and is not a public report.
- Create-only JSON reports remain confined to `reports/latest/`. Existing
  outputs cannot be overwritten; symlink destination/source/parent and path
  traversal examples must not produce output outside that directory.
- A valid reviewed source is byte-for-byte unchanged and the JSON has all
  approval flags false; R4's seven positive authored ZIP previews and R5/R6
  known official validator observations still run in the full suite.

Existing review logic must not change unless the tests actually reproduce
an incorrect verdict or unsafe write. This does **not** authenticate a TOML
file's author, select SPDX/maintainer, verify licenses, authorize redistribution,
build an Extension ZIP, install untrusted Python or approve any publication.
The official synthetic six-case validator remains run separately by the
A-owned real Blender smoke on 4.4.3, 4.5.15 and 5.2.1; these TOML Python
tests do not claim to execute Blender. EXT-001 remains partial.


## R8 — separation of technical checks, ownership, rights and release

R8 tests the **provenance-evidence boundary** only. Existing preview ZIP
preflight can confirm canonical CBDK-style ZIP layout and matching included
hashes. Those are self-contained technical checks, not proof of author
identity, consent, SPDX/license compatibility, signing authority or
authorization to redistribute or publicly release.

### Five independent findings, never promoted into one approval

| Observation | May be measured now | Cannot infer |
| --- | --- | --- |
| Static authored-preview ZIP structural/hash check | Yes, on seven CBDK-authored development preview recipes | Source authenticity or permission to ship |
| Blender official manifest validator output | Yes, on six **synthetic data-only** fixtures in each of three Blender CI versions | That any real authored ZIP passed official validation or was executed |
| Real author/owner consent | No authenticated evidence | Consent from a self-asserted JSON/TOML field |
| Actual SPDX licensing and redistribution clearance | Only syntactic license shape on synthetic TOML | Compatibility, attribution clearance or license selection |
| Explicit release authorization | No authorization | Publishing permission based on successful technical checks |

The R8 tests assert this separation on all seven authored recipes, including
legacy mesh_inspector and six modular previews, while checking that every
valid preflight report retains \`blocked_for_extension_release\`,
\`preview_only=true\`, \`source_authenticity_verified=false\`, empty owner
version/maintainer/license, and pending owner/approval/packaging/verification
blocker categories.

Negative fixture cases retain the same explicit lack of authority:

- Inject forged positive evidence fields (author consent, SPDX compatibility,
  redistribution permission, signing, official-validation claim and release)
  into the preview's own \`CBDK_BUILD_INFO.json\`. The source package may still
  be structurally valid; these **self-asserted new fields** must never become
  trusted report flags or remove publication blockers.
- Attempt to alter **existing mandatory protective flags** such as
  \`preview_only\`, \`approved\`, \`redistribution_cleared\` and
  \`blender_runtime_verified_for_this_build\` on both legacy and modular
  previews. Each attempt must fail closed as invalid provenance.
- Add a synthetic traversal path to a ZIP. It must not be accepted as a
  canonical preview, even with otherwise valid package file content.
- Feed realistic-looking but **synthetically constructed** official-validator
  success text. An accepted parser observation is still
  \`authenticates_log=false\`; unknown, duplicate or contradictory official
  diagnostics must remain unclassified, and neither case proves authorship
  or licensing.
- Feed structurally valid TOML with a syntactically well-formed SPDX example,
  a claimed maintainer, and additional self-asserted owner-consent/release
  fields. Review remains \`review_only\` with \`release_authorized=false\`.
  Unknown keys, including nested ones, are sanitized. A bounded TOML
  nested-fanout example illustrates that the existing **64-field limit is
  on top-level fields**, not 64 recursive descendants; it does not authorize
  deeper claims or promise a worst-case resource bound.

The existing Python tests run **without any Blender executable**; the
separate A-owned Blender CI must still perform its existing six data-only
official extension-manifest checks in 4.4.3, 4.5.15 LTS and 5.2.1 LTS.
No private source is imported/executed, no formal Extension ZIP is built,
no author consent or license compatibility is assumed, and no release
approval is fabricated. All fixtures are temporary synthetic data from this
repository. EXT-001 remains \`partial\`.

Only change production preflight, manifest review or diagnostic code when
the new negative controls reproduce an actual unsafe escalation or privacy
leak. Shared validator scripts, workflows, STATE, Handoff, Notion, main and
the published v0.17.0 release stay owned by coordinator A.


## R9 — self-consistent SHA inventory is not source authentication

This round tests a narrowly scoped distinction between **file-integrity
consistency** and **authentic, approved source provenance**. Only generated
CBDK-authored legacy and modular ZIP previews are read, and the synthetic
modification is an inert appended Python comment. No package Python is
imported, executed, installed, signed, endorsed or redistributed.

For each of the two representative authored preview families:

1. An unchanged preview has the established
   \`blocked_for_extension_release\` report, positive structure/hash checks,
   and **false** source authenticity, consent, license compatibility and
   release authority. The full seven-recipe positive R4/R8 regression
   remains in place.
2. A helper is modified without updating either the ZIP inventory digest
   or per-part source digest: the result **fails closed** with the
   \`archive_integrity/hash_mismatch\` diagnostic, no private payload/path.
3. Updating the \`files_sha256\` member entry but not corresponding
   \`parts[*].sha256\` (legacy) or \`parts[*].source_sha256\` (modular)
   fails \`provenance/part_provenance_mismatch\`. Updating only the
   per-part entries without the inventory fails \`hash_mismatch\`.
4. Updating **both** the member hash and **all** corresponding part
   source digests creates a synthetically *self-consistent* static ZIP.
   \`provenance_hashes_verified=true\` only means the ZIP agrees with its
   own mutable metadata: \`source_authenticity_verified=false\`,
   \`preview_only=true\`, and \`blocked_for_extension_release\`
   **must remain**. Validating hashes is *not* verifying authorship.
5. Claiming author consent, SPDX validation, signature success,
   redistribution and publication through newly added self-asserted JSON
   flags must not affect status. For the legacy preview, both parts that
   reference the same helper must agree with the same digest; partially
   updated part declarations fail the dependency/provenance consistency
   guard.

These are data-only tests. The chosen helper comments are synthetic, not
external/unauthorized code. Unit tests do not execute Blender. Official
Blender manifest validator smoke against six unrelated **synthetic**
fixtures remains a separate A-owned CI check across Blender 4.4.3,
4.5.15 LTS and 5.2.1 LTS; those observations neither authenticate these
packages nor authorize licenses or a release.

This test does not establish that CBDK package contents are signed,
authentic, copyright cleared, SPDX compatible or installable as an
official Extension. EXT-001 remains \`partial\`. Production code should
change only if a concrete unsafe permission escalation or privacy leak
appears; common scripts/CI/STATE/Handoff/Notion/main are A-owned.


## R10 — separate repository source comparison (development-only)

**Status: test-and-design evidence, not a new production trust API.** R9
demonstrated that a ZIP can be self-rehashed: its recorded digests can match
modified packaged helpers even though those helpers differ from the current
CBDK checkout. The R10 Python tests model a bounded, **read-only** comparison
with a reference independently read from known repository-owned source files.

The comparison is deliberately in the D-owned test suite, not in release
packaging. It must **not** alter \`cbdk/extension_preflight.py\`,
\`source_authenticity_verified\`, signed-package status or publication gates.

### Tested comparisons and hard bounds

- The reference root is fixed to the imported CBDK \`addon_builder.ROOT\`
  checkout (resolved once). An unknown root argument, an absolute/traversal
  source name or a name outside the hard-coded \`SOURCES\`, \`HELPERS\` and
  \`TRUSTED_FEATURES\` mappings must be refused. No path from the archive's
  own JSON is treated as an authoritative external reference.
- At most the existing \`MAX_MEMBERS=64\` members are inspected, and only
  for valid preview ZIPs already accepted by \`inspect_preview_archive\`.
  Archive size remains bounded by \`MAX_ARCHIVE_BYTES=16MiB\` and each
  referenced file/read by \`MAX_ENTRY_BYTES=2MiB\`. ZIPs failing canonical
  checks are not promoted to a source comparison.
- Normal CBDK-authored ZIPs from **all seven** known recipes are compared
  byte-for-byte against current repository-owned helper and modular feature
  file contents, with the same CRLF-to-LF normalization used by the builder.
  Only allowlisted helper/feature members are compared. Generated init/README
  content is excluded because those are template-expanded, not direct copies
  of a single known source path.
- A changed helper with **unmodified** declared SHA is rejected by the
  existing archive-integrity preflight before comparison. A changed helper
  with **both** self-declared file and part hashes updated passes static
  *internal* ZIP checks but differs from the independent, currently checked
  out source. Reports contain **only a status and bounded counts**, never
  raw code, paths, member names, user values, license text or marker strings.
- A hypothetical **updated known source** is simulated strictly by creating
  an *in-memory test snapshot* with the same changed bytes; comparison then
  yields byte equality against the simulated reference. This does not
  overwrite the real repository or accept arbitrary caller-controlled roots.
  It illustrates that equality is relative to the selected source snapshot.
- References with an unknown name/root, incomplete or unexpected member
  inventory, non-byte content or oversized values are rejected; original
  repository source file bytes remain unchanged. The independent comparison
  does not import/execute/install packaged code.

The test-only results \`same_known_repo_bytes\` and
\`different_known_repo_bytes\` mean **byte agreement with the selected
known checkout or synthetic reference snapshot**, nothing more. Even
\`same_known_repo_bytes\` leaves all of
\`source_authenticity_verified\`, author consent, SPDX/license compatibility,
redistribution permission, official Blender Extensions validation and release
authorization **false**. The final canonical ZIP status remains
\`blocked_for_extension_release\`. R4's seven valid previews, R9
self-rehash regressions and A's six **data-only** official Blender validator
fixtures in versions 4.4.3/4.5.15/5.2.1 remain required.

The comparison's fixed-root allowlist is a *test property*, not proof of
the repository's signed origin. Actual owner approval, externally verifiable
signature, source rights, private-user addons, Windows GUI and formal
Extension creation/install/uninstall remain unverified. EXT-001 is still
\`partial\`. Shared CI/scripts/STATE/Handoff/Notion/main are A-owned.
