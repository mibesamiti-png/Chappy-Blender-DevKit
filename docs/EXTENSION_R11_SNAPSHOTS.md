# R11 D — bounded source snapshot observations

Base: `a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`.

Four new tests use CBDK-authored ZIPs and disposable synthetic checkouts.
The R10 helper remains test-only; no public trust API or production change
was justified by these cases. No arbitrary ZIP Python is executed/imported.

- A lawful checkout update and a self-rehashed ZIP edit yield the same kind
  of byte mismatch against an old snapshot. Matching the updated snapshot
  only establishes byte equality to that snapshot. A comparison must name
  its independent source/commit baseline; ZIP self-declarations cannot
  identify provenance, freshness or the reason for a difference.
- CRLF checkout sources normalize to LF, as the existing builder does.
  Independently rehashed CRLF ZIP member bytes remain byte-different from
  canonical LF references, even though internal hashes are valid. No source
  rewriting or newline conversion of arbitrary ZIP code is performed.
- Case-changed member inventories, nonliteral source paths, unknown roots
  and sources fail closed. Exact allowlist matching is intentional on both
  case-sensitive and case-insensitive hosts.
- A symlink parent that escapes the fixed root is rejected before opening
  the source. The test patches Path.open to fail if attempted. Platforms
  unable to create symlinks explicitly skip that case, never count it as
  proof of protection on that platform.

Local Python 3.12.14: four new tests passed (no skips); combined R10/R11
source-reference suite: 12 passed. Existing seven recipe positives, ZIP
16MiB/member 2MiB/64-member bounds and official synthetic validator remain
unchanged. CI evidence is recorded by exact HEAD in the separate benchmark.
No source paths/payloads enter comparison output. Equality never establishes
authenticity, owner consent, SPDX, redistribution, official validation or
release permission. Extension release remains blocked.

Initial Windows 3.11/3.13 CI failed in the new synthetic-root fixture: the
patched fixed root was not canonicalized, unlike R10 FIXED_REPO_ROOT. Resolve
the synthetic root before binding it (including Windows temporary-directory
short-name aliases); do not weaken allowlist or escape rejection. Corrected
HEAD evidence is recorded separately; initial failure is retained for timing.
