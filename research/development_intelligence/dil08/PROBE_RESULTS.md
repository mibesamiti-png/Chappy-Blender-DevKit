# DIL-08 — first post-freeze metadata source probe (secondary, exploratory)

2026-11-11 JST. This **is not** the preregistered actual full-corpus SQLite comparison. The primary DIL-08 experiment remains **unscored** until a local checkout containing the pinned Git objects can run `evaluate.py`. Do not transfer this score into a production claim or claim a DIL-04 SQLite comparison happened.

## Evidence and integrity

- Preregistered METHOD, tag catalog, 12 authored scenarios and offline selector/evaluator frozen at research commit `e8a74c327dc146952c338fa066ab5dd01ab2aa6a` in `FREEZE.json`, **before this first metadata-only source-probe score**.
- Source metadata: DIL-07 `observed_matrix.json`, previously obtained from twelve exact public CBDK documents at dev commit `2b8220210c2475239a43354d544b5a6f176fba80` with confirmed blob IDs and registered literal anchors. This probe **did not re-fetch or read the source bodies** and does not re-verify the bodies by itself.
- Candidate selection: same 12 manually authored DIL-08 scenarios, known document tags, read-only `selector.py` selection logic. No AI intent classification. Document byte lengths come from prior DIL-07 serialized evidence observations and are **approximately** summed for list punctuation; these are not tokens or measured runtime context traffic.
- Offline tests in this work session: **35/35 unit tests passed** using synthetic fixtures and a local SQLite FTS5 trigram smoke test. This does not prove complete public-corpus SQLite accuracy.

## Secondary source-probe measurements

| Metric | Observed in metadata probe |
| --- | ---: |
| Fixed operational scenarios | 12 |
| All mandatory/optional evidence, pooled | **37/37** |
| Mandatory action evidence | **29/29** |
| Additional task evidence | **8/8** |
| Exact required document sets (no extras) | **7/12** |
| R15 selected as current instruction | **0** |
| Approximate candidate serialized bytes | **1,478,704** |
| Approximate full 12-document input bytes | **3,165,264** |
| Candidate/full ratio | **46.72%** (53.28% smaller) |

The 7/12 exact-set result shows that the broad topic mapping often returns extra documents. The 37/37 shows *no missing hand-labeled document IDs in these 12 structured scenarios*, not that a downstream assistant would correctly interpret them. The authority-first candidate cannot independently verify a live Issue #125, exact CI, user permission or actual task completion; it deliberately sets action permissions to false.

**Methodological caution:** Source selection and byte summation were evaluated through previously recorded metadata, not full SQLite text ranking. Comparing to the DIL-04 actual FTS5 arm remains **pending**. The 46.72% figure is not an exact savings estimate for a live AI prompt: provenance wrappers, prompt templates, tokenization, model response and indexing costs are not included.

## Decision and next checkpoint

**Partial research outcome only; operational adoption NOT APPROVED.** Continue only with the fixed `evaluate.py` against a local CBDK clone containing the source commit, and record its **first** complete real-SQLite run as a separate immutable JSON. Then obtain independent blind questions and real project HEAD/role/CI revision checks before asking A to trial it. No shared docs, CI policies, branches, product code or developer authority changed by DIL-08.
