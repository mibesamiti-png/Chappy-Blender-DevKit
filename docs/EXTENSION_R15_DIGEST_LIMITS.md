# Team D R15 — same-inode metadata replay and prior digest limits (EXT-001)

## Scope and result type

R15 extends the **test-only** R14 pinned-handle source experiment. It does
not add a production source reader or an authenticated Git commit binding.
Tests use disposable, synthetic checkout source files plus the seven
CBDK-authored positive preview ZIP recipes only. No private addon or third-
party Python is imported, executed, uploaded, installed or published.

The central question is whether **same-inode, same-length content changes
with the original mtime restored** can be mistaken for stable source.
On a normal filesystem R14's open-time and post-read stat also include
ctime and may detect such a change. But **mtime and inode alone are
insufficient**, and deliberately replayed/masked metadata cannot establish
bytes unchanged. SHA-256 of previously sampled bytes can distinguish them
from a **separately pinned prior digest**, not prove authorship or
authorize publication.

## R15 synthetic test matrix

- **Independent digest absent, malformed, unknown:** refuse with
  \`inconclusive_reference_basis\` **before any source content read**.
  Never derive this digest from the ZIP being evaluated.
- **Known prior SHA-256 (64 lowercase hex) of normalized synthetic bytes:**
  a bounded R14 POSIX dirfd/O_NOFOLLOW observation may report
  \`observed_bytes_equal_independent_digest\`, meaning only that the
  **observed sampled bytes** match this test-harness-held digest. This is
  not proof the current file is still identical, that a Git commit is
  signed or that any license/owner permissions exist. CRLF→LF
  normalization follows the R14/builder contract.
- **Same inode, same byte count, original mtime restored after rewriting
  between precheck and open:** expect R14's ctime-inclusive identity
  check to refuse with \`inconclusive_reference_changed\` and no
  file-content read. Test records inode/mtime/size equality but does
  **not** claim real ctime can be set arbitrarily by an unprivileged
  writer.
- **Adversarial metadata-replay model:** monkeypatch only R14's
  **test-only metadata comparison** to omit ctime; preserve inode,
  length and mtime on actual temporary source. The bound source then
  may be sampled, but an **independently frozen earlier SHA-256**
  detects the observed byte difference. There is no cryptographic
  identity check on the filesystem participant or prior-digest source.
- **In-place modification after the read:** if the deterministic
  after-read mutation is explicitly present and metadata comparison
  is intentionally weakened, the experiment returns
  \`inconclusive_reference_freshness\` even when sampled bytes match
  the prior digest. Thus it does **not** present sampled equality as
  a proof of current-file stability. Unknown hostile races without
  an explicit hook remain unproven; this wrapper is a test model,
  not a production TOCTOU guarantee.
- **Legitimate revision versus unauthorized edit:** two synthetic
  histories with identical resulting changed bytes produce the **same**
  \`observed_bytes_different_independent_digest\`. A digest mismatch
  cannot identify motive or distinguish legal updates from tampering.
- **Unknown path, stale pinned root, oversized file, Windows lack of
  native no-reparse handle guarantee:** retain R14's fail-closed
  codes and **zero unauthorized content reads** under controlled cases.
  Source cap: **2 MiB**, archive cap **16 MiB**, ZIP members **64**.
- **Seven CBDK-authored preview positives** retain
  \`blocked_for_extension_release\`. The existing actual Blender
  CLI test against **six data-only synthetic manifest fixtures** on
  versions 4.4.3/4.5.15/5.2.1 is an independent CI gate, not evidence
  of a real Extensions release.

Only fixed reason/status codes, content-open counters and bounded byte
counts are reportable. Reports omit every file path, private-looking
fixture payload, raw source, actual digest and owner/license value.
Flags for \`source_authenticity_verified\`, \`owner_consent_verified\`,
\`license_compatibility_verified\`, \`redistribution_authorized\`,
\`signature_verified\`, \`official_blender_extension_validate_ran\`,
\`python_code_executed\` and \`release_authorized\` **always remain
false**. The R15 digest parameter is only an *independent evidence
assumption* created by its test harness, not a public trust root.

## Limits and next research

Not tested or proven: adversarial races with no deterministic test hook;
privileged restoration/forging of all inode clocks, hardlink swaps,
network/virtual filesystem consistency, hash-reference provenance
authentication, native Windows file handles with reparse restrictions,
arbitrary user addon reading, Windows GUI, actual Extension
build/install/sign, author consent, SPDX/license attribution or
redistribution clearance. A digest of observed bytes does not prove
those bytes are **currently** unchanged after the read.

**EXT-001 stays partial**, and there is no authorized formal release.

R16 research candidate (not allocated): a strictly bounded, synthetic
**two-sample/independent signed-snapshot provenance separation** to
demonstrate that re-reading improves detection probability but still
cannot prove stability against adversarial between-read changes.
Investigate independently authenticated reference provenance as a
separate trust problem; no automatic read of third-party/private
sources, no approval flags, and no production adoption without a
cross-platform handle threat model and A authorization.

Coordinator A exclusively owns combined R15 integration, shared
scripts/CI/STATE/Handoff/PROGRESS/Notion/main and the separate
integrated-SHA plus post-merge seven-family CI gates. R14 individual
specialist PRs must not be merged twice.
