# DIL-07 — real public CBDK retrieval: first evidence-backed source probe

2026-11-11 JST. **FAIL to transfer DIL-04's synthetic success to real CBDK documents. No product adoption, no production tool deployed.** This is a **source-content proxy assessment**, *not* the execution of the frozen DIL-04 SQLite FTS5 algorithm on the complete local repository*.

## Pre-registration & integrity

- Pre-registration already committed in research PR #115 at **`4f372a2e6519e921962ef0a854b5452be31cc8a2`** before inspecting any results for the 15 frozen evaluation cases. `METHOD.md`, `manifest.json`, `cases.json`, `snapshot.py`, `evaluate.py`, `test_field.py`, `FREEZE.json` fixed at this commit. Frozen scripts not retuned after probe.
- Actual **12 public source files** from v0.18 dev commit `2b8220210c2475239a43354d544b5a6f176fba80`; each returned GitHub blob SHA matched its preregistered `manifest.json` digest (12/12).
- All 16 declared document+anchor obligations in the 15 cases existed verbatim in the pinned source bodies. Same researcher wrote questions, topics and gold IDs; no blind or third-party label, real user query distribution or LLM answers.
- Eleven current-for-this-experiment documents, one archived **R15 as an outdated current-assignment signal only**. That R15 file is valid history; it is excluded only when selecting *current R16 instructions*.
- Local **12/12 Python tests** passed for SHA checks, invalid paths, gold rejection, stale exclusion, untagged FTS sample and unchanged DIL-04 engine blob `6d2ab052ff3ba40a16fb99288e82a0a646624c58`.

## Direct public-source probe and indicative scores

This pass collected 12 complete source bodies through the connected GitHub tool and computed exact source-text anchor presence, metadata topics, per-document DIL-04 bundle UTF-8 byte lengths and Unicode substring matches for the preregistered DIL-04 lexer's query terms. **This last step approximates FTS5 trigram quoted-phrase matching; it does not execute SQLite FTS5 on the complete real texts.** `max_docs=12` was locked, so no ranking truncation in the proxy. The reproducible Python/SQLite evaluator is supplied but **has not been run on a complete local clone in this environment**. Numbers here are labeled *source-probe*, not independently reproduced SQLite results.

| Arm | Exact doc sets /15 | Required docs /16 | Historical R15 appearances | Serialized bytes over 15 questions |
|---|---:|---:|---:|---:|
| All 12 documents, negative control | 0 | 16 | 15 | 3,956,580 |
| DIL-04 metadata-only (same topic routing) | 9 | 10 | 0 | 251,747 |
| DIL-04 FTS trigram **literal-match proxy** | 0 | 1 | 0 | 195,500 |
| DIL-04 hybrid **literal-match proxy** | **9** | **11** | **0** | **447,232** |

- Hybrid/source-all byte ratio **11.30%**: **88.70% lower input bytes**. No token counts, inference cost or observed ChatGPT usage.
- Crucially, hybrid/source-probe misses **5/16** required document instances, so it is **not ready for automatic CBDK instructions** even though the byte threshold was met. Missing on Q02, Q03, Q05, Q08 and Q14 (free-form long or paraphrased Japanese queries). Q11 retrieved UI evidence *and 3 unrelated but current documents*, so it has an exact-set false positive despite mandatory evidence being present.
- In this fixed 15-question set, 9 manually topic-tagged cases find their required 10 document instances; among 6 untagged cases, only Q11 found its required document. This strongly suggests the synthetic DIL-04 test benefited from structured topic labels. It does not establish the true error rate in users' questions.
- All-context contains historical R15 at every turn; selective methods exclude it as a *current assignment*. Neither approach independently proves that the current round is live and approved. Missing search results must mean **"insufficient source evidence"**, not "permission granted".

## Why this matters / hard limitations

- Example risk: a natural prompt asking whether R16 can start cannot be safely resolved from an empty FTS result; formal R16 assignment and current CI gates must be loaded independently.
- Metadata-only can be very precise if someone or a validated system supplies the topic, but this study did **not** measure the real effort/error of that classification.
- `docs/project/STATE.json` is large; including it alone for the tagged state question consumes a substantial fraction of retrieved bytes. Compression into chunks risks omitting dependencies. This experiment does not test safe chunking or natural-language summarization.
- GitHub blob SHA confirms pinned source identity, **not** that a developer has permission to use private assets or that a documented feature is complete, approved, or safe. Dev HEAD can change after this recorded commit.
- This source probe does not prove the exact SQLite case-level return sets or token savings. The frozen `evaluate.py` is provided for later authoritative full-corpus SQLite reproduction (and will fail closed if Git objects or blob hashes differ); no post-hoc edits to the preregistered questions are permitted.
- No modification to A-owned rules, common CI, shared STATE/HANDOFF, ABCD branches, Geometry Lab, or main. No model inference, merge, CI skip, external process monitor or reviewer assignments.

## Artifacts / reproduction

- `METHOD.md`, `manifest.json`, `cases.json`, `FREEZE.json`: immutable preregistration.
- `snapshot.py`: source git objects via `git show SHA:path`; verifies independent `git blob SHA1` before reading.
- `evaluate.py`: genuine DIL-04 `retrieval.py` imported unchanged; refuses freeze violation; source-backed Python/SQLite *not yet executed in this environment*.
- `observed_matrix.json`, `evaluate_probe.py`, `results/first-source-probe.json`: first bounded GitHub-connected textual probe, clear proxy labeling and per-case outcomes.
- `test_field.py`: locally executed unit tests.

To reproduce complete FTS via original engine on a local repository with the source commit available:

```sh
cd research/development_intelligence/dil07
python -m unittest -v test_field
python evaluate.py --repo /path/to/Chappy-Blender-DevKit --output runs/first-local-sqlite-result.json
```

The source commit must be fetched into that git repository before execution; output uses exclusive creation and does not replace any original first-pass evidence.

## Decision

**No transfer/adoption approval.** Real document coverage under natural-language queries is incomplete in the first source probe; seek a separately preregistered follow-up with authority-first routing, source-version classification, **genuine** SQLite field execution, and independently reviewed blind questions *before* considering operational use. Do not ask A to do extra review or collect telemetry automatically. Keep DIL PR #115 Draft/unmerged.
