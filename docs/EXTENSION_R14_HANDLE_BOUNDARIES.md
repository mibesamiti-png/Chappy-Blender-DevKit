# R14 Team D — Handle-anchored source race review (EXT-001)

**Scope:** R14 is a synthetic, bounded **test-only** study of the
precheck→open time-of-check/time-of-use gap seen in the R13 reference-read
prototype. It does not introduce a production source reader, a public
permission API, an Extension package, a checksum authenticator, or a
new install/release path. R13's test-only path checker and v0.18's existing
production ZIP preflight remain unchanged.

## What R13 proved, and what it did not

R13 correctly refused stable leaf/ancestor symlinks, Windows junctions,
unknown source spellings and malformed inventory bases **before opening
source bytes** in controlled fixtures. It compared directory/file metadata
before and after a read. However, checking a pathname and subsequently
opening that same pathname is a separate operation. A synthetic or hostile
filesystem participant could replace a parent directory with a symlink or
junction **after** the lexical check but **before** an ordinary absolute-path
\`os.open()\`. A successful post-open inode/time comparison might recognize
a replacement *after bytes have already been opened*, which is too late
to claim zero unauthorized content reads. R13 did not prove an atomic
filesystem security boundary.

## R14 bounded, non-production test model

\`tests/test_extension_reference_race_round14.py\` models a safer **POSIX
only** strategy. It starts with a directory descriptor already pinned by
a trusted caller in a disposable CBDK-created checkout. Each allowed path
component is opened **relative to its held parent descriptor** using
\`dir_fd\`, \`O_NOFOLLOW\` and, for intermediate entries, \`O_DIRECTORY\`.
File identity and size are compared before/after \`open\`, with a bounded
final read of at most 2 MiB + one detection byte. The parent directory
handle stays pinned even if the pathname is renamed. Source names are
an exact hard-coded repository-owned allowlist, not archive-supplied
paths. A separate controlled callback can change a component after its
precheck but before the handle-relative open.

POSIX negatives explicitly exercise:

- parent symlink inserted after \`stat\` and before component \`open\`:
  the guard refuses it with **zero file-content reads**;
- leaf symlink substituted during the same window: no external bytes read;
- a different inode with the *same byte length and preserved mtime*
  substituted after precheck: reject on open-handle identity before read;
- a source modified after a bounded read: return an inconclusive reason
  and **no source bytes**, despite a prior successful precheck;
- exact 2 MiB source is bounded and observable; 2 MiB + 1 is rejected
  before content read;
- a root pathname replaced by a symlink **after a trusted directory FD
  is pinned**: the retained FD continues referring to the original
  directory rather than the external path;
- unknown, case/8.3-like or traversal source aliases, and an unrelated
  root descriptor: reject without content open.

Each test checks read/open counters, report redaction, and five stable
reason-only unverified authority codes. Allowed counters refer to
**this controlled test helper**, not a whole-process I/O audit or proof
against arbitrary kernel races. A mismatch is not automatically malicious:
legitimate repository source updates may produce the same difference.

On **Windows**, Python's ordinary \`os.open\`/stat model does *not* provide
the same directory-descriptor plus no-reparse guarantee in this test.
R14 therefore returns
\`inconclusive_platform_handle_guarantee\` **without content I/O**,
including against a real Windows runner-created junction fixture when the
host allows its creation. This is not a substitute for Windows
\`CreateFileW\` handle/reparse-point threat modeling. If the junction
creation capability is unavailable, the Windows-specific case must
be reported as *skipped*, not proven.

## Stable report schema and invariants

The test-only status is \`review_only\` (bounded bytes observed) or
\`inconclusive\`, with one of six fixed, value-free reason codes:

- \`reference_bytes_observed\`
- \`inconclusive_reference_basis\`
- \`inconclusive_reference_path\`
- \`inconclusive_reference_changed\`
- \`inconclusive_reference_limit\`
- \`inconclusive_platform_handle_guarantee\`

All report flags for source authenticity, author consent, license
compatibility, redistribution, signature, official Blender validation,
bundled code execution and public release remain **false**. The fixed
unverified reason-code tuple does not include any path, payload,
repository root, author name, contact, key, content or license string.
Private-looking labels in synthetic fixtures are deliberately fake.
A successful \`reference_bytes_observed\` is **not proof** of origin,
signature, rights or permission to ship.

This test does not establish a handle-level public API for arbitrary
untrusted source roots, Windows reparse-point races, network filesystems,
same-inode replacement with all metadata restored, hardlink changes,
in-memory byte mutations undetected by metadata, or cryptographic
snapshot provenance. Those are **still unverified** and cannot be used
to promote the test prototype into a production automatic reader.

The existing R4–R13 controls must remain green: seven known CBDK-authored
preview ZIPs (still \`blocked_for_extension_release\`), canonical archive
limits **16 MiB / 2 MiB per member / 64 members**, and Blender 4.4.3,
4.5.15, 5.2.1's six data-only real-CLI synthetic manifest validator
cases. CI confirmation of these is separate from legal approval,
installability, real GUI and arbitrary addon testing.
\`EXT-001\` remains **partial**.

## Coordination

Team D owns only this Extensions test file, the watched Extensions
preflight test and this dedicated document. No changes to
\`cbdk/extension_*\` production code are needed because the observed
absolute-path race was in an earlier **test-only** prototype and there
is no substantiated safe cross-platform production promotion.

Coordinator A alone owns combined-R14 integration, common
scripts/workflows, STATE/Handoff/PROGRESS/Notion/main, and the separate
integrated-SHA and post-merge CI checkpoints. No old R13 specialist
PR is remerged or retroactively modified.
