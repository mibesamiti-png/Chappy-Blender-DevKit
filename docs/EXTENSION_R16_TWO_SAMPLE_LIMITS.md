# Team D R16 — two-sample reference read blind spots (EXT-001)

**Status: synthetic test-only evidence.** This R16 work does not create,
change, or authorize a production source-reading or Blender Extensions
release API. It extends the R14 pinned POSIX directory-FD probe and R15
test-harness-held prior SHA-256 comparison without importing or executing
third-party/user addon code. Synthetic file names and contents only.

## What two reads do and do not establish

Two bounded reads of the same **allowlisted, synthetic** checkout source
can agree with an independently held prior digest. That establishes only
**two sampled byte observations**, not that the source remained unchanged
between observations, remains unchanged afterward, has a trusted
cryptographic origin, or can be redistributed.

Tests deliberately distinguish:

1. **No mutation seen:** both observations match the independent prior
   normalized digest. The result is
   \`observed_two_samples_match_prior_digest\`, **review-only**, never
   \`stable_source_verified\` or release approval.
2. **Change persists between samples:** first matches and second differs,
   returning \`inconclusive_sample_disagreement\`. This is observable
   *difference evidence*, not attribution of author or motive.
3. **Change then restore between samples:** the source is rewritten with
   same-length bytes, then restored. Two separately instrumented real R15
   observations **both match** the prior digest, missing the temporary
   mutation entirely. When this mutation is deliberately injected through
   a *trusted synthetic test hook*, R16 returns
   \`inconclusive_gap_mutation\` even though the two samples agree.
   Real, unobserved between-sample mutation cannot be proven absent.
4. **Source already differs before both reads:** both samples disagree
   with the independent prior; \`inconclusive_prior_digest_mismatch\`
   does not distinguish legitimate checkout revisions from tampering.
5. **Change after the second sample:** the prior two-sample report
   remains historical evidence; the real file can change immediately
   afterward. The report permanently states
   \`current_source_stability_verified=false\`.
6. **Unknown prior digest, nonallowlisted path, unsupported Windows
   no-reparse handles, or stale pinned directory identity:** fail
   closed before unauthorized content reads and without any positive
   source, owner, license or release claim.
7. **Bounded test work:** exactly two observations at most, using
   R14's per-member \`2 MiB + 1\` detection bound (aggregate at
   most \`2 × (2 MiB + 1)\` bytes read), existing archive limits
   \`16 MiB / 2 MiB / 64 members\`, and a 30,000 ms **post-read
   review deadline**. Invalid duration settings refuse before reads.
   This duration check **is not a preemptive I/O timeout or OS sandbox**
   and must not be represented as a guaranteed wall-time limit.

The helper returns **fixed reason/status codes and bounded counters only**.
There is no raw source, hash, path, marker, author data, secret, personal
information, licensing text or executable content in a report. The
previous false authorization flags remain false, alongside explicit
\`sample_gap_stability_verified=false\`,
\`current_source_stability_verified=false\`, and
\`independent_reference_origin_verified=false\`. A prior digest in these
tests is assumed independently held by the **test harness**; it is not a
verified Git commit signature, an authenticated owner declaration, or a
source of authorization.

## Invariant existing coverage

- All **seven CBDK-authored preview ZIP recipes** still pass canonical
  static archive/provenance checks and remain
  \`blocked_for_extension_release\`; no code is imported/installed.
- Archive/member/count caps stay **16 MiB / 2 MiB / 64**.
- The existing real Blender CLI **six data-only synthetic official
  validator cases** are required in each of 4.4.3, 4.5.15 LTS and
  5.2.1 LTS. They do not validate a real third-party Extension.
- Windows intentionally returns
  \`inconclusive_platform_handle_guarantee\` and does **not** acquire
  arbitrary addon content with Python's insufficient native reparse
  guarantees.
- Genuine author consent, SPDX/license/redistribution compatibility,
  independent signed source provenance, official Extension build/install/
  uninstall, real Windows GUI and public release are **not verified**.
  \`EXT-001\` remains **partial**.

## Caveats and next design seed

The R16 two-read helper is a controlled race **model**, not a
production-safe method to automatically read untrusted source. It cannot
catch an adversarial change-and-restore wholly in the uninstrumented
sample gap. POSIX \`O_NOFOLLOW\` behavior in a synthetic checkout is not
a proof of Windows-native junction and reparse point safety. Independent
digest provenance and malicious filesystem races still need separate
threat-model verification.

**R17 candidate, not formally allocated:** test a **pinned, separately
attested source revision** (synthetic immutable artifact or trusted
external reference) against sampled code, and quantify which replay
histories are unobservable with bounded source reads. This still cannot
grant licensing, consent, install or release permissions. No R17
branch/PR until A's latest dev post-merge CI and new formal allocation.

Coordinator A alone manages shared STATE/Handoff/PROGRESS, scripts/CI,
Notion, combined-head integration and independent seven-family
post-merge verification. No old specialist PR, main, release or
Geometry/DIL research branch is changed by this Team D patch.
