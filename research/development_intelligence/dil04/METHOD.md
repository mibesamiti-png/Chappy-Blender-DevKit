# DIL-04 — Evidence retrieval with minimal input: preregistration

2026-11-11 JST. **Independent research, no production adoption, no official HANDOFF modifications.**

## Motivation / repository overlap

Existing formal STATE/HANDOFF and `scripts/project_handoff.py` remain owned by team A. PR #113 specifies provenance, license and review-only modeling know-how intake; it has no production search engine. DIL-04 *reads* these requirements but does not update them or treat draft research as formal truth. DIL-01's timestamp evidence, DIL-02's stop gate and DIL-03's cooperative writer experiment remain unchanged. The previous DIL-03 `QUEUE.md` selects DIL-04.

## Four comparable methods

All methods see the **same 40 synthetic documents** and 12 development / 12 unused test tasks, each with human-authored required evidence IDs. Sources are invented public-synthetic examples, not real user files or repo documents. No labels are extracted from retrieval outputs.

1. `all_context`: pass every document, including stale/out-of-project references (no omission but enormous input; negative control).
2. `metadata_only`: exact project+topic metadata, active approved records only; zero search dependency, but the caller must supply topic labels.
3. `fts5_trigram`: project/version-filtered SQLite FTS5 trigram, phrases from the query; handles Japanese substrings of >=3 characters but no semantic paraphrases.
4. `hybrid`: use cheap exact metadata when structured topics exist, otherwise fall back to FTS5 trigram; return **verbatim evidence** and source+revision instead of an AI summary.

Evaluation does **not** measure correctness of full-language answers, training or inference. Query topics are manually preclassified for some tasks and are not inferred by an AI. This is a deliberately narrow contrast; human labor to tag documents and queries is not counted, and this dataset is too small to establish large-index speed or quality.

## Fixed goal / metrics / thresholds / budget

Goal: retrieve each mandatory evidence document with source/version, avoid obsolete or other-project material, and shrink the amount of text supplied as a candidate AI input.

Metrics per method and split: exact-gold *set* matches, number of required documents retrieved vs number required, returned wrong-project documents, returned retired/unapproved documents, total serialized evidence bytes and median bytes per task. These bytes are **not AI tokens**, API cost or actual network bytes. No extrapolation to live production recall or hallucination rates.

**Accept a limited prototype only if**, on the unused 12 tasks: hybrid exact >=11/12; all required evidence found; 0 wrong-project and 0 retired/unapproved returned; input bytes <=25% of the unfiltered `all_context` baseline; hybrid exact improvement >=3 tasks over `metadata_only`; all 14 unit tests pass. If not, report fail/reject. We will not adjust code after first holdout evaluation.

Budget: 40 artificial documents with 8 projects × 4 topics (32 current + 8 retired), development 12, holdout 12, 14 focused unittest cases, 1 frozen benchmark (each method once per split) <=60 seconds, post-holdout tuning 0. Freeze SHA256 of code, corpus, development and holdout files, test source and METHOD **before first holdout execution**. Do not add higher-complexity embedding models or production adapters in this cycle.

## Boundaries / failure modes

- Selection is against caller-provided project, supplied topic tags or FTS phrase matches. Incorrect/missing caller metadata, alias mismatch, misspelled words, unregistered synonyms, new documents, index freshness and short Japanese 1-2-character queries can all fail. A missing evidence hit must not be represented as proof the policy does not exist.
- FTS5 trigram is a SQLite build-time feature; if unavailable, report that rather than claim fallback retrieval worked. The prototype regenerates a tiny in-memory index for each untagged query; this is **not** a scalable deployment design.
- Current-ness is determined by fixture flags, *not* by GitHub revision/CAS/source attestation. In real use, source and commit must be verified; status labels must never confer permission or secret access.
- Full-text snippets may omit dependencies outside the retrieved document. A real production answer must cross-check critical constraints and abstain on missing evidence. This experiment does not verify semantic completeness of a drafted summary.
- All documents are invented synthetic public examples; real CBDK handoffs, actual developer time, paid model tokens, user intervention, indexing/setup overhead, disk/RSS and privacy handling on real data are **not measured**.

## Reproducibility

Python 3.11+ with stdlib sqlite3 built with FTS5 trigram. No paid service, Astra, Codex, network or Blender needed. From directory `research/development_intelligence/dil04`:

```sh
python -m unittest -v test_retrieval
mkdir -p runs
python benchmark.py --output runs/new-result.json
```

Benchmark refuses any frozen source or fixture hash mismatch and uses an exclusive output path. `generate_fixtures.py` is documentation of fixture construction, not intended to run again after freeze.

Reference (capability, not a claim that this experiment is production-ready): <https://www.sqlite.org/fts5.html> (§4.3.4 trigram tokenizer).
