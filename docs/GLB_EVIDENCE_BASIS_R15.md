# Team B R15 — safe declared-basis review for anonymous GLB evidence

**Formal task:** GLB NEXT-008/GLB-021; `docs/R15_ABCD_START.md` after A's R15 milestone. Latest development branch at start `492b6d83e81de7c5283e70d4da55f58f8a598530`, descended from R14 A integration `db25585342e19e629fc32e2cc94ceae5d2e3d7b4`. R14 combined [PR #117](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/117) and A's formal R15 milestone already merged; baseline's independent **seven workflow families** successful. Historical specialist B R14 [PR #107](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/107) is already represented in the combined code, **not** separately merged.

## Use case

R14's `build_glb_evidence_triage(...)` summarizes metadata differences,
silhouette IoU, boundary-count audit, sampled surface distance and AST
candidate families in anonymous form, but does not link their original
measurement sessions. R15 adds
`cbdk.glb_evidence_basis_r15.build_bound_glb_evidence_triage(...)`.
It calls the unchanged R14 validator first, then separately reviews **small
caller-supplied declarations** about the inputs' measurement basis. The
caller still has to establish provenance outside CBDK before trusting a
measurement association. No existing GLB report contains a generally
authenticated same-run identifier; R15 neither invents one nor derives
one from raw private geometry.

The new function accepts the same five optional R14 source reports plus
`source_basis` (a dictionary keyed by supplied original source, not R14
derived channels) and `expected_basis` (a single caller-declared reference):

```python
from cbdk.glb_evidence_basis_r15 import build_bound_glb_evidence_triage

# Fake self-authored constants only. NEVER use raw GLB paths/coordinates.
basis = {
    "session_token": "a" * 32,     # opaque 32-char lowercase hex declaration
    "trial_token": "c" * 16,       # opaque 16-char lowercase hex declaration
    "baseline_digest": "b" * 64,  # declared basis digest, not authentication
    "revision": 4,                # locally declared positive revision number
}
result = build_bound_glb_evidence_triage(
    comparison=comparison_report,
    boundary_reference=reference_audit,
    boundary_candidate=candidate_audit,
    sampled_surface=surface_report,
    source_basis={
        "comparison": basis,
        "boundary_reference": basis,
        "boundary_candidate": basis,
        "sampled_surface": basis,
    },
    expected_basis=basis,
)
assert result["basis_review"]["status"] == "declared_consistent_unverified"
assert result["basis_review"]["sources_verified_same_run"] is False
```

**Important:** Even `declared_consistent_unverified` is **not** a claim that
two reports came from one experiment. Neither tokens nor digests are
authenticated or bound to original report contents by this function.
Hashes do not prove part geometry, true holes, original author consent,
source licensing, code safety or authority to edit/release.

## Three conservative outcomes

- `declared_consistent_unverified`: an expected declaration was supplied,
  all declared present reports agree with its session/trial/baseline/revision,
  at least two original report sources exist, and, where both are available,
  the boundary and sampled surface triangle counts agree. **Only declaration
  consistency**, not independent same-run verification.
- `conflict`: any asserted session/trial/baseline/revision disagreement,
  stale or unexpected revision relative to the caller's declared reference,
  or contradicting reference/candidate triangle counts between bounded
  boundary audit and measured surface report. Reason codes:
  `triangle_count_conflict`, `session_conflict`, `trial_conflict`,
  `baseline_conflict`, `stale_revision`, `unexpected_revision`.
  Multiple reasons are returned in stable order; no submitted value is
  copied into the result.
- `unknown`: absent expected basis, missing source declarations or fewer
  than two independent original source reports. Reason codes:
  `missing_expected_basis`, `missing_basis`,
  `insufficient_independent_sources`. Unknown is not presumed consistent.
  Even if all source declarations match one another, the absence of
  an explicit expected reference remains `unknown`.

`revision` is an explicit, bounded integer sequence (1..1,000,000), not
wall-clock time or evidence of freshness. A source with revision less
than the declared reference is labeled `stale_revision`; a greater
revision is `unexpected_revision`. With an outdated *reference* matching
an outdated set, the result is still merely `declared_consistent_unverified`.
The caller must independently obtain a fresh expected basis.

The five input names are fixed: `comparison`, `boundary_reference`,
`boundary_candidate`, `sampled_surface`, `static_property_triage`.
No declaration for an absent input is allowed. A missing declaration for
a present input remains explicitly unknown; it never silently inherits
another report's identity. Both boundary audits have independent basis
entries because they may have come from different source runs.

**Additional objective check:** When both boundary audits and a measured
CBDK sampled surface report are provided, their anonymous reference and
candidate triangle totals must match. This can **disprove** one claimed
combination, but equal totals cannot **prove** two model identities.
A deliberately skipped surface stays unmeasured, never equivalent;
missing reports are not silently inferred. Existing R14 strict validation
rejects malformed or inconsistent source reports first.

## R15 regression scope

`tests/test_glb_evidence_basis_r15.py` exercises eleven CBDK-authored
unittest methods: R14's four independent synthetic geometry conditions,
same declared basis, mixed trial, mixed session, changed baseline digest,
stale and future revisions, missing reference or record, single/zero
source, intentionally mixed anonymous mesh counts despite equal tokens,
private AST candidate counts, Boolean/NaN/malformed/extra basis rejection,
semantic report forgery, deterministic output, immutable inputs and
no private labels or digests in the result.

`tests/test_glb_regression.py` adds a mocked-IO facade control ensuring
an apparent basis agreement cannot flip a missing-part GLB comparison
to passed. It is an existing trigger for native Blender
4.4.3/4.5.15/5.2.1 smoke; the **new R15 4-shape/provenance tests run in
Python only**, not newly exported Blender R15 GLB fixtures. Common CI and
Blender scripts belong to A, are unchanged by B.

The bounded count check uses the pre-existing 512-triangle/64-part
limits from R14's source validators. Existing R2/R3/R8/R13 matching,
257-edge guard, review-only flags and R14 output schema are **unchanged**.
All R15 output safety and authenticity assertions are false. The R15
function neither executes code nor reads files or writes a report.
Original input paths, source labels, model names, mesh coordinates and
opaque declared tokens are never serialized or logged.

## Acceptance and limitations

For the exact final R15 specialist SHA, independently verify GitHub Actions
Python3.11/3.12/3.13, Windows PowerShell3.11/3.13, Blender4.4.3/4.5.15/5.2.1,
Chromium offline, Handoff and new-test actual job logs. Kit/Skill count only
if triggered. A's combined R15 SHA (5 CI families) and actual post-merge
developer SHA (7 CI families) require **separate** verification; the
R15 base HEAD green does not substitute.

No cross-report authenticity, same-run verification, cryptographically
trusted collection, real private GLB performance, Windows GUI/Undo,
small hole/exact solid proof, part identity or source-code causality is
established. No license, official Extension/Pages release, public v0.18 or
v0.19 activation is approved. No research PR #114/#115 or other teams'
changes are imported. STATE/HANDOFF/PROGRESS/Notion, main and shared
CI/scripts remain A-owned.

**R16 candidate (design only):** A-approved local-only, auditable
*measurement manifest* that binds one review to its own session, run
revision and validated count summaries before aggregation. Test
time-of-check/time-of-use stale-manifest and deliberate self-hash
replay attacks; never promote self-asserted hashes to authenticity
or export private paths. Requires explicit A allocation and fresh
integrated base; no R16 branch/PR under R15.
