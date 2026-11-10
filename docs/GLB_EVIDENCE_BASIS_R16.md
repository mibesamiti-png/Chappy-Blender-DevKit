# Team B R16 — Limits of self-declared GLB measurement provenance

**Formal task:** `docs/R16_ABCD_START.md`, B GLB NEXT-008 / GLB-021, P1.

**Starting gate:** A R15 combined PR #122 and formal R16 milestone PR #123 are merged into
`feature/v0.18-shape-diagnostics`. Fresh branch base
`3f425212c560043a43ca092443e390cf57d82ae3`, whose independent
Python, Windows, Blender (4.4.3/4.5.15/5.2.1), Chromium, Handoff, Kit,
and Skill CI workflow families all ended `success` before R16 work began.
Historical individual B R15 #120 is already represented in the combined
dev code; **do not merge it again**.

## Decision: tests and documentation only

R15 introduced the bounded in-memory
`build_bound_glb_evidence_triage(...)` API. It accepts independent
existing anonymized reports and **untrusted** `source_basis` /
`expected_basis` declarations. It uses three values:

- `declared_consistent_unverified`: only the caller's declarations agree
  with its chosen reference, and available aggregate triangle counts do
  not contradict one another. This is *not* independently verified
  authenticity or even proof of same-run source.
- `conflict`: a declared session, trial, baseline digest or revision
  differs, or audit and measured surface triangle counts visibly disagree.
- `unknown`: a missing reference, absent required declarations or too
  few actual source reports. All outer results stay `review_only`.

R16's key question was whether we could reliably detect reuse, fake
declarations, or a replayed old run from these **self-declared fields
alone**. The answer is **no**. A malicious or mistaken producer can
repeat exactly the same session/trial/baseline/revision fields across
different report contents. Hash *matching* is not independent content
binding, permission to edit, a copyright/license authorization,
nor authentication of origin. R15's own result explicitly sets
`claims_bound_to_report_content=false` and
`sources_verified_same_run=false`; no trusted provenance source
exists in this specialized task to change that honestly.

Accordingly, **R16 deliberately does not add a manifest feature,
change R15's existing status labels, introduce a "verified" flag,
or change production matching algorithms**. Focused synthetic
counterexamples are a more useful and safer outcome.

## Ten synthetic regressions

`tests/test_glb_evidence_basis_r16.py` imports previously CBDK-authored
R14/R15 tiny geometry fixtures; its tokens are fixed invented hexadecimal
test values, not asset fingerprints. Tests cover:

1. **Replay of identical declarations and report:** stable output,
   all authenticity/authorization proof flags false, no mutation.
2. **Old revision reused as both source and expected:** declaration
   agreement is still possible, even though freshness is unproven.
   Comparing old revision against separately supplied newer expected
   revision produces `stale_revision`, which remains only an
   assertion-relative conflict, not independently trusted recency.
3. **Valid report substitution with equal face counts:** replace one
   input channel at a time with a separately generated moved-opening
   example, retaining identical invented basis claims. Such a mixture
   can still return `declared_consistent_unverified`: **explicitly
   demonstrates the detector's limit**, never a successful same-run proof.
4. **Cross-batch mixture with equal triangle counts:** independently
   authored displacement, opening and identical samples combined into
   one view, all original basis records reused. No false authenticity.
5. **Distinct self-declared trial/session/baseline and lower revision:**
   stable anonymous `session_conflict`, `trial_conflict`,
   `baseline_conflict` and `stale_revision` reason codes.
6. **Unanchored or missing source declarations:** `unknown` and
   corresponding explicit `missing_expected_basis`/`missing_basis`.
7. **Absent source/one reported item:** `unknown`; fabricated
   basis record for an absent report fails closed.
8. **A skipped over-limit Blender sampled surface:** remains
   `not_measured` even if its caller basis matches.
9. **Contradictory actual aggregate triangle counts:** conflict even
   when self-claimed tokens match; equal triangle counts in a
   different fixture still establish no identity.
10. **Privacy and deterministic output:** fake secret model names,
    source paths and opaque tokens never appear in returned
    aggregate JSON, and no report input is modified.

Each returned report and inner R14 summary must remain
`review_only`. Tests check `authenticates_evidence=false`,
`proves_identity=false`, `auto_applies=false`, and R15's
`sources_verified_same_run=false`,
`hash_equality_authorizes_edits=false`, etc.

Tests exclusively use in-memory, self-authored synthetic metadata,
boundary audits and sampled surface distance; they do **not** execute
Blender or external addon code, export original GLBs, inspect or
publish any real/private geometry, or copy user identifiers. The
existing native Blender workflow is checked separately for regression
of pre-existing GLB fixtures; its successful execution cannot
establish that R16 provenance scenarios ran in Blender.

## Safety and gates

- **Code delta:** only B-owned `tests/test_glb_evidence_basis_r16.py`
  and `docs/GLB_EVIDENCE_BASIS_R16.md`; no new `cbdk/glb_*` API.
- R2/R3/R8/R13 matching, R14/R15 validators and their `unknown`,
  `review_only`, 256-edge, 512-triangle and 64-part limits remain
  untouched. Hash agreement can never prove geometry, hole location
  or source code behavior.
- The R16 B Draft PR requires **exact final SHA** Python 3.11/3.12/3.13
  (including ten new tests), Windows PowerShell 3.11/3.13,
  Blender 4.4.3/4.5.15/5.2.1, Chromium, and Handoff workflows.
  Kit and Skill must not be claimed unless separately triggered on
  the same SHA. A's combined R16 SHA must pass its own 5 CI and
  once-only dev merge SHA must pass a new independent 7 CI.
- STATE/HANDOFF/PROGRESS/Notion, shared CI/scripts, team C/D,
  Geometry Lab #114, Development Intelligence Lab #115, historical
  R15 specialist PRs, `main`, v0.17.0 and official release/
  publishing permissions are A- or separately-owned and unchanged.

**Not verified:** real GLB provenance, token/key generation process,
trusted measurement session, TOCTOU or off-host replay prevention,
real Windows GUI/Undo, exact topology/holes/part identity, source
license, author consent or official Blender Extensions publication.
Even repeated matching digest observations alone cannot prove
current safety, provenance or edit authority.

**R17 design candidate only:** After a separate A-controlled scope
decision, explore a locally trusted *external measurement collector*
that binds report bytes to session/batch metadata, rejects read-time
changes and rechecks in-memory snapshots. Test forged self-hash,
replayed collector output, swapped same-size report contents and
absent trusted prior state. Do not store user paths/model geometry in
portable/public reports, treat a digest as a legal/identity proof,
or create an R17 PR before the next formal gate.
