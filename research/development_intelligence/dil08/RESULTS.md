# DIL-08 — first complete public-corpus SQLite FTS5 field run (frozen evidence)

**2026-11-11 JST. Experimental limited pass on manually tagged questions; NO production adoption.**

## Independent execution evidence

- Run: [isolated, branch-only GitHub Actions #42963844005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42963844005), successful 2026-11-11 05:09 UTC, job `130336376861`, workflow commit `0eb01b07e954d7af268679952fc1cd182ace7afd`.
- Separate temporary branch `research/dil08-field-once-20261111` hosts the one-shot workflow, **not** the formal development branch or shared ABCD CI. The workflow fetched the pinned source commit and used the existing frozen `dil08/evaluate.py` / unmodified DIL-04 `retrieval.py`.
- Pinned public source commit `2b8220210c2475239a43354d544b5a6f176fba80`. 12 exact-source Git objects, 12 researcher-authored new operational scenarios. Additional 15 **already-seen** DIL-07 development questions were evaluated separately. Code/test/method SHA256 recorded in `FREEZE.json` **before** the execution; source loader checked Git blob SHA and refused mismatches.
- 35/35 unittest passed in the workflow. Runner Python 3.14.4, SQLite 3.46.1, FTS5 trigram available.
- **Full, byte-identical 70,410-byte JSON first-run report:** [`results/first-full-sqlite.json.gz`](results/first-full-sqlite.json.gz), committed as binary gzip. Decompress with `gzip -dc results/first-full-sqlite.json.gz > /tmp/dil08-first-full-sqlite.json`. Original uncompressed JSON SHA256 `1737d575f74f9b3b6bbe21880ca44309addad187eab942d62e269c836d310b0f`; deterministic gzip SHA256 `5f2b2e2292e89802601e58cc5cac70c51fe2dd9c4ae31993ef4f3b23115fc72f`.
- Original [GitHub Actions artifact](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42963844005) retained by GitHub for 30 days, artifact `13829499102`, ZIP digest `sha256:4326b46b185cfd9972950b39b450a056853f3ee2c7405a2a8074ecbe01134ea2`. Committed gzip above is the durable record.

## First-run metrics (12 preregistered operational scenarios)

| Same original text serialization | Found required sources /37 | Exact sets /12 | R15 returned in action context | Required action evidence missing cases | Input UTF-8 bytes |
|---|---:|---:|---:|---:|---:|
| Full context negative control | 37/37 | 0/12 | 8 | 0 | 3,165,264 |
| Frozen DIL-04 hybrid, **real SQLite FTS5** | 10/37 | 4/12 | 0 | 8 | 146,299 |
| **DIL-08 authority-first tagged selector** | **37/37** | **7/12** | **0** | **0** | **1,478,704** |

- Candidate/full ratio **46.71660878839806%** (reduction **53.28339121160194%**). This is input **UTF-8 bytes**, not real LLM tokens, API price, prompt completeness, latency or developer effort.
- Mandatory action documents **29/29**, other required evidence **8/8**. No historical R15 selected as *current*.
- Precommitted thresholds: no unsafe permissions/CI bypass, no R15-as-current, all required action evidence, >=95% additional evidence, <=50% all-context bytes. **All test-level gates passed**, so the run's `limited_field_pass=true` label is accurate for this test.
- **Caution:** `no_unsafe_automation=true` is structurally true because this read-only selector **never grants any action permission**; this experiment does NOT test real agent compliance with user instruction or detect hidden semantic permissions.
- Unnecessary documents remain for 5/12 questions. Their full original text is included, not summary excerpts. Byte reduction comes with retrieval/routing assumptions, not a validated whole-system token saving.

## Crucial negative result: 15 previously seen freeform development questions

| Arm | Required evidence found | Exact sets | Input bytes |
|---|---:|---:|---:|
| All-context | 16/16 | 0/15 | 3,956,580 |
| DIL-04 hybrid (SQLite) | **11/16** | 9/15 | 447,237 |
| DIL-08 selector | **10/16** | 6/15 | 346,789 |

DIL-08 was not better on these freer-form queries. Six missing required documents show that **manual intent/topic metadata and real free-text classification are a separate, unsolved gate**. The old DIL-07 source-text proxy was not the real SQLite result; these rows supersede its approximate literal-match claims on this fixed corpus.

## Limitations and decision

All 12 new scenarios were authored and labeled by the same researcher (no independent blind gold); structured task intents/topics were **supplied manually**. A source-ID hit is not proof that an LLM uses the evidence properly. `source_commit` pins past evidence, **not** present-day dev HEAD, Issue #125 revision, valid CI, actual user permissions, or readiness for R17/v0.19. The source corpus is only 12 chosen public documents; full context is a deliberately costly negative control. No live Blender runtime, no model inference, no cross-project transfer, no real user workload, no repeat performance measurement.

**Decision:** accept DIL-08 as a *limited field-search experiment only*. Do **not** merge into ABCD, enable automatic role assignment, loosen permission/CI checks, or mark a product feature complete. Preserve PR #115 Draft/unmerged. Next research should address freeform intent classification and wrong-tag negative examples in a newly frozen DIL-09 dataset, ideally with independent review. Do not retune DIL-08 frozen scenarios after seeing this outcome.
