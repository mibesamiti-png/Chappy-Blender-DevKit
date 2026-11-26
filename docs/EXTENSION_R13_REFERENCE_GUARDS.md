# R13 D — pinned inventory and filesystem alias guards

R13 work is a **synthetic test-only reference review**, not a new production trust, signing, or release API. It is based on the latest v0.18 development branch after A's merged #99 formal allocation. Changes stay inside Extensions tests/docs; B's PR #100, shared scripts/CI/STATE/Handoff/Notion and main are untouched.

## Frozen reference basis

The R12 descriptor combines a 40-character commit, normalization policy, and digest of a known reference inventory. R13 checks an **independently frozen descriptor** against both the caller's presented descriptor and the bounded reference bytes **before reading the ZIP**. Identical commit identifiers with divergent inventories or policies must return `inconclusive_reference_basis`, never `same_known_repo_bytes`. An unknown/extra field, malformed basis or oversized inventory similarly fails closed. The independent basis itself is still a *test observation*, not a signed origin or permission to ship.

## Path aliases and read stability

The test-only reader accepts only exact names from the fixed CBDK repository-owned `SOURCES`, `HELPERS` and `TRUSTED_FEATURES` allowlist, a separately pinned checkout root, and small regular files. It rejects unknown roots, source case/8.3-looking aliases, traversal paths, leaf symlinks, source parent symlinks, **requested-root ancestor symlinks/junctions** and Windows reparse/junction components **before any content open**. The requested-root ancestor guard is intentionally separate from allowing canonical Windows root case/8.3 spellings when none of their actual path components is a reparse point. Rejected paths are tested with `os.open` intercepted so unauthorized **content opens = 0** in those controlled fixtures.

On Windows, an alternate **root spelling** via case changes or actual 8.3 short name may be accepted only if it resolves to the identical pinned root, is not itself a reparse point, and requests the same exact allowlisted relative source name. The Windows-native junction, root case and 8.3 probes distinguish executed checks from unavailable capabilities/explicit skips. Linux never asserts that Windows native behavior was exercised.

On accepted paths the reader enforces the existing 2 MiB file limit, checks metadata before opening, checks the actual open handle, reads at most 2 MiB+1, and checks metadata again after reading. A deterministic change between read and final metadata verification must return `inconclusive_reference_changed` **without returning source data**. Stable CRLF is normalized to LF as in existing build logic; original source bytes remain unchanged.

This is a **bounded synthetic interleaving** test. It does not prove absolute freedom from simultaneous hostile directory swaps, deliberate timestamp restoration, or all Windows reparse behaviors. Such a public API would need a separate OS-level handle security review. No production source-reference reader is created or advertised.

## Release and regression limits

Only safe status names and bounded counts are exposed, without paths, source contents, synthetic private markers, unknown names or license data. All source-authenticity, owner consent, licensing, redistribution, signing, code execution, official real-package validation and release authorization indicators remain false.

The seven CBDK-authored preview ZIP positives, 16 MiB archive / 2 MiB member / 64 member limits, R9 self-rehashed negative cases and existing three-version Blender official validator **six data-only synthetic** fixtures remain required. No private/user addon Python is imported, installed, executed or published. `EXT-001` stays partial. This design doc is not CI evidence; final verified CI and any capability skips belong to the R13 draft PR.

## Windows clock compatibility correction (A, 2026-11-26)

Windows Python 3.12/3.13 can expose creation time through path stat ctime
and metadata change time through descriptor fstat ctime. These are not
equivalent clocks. The test-only fingerprint compares birthtime_ns on
Windows when available, with legacy ctime_ns fallback; POSIX retains
ctime_ns. Path checks, size/identity/mtime comparisons, bounds and prior
test expectations remain unchanged. This is not a production reader or
a new guarantee against hostile timestamp restoration or all metadata
changes.

Independent diagnostic branch `work/a-r13-observation-20261126`:
- [Initial reproduction](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45837112669):
  Python 3.13 focused 59/60, one false refusal before the mutation callback
  due exclusively to ctime_ns; Python 3.11 focused 60/60.
- [Win32 FileBasicInfo comparison](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45839415722):
  40 observations per interpreter; native mapping confirmed for 3.11.9
  and 3.13.17. One natural 15.6168 ms clock difference in 20 fresh
  3.13 files, 20/20 deliberately separated-clock files reproduced it.
- [Repair comparison and regression](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45840533624):
  old reader met 100/300 scenario expectations (newer Windows readers
  refused before mutation, not an unsafe acceptance); corrected reader
  met 300/300, including 240 actual mutation detections with no returned
  bytes. Windows 3.11/3.12/3.13 focused 180/180; full suite 1370 tests
  per environment (Windows 16 skips each, Linux 3.13 7 skips), no failures.
  This evidence belongs to research commit `f4538b0ad31a802b42b698c5b267ff48887bd831`,
  which includes the separate integration candidate, not this dev-based PR.
  The exact corrected test-file blob is reused.

Source audit:
[CPython v3.13.17 path stat](https://github.com/python/cpython/blob/v3.13.17/Modules/posixmodule.c#L2218-L2228),
[descriptor clock mapping](https://github.com/python/cpython/blob/v3.13.17/Python/fileutils.c#L1139-L1143),
[Python 3.11 legacy mapping](https://github.com/python/cpython/blob/v3.11.9/Python/fileutils.c#L1089-L1093).

The Work host's separate changed-source failure has not been independently
reproduced there. The demonstrated early false refusal may explain it
but the original detailed failure log remains unavailable. Do not claim
that all possible R13 races or the integration candidate are certified.
