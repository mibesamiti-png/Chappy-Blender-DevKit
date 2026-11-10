# DIL-04 Results — minimal evidence retrieval with fallback

2026-11-11 JST. **Limited synthetic research passed; product adoption on hold.** All original DIL-01/02/03 files unchanged.

## Preregistration and environment

- Objective and pass/fail criteria were set in [METHOD.md](METHOD.md) before the holdout benchmark.
- 40 synthetic public documents: 8 projects × 4 active topics, plus 8 deliberately obsolete handoff records. No real user material, private source or production CBDK corpus.
- Development tasks: 12; unseen evaluation tasks: 12 (in the sense of no evaluation execution before freeze; the same researcher authored all gold). Needed documents: 15 per split.
- The eight designated source/fixture/method files were SHA256-frozen in [FREEZE.json](FREEZE.json) before the first holdout execution, and benchmark checks those hashes. Post-holdout tuning: **0**.
- Environment: Linux, Python 3.13.5, SQLite 3.46.1 with FTS5 trigram available. Python standard library only; no AI, paid tokens, network, Blender or Astra.
- 14 focused unittest cases passed locally; the benchmark ran once across 4 variants × 2 splits (benchmark wall clock 0.0191 seconds; this is **not** workflow/productivity speed). Full per-case outcomes in [results/dil04-first-run.json](results/dil04-first-run.json).

## Numeric comparison

**Exact-gold** means the returned document-ID *set* is exactly the manually specified required evidence set (no extra docs); full_context includes all evidence but thus has no exact-gold successes.

| Method | Dev exact /12 | Held-out exact /12 | Held-out required evidence | Held-out wrong-project returned | Held-out obsolete/unapproved returned | Held-out input bytes (total 12 cases) |
|---|---:|---:|---:|---:|---:|---:|
| Unfiltered full context (negative control) | 0 | 0 | 15/15 | 420 | 96 | 199,788 |
| Metadata topic filter | 8 | 6 | 9/15 | 0 | 0 | 4,199 |
| FTS5 trigram alone | 4 | 6 | 6/15 | 0 | 0 | 2,799 |
| **Metadata first, FTS fallback** | **12** | **12** | **15/15** | **0** | **0** | **6,974** |

- Hybrid reduction against all_context: **96.51% fewer UTF-8 bytes** (6,974 vs 199,788). This is **not** token count; the baseline includes intentionally irrelevant and retired text, not a measured CBDK handoff.
- Hybrid improved exact results over metadata_only by **6 cases** (12 vs 6). It used more bytes than metadata-only (6,974 vs 4,199) because metadata-only silently missed required evidence for the six untagged cases.
- Full-context retrieved 100% of the needed evidence but flooded every request with all 40 documents, including retired and cross-project material. Its 420/96 counts are occurrences across 12 tasks, not distinct files or actual data leaks.
- FTS5 only did not match many long Japanese questions; it is not an automatic semantic paraphrase solver. Hybrid chose the metadata index when explicit topic labels existed, falling back to trigram when only a query phrase existed.

**Pre-registered narrow acceptance reached:** held-out 12/12 >=11; 15/15 required evidence; 0 wrong-project/stale; 3.49% of unfiltered bytes (<25% budget); +6 exact cases vs metadata-only; 14/14 unittest. Stop at this point; do not further tune this dataset.

## Observed successes, negative findings and limitations

- Successful scope: evidence lookup using manually assigned project/topic fields, version/status filtering, fallback substring search for >=3-character phrases, returning source+revision with unmodified text. Minimal retrieval can lower input bytes without losing the manually identified evidence *in this synthetic dataset*.
- Negative finding: pure metadata lookup is cheaper and sufficient **when queries are fully and correctly tagged**; FTS adds little value then. Pure FTS underperforms on paraphrases/phrases; it cannot guarantee capture of a policy that uses different wording. Missing results should yield 'unknown', never 'no restriction exists'.
- **Not demonstrated:** AI interpretation of human requests into tags, real CBDK knowledge search, source authenticity or GitHub HEAD consistency, complete related constraints outside retrieved snippets, natural language answer correctness, production security, exact LLM tokens, billable usage, processing latency at scale, maintenance cost, human interventions and development speed.
- The corpus is deliberately regular: one approved record per project/topic, repeated text style, and a small controlled synonym set. The same researcher authored the gold and algorithm, so the 12/12 result cannot be generalized to actual technical research. Real workloads can have several applicable documents, conflicting versions, partial approvals or omitted critical dependencies.
- `retrieval.py` indexes an in-memory SQLite FTS table per lookup. No proof that this is efficient at scale. A real deployment should reuse a persistent index and verify source revision; neither was implemented. FTS5 may be absent from some Python/SQLite builds, and short strings (<3 Unicode characters) cannot be searched through FTS trigram alone.
- No content summarization was implemented. Verbatim evidence was chosen to avoid loss of hidden constraints; actual AI context creation would require measured truncation/coverage and an 'insufficient evidence' gate.

## Practical adoption and preservation

A coordinator can consider a **read-only prototype** to select a small set of authoritative documents before a 'continue' turn, but must validate source SHA, constraints, dependencies and project access. Preserve official `STATE/HANDOFF` generation, PR #113 provenance/review rules, and all current quality gates. Do not automatically integrate into A/ABCD/Geometry Lab. This research has **no real access-control enforcement**.

### Reproduction

```sh
cd research/development_intelligence/dil04
python -m unittest -v test_retrieval
mkdir -p runs
python benchmark.py --output runs/another-fresh-result.json
```

Keep `FREEZE.json` hashes unchanged; the benchmark errors if frozen source/fixture content differs. For stable reproducibility use the recorded first-run JSON as published evidence. A new run creates a new output file, never replaces the first run.

## Decision

**DIL-04 research cycle closed: accept only as artificial-data demonstration.** Product adoption postponed pending blind labels and actual public CBDK-doc evaluation with real query variants, omissions and source-version checks. No background work, CI integration, user account permission or production modification was performed.
