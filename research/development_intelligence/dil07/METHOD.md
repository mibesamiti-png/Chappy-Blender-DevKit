# DIL-07 — public CBDK documents: frozen retrieval transfer test

2026-11-11 JST. Preregistered *before evaluating the 15 queries*.

## Question
Does the successful DIL-04 **synthetic** metadata-first/FTS5-fallback search still retrieve all essential evidence when applied to real public CBDK documents, particularly old-vs-new assignments and policy scope?

## Fixed input, authority and exclusions

- Exact public development commit `2b8220210c2475239a43354d544b5a6f176fba80` (not `main`, not current HEAD on future reruns), 12 source files and their Git blob SHA in `manifest.json`.
- 11 source files are eligible *for this experiment's current-assignment role*. `docs/R15_ABCD_START.md` is an **historical**, deliberately excluded *current-assignment* negative; it remains useful valid history, not misinformation or an invalid file.
- `cases.json` contains 15 authored questions and preselected mandatory evidence document IDs plus literal phrases, all fixed before the first evaluation. Nine have manually supplied topic tags, six do not. The same experimenter selected labels and queries; **no independent human blind gold**.
- A document counts as found only when the selected output includes the exact gold source ID *and* its preregistered verbatim anchor was confirmed present in the pinned source. No natural-language answer generation or question-to-topic classification is evaluated.
- Exclude private user assets, PR #114 research inputs, unmerged PR #115 research code as policy source, external web knowledge, or unstated approvals.

## Locked arms

Use the **unmodified DIL-04 retrieval.py** via local import, with a declared compatibility metadata wrapper (synthetic fixture fields `status=approved`, `visibility=public_synthetic` only for passing its existing `_live` predicate; these are algorithm flags and do not assert the source is synthetic or a product/license approval). Source body remains byte exact; source URLs pin the commit.

- `all_context` negative control: all 12 public docs, including old R15; high recall but stale assignment.
- `metadata_only`: original DIL-04 exact topic routing.
- `fts5_trigram`: original DIL-04 SQLite full-text search, no supplied topics.
- `hybrid`: DIL-04 metadata when tags provided, else FTS5.
- For consistent set-comparison, `max_docs=12`, so BM25 ordering does not silently truncate eligible docs. No ranking or context-window optimization claim.

Metrics: exact doc-set answers, gold documents found/total, missing-evidence cases, instances of historical R15 returned, bytes of serialized verbatim DIL-04 bundles, absent required anchors, output documentation SHA/URL provenance. Full-context bytes are an intentionally weak control; the 12-source corpus is not every CBDK document. Calculate `hybrid/all_context` bytes, **not tokens, cost or productivity**. Diagnose whether manually tagged vs freeform questions differ.

Safety gates: **zero** automatic merge/CI skip/privilege grant, do not treat missing matched documents as unrestricted permission; every partial/empty retrieval is `needs_authoritative_source`, including if it is caused by query mismatch. Strong transfer success would require full 15/15 doc-gold recall, 0 historical R15 and <=25% input bytes; otherwise label DIL-04 transfer **FAILED / not ready** and keep frozen evidence unchanged. Success also does not prove autonomous answer accuracy.

## Reproduction

Python 3.11+, stdlib SQLite FTS5 trigram, repo checkout containing the pinned source commit (fetch that SHA if needed), no network or model needed after checkout. `snapshot.py` reads `git show PIN:path`, independently rehashes Git blobs and refuses mismatch; `evaluate.py` imports DIL-04 code verbatim. `test_field.py` tests invalid SHA/anchor, stale exclusion, FTS absence, correct freeze and artifact fail-closed. `FREEZE.json` records hashes before the **one first** evaluation. `results/first-pass.json` is immutable first outcome. No post-holdout tuning; do not change the frozen script or cases to make the same experiment pass.

## Boundaries

Not real human query data; the author also wrote labels; a small, nonrandom, nonblinded question set. Correct doc-set membership does not prove all implicit safety constraints are captured. Timestamp freshness of arbitrary HEAD, genuine GitHub auth, a model answering correctly, FTS indexing/update cost, Windows performance, tokens, and actual developer time are out of scope. No ABCD/A/GIT actions, CI changes, automated scheduler, or production adoption.
