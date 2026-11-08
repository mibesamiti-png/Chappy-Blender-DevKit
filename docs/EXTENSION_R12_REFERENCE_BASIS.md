# R12 D — explicit reference basis and canonical filesystem fixtures

Base: `faab6ab023f50495c719d091b29f320aa6ab36df` (unchanged R11 candidate).
Only D tests/docs. No new production trust API or release permission.

A test-only descriptor records an independent source commit, a bounded known
inventory digest and explicit checkout-CRLF→LF / ZIP-exact comparison policy.
Unknown/changed basis produces inconclusive_reference_basis, not authenticity
or a cause for mismatch. Legitimate source updates and rehashed ZIP edits are
indistinguishable by byte mismatch alone. The R10 compare safety flags remain
false. Snapshots are observations, never author consent/SPDX/release evidence.

All synthetic roots are resolved before binding FIXED_REPO_ROOT. Tests cover
CRLF read normalization without source rewriting, unknown roots, literal
allowlist/case rejection, parent and leaf symlink escapes with Path.open
forbidden. Windows-only native probes cover junction escape and actual
GetShortPathNameW root alias plus root case alias. Short names disabled,
lookup/creation permissions unavailable are explicit skips, not validation.
Junction cleanup removes only the link, preserving the outside fixture.

Local Python 3.12.14: six new tests discovered; four passed and two Windows-only
probes skipped. Windows execution evidence is obtained from exact-HEAD CI;
Linux skips cannot prove Windows safety. Known seven ZIP recipe positives and
16MiB/2MiB/64-member bounds remain unchanged, as does the existing synthetic
Blender official-validator path. No packaged Python/private source is executed.
Final CI, actual per-host skips and timing are recorded in the R12 benchmark.
