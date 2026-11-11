# DIL-05 — SHA-bound, read-only early-review preparation (preregistered)

Date: 2026-11-11 JST. This is **research only**, not a production queue, CI dispatcher, merge guard or authorization engine.

## Existing work / choice

A-owned Draft PR #109 already implements `scripts/ci_cycle_metrics.py`, `scripts/abdc_preflight.py` and proposes rolling early review. Do **not** clone or bypass those tools. The official `docs/PARALLEL_DEVELOPMENT.md` also permits read-only A review while B/C/D are working, but requires a fresh combined-head 5-family gate and a fresh merged-dev 7-family gate. DIL-05 studies the small unverified question: **whether incremental, SHA-pinned review preparation can move mechanical metadata checking out of the all-BCD-ready phase without reusing stale evidence**.

Alternatives considered: (1) shorten/skip required CI: out of scope, unsafe without A review; (2) recreate A's metrics/preflight: redundant; (3) reorganize number of teams: high confounding and A-owned; (4) read-only incremental preparation with final HEAD recheck: selected as narrow test.

## Fixed design and comparisons

Three strategies replay **identical events** for each of 12 development and 12 held-out synthetic scenarios:
- `late_only`: after all three final exact-head synthetic CI/scope indicators are green, prepare all 3 metadata reviews; 0 ahead-of-batch preparation (safe reference).
- `eager_unpinned`: prepare as soon as green, but incorrectly keep first snapshot when the head changes (deliberately unsafe negative control).
- `sha_pinned`: prepare as each valid head appears, invalidate the value of outdated snapshots and prepare the newly green SHA. Every result says **manual review required, combined CI still due, no merge authorized, CI dispatched=0**.

Gold `gold_valid` is **manually written into fixture inputs** from the final team/HEAD/CI/scope/base event states; it is not derived from a model output. The simple input `scope_ok` and `ci` are assertions supplied by caller, not audited here. Real adoption must consume A's exact-head matrix preflight, *never* assume a caller's boolean is sufficient.

Metrics: final current-valid team matches to gold (12 per split), cases with unsafe re-use of stale prepared snapshots, number of metadata-preparation **units after** the batch's last green event (1 unit per team, equal-cost abstract units, **not work minutes**), and sum of possible overlap windows across teams (seconds between the team's evidence event and last evidence event). At the exact instant of final all-green, the last team is **not** counted as early preparation. Extra work due to invalidated snapshots is reported separately.

## Preregistered acceptance and stop rule

Accept a **research-only candidate** iff held-out `sha_pinned` has 12/12 correct current-valid team sets, zero unsafe stale reuse, at least 30% fewer post-ready metadata preparation units than `late_only` among eligible completed batches, all 15 focused unittest methods pass, and no CI/merge actions are performed. If any condition fails, record failure and stop without tuning. Even on success, no product/ABCD adoption, and stop after one cycle.

Budget: 12 development + 12 untouched held-out synthetic traces, 3 strategies, one frozen evaluation of each split, 15 focused unittest methods, <=60 seconds benchmark, **0 post-holdout tuning**. SHA256 freeze of implementation, benchmark, tests, source fixture builder, both input files and METHOD **before first holdout execution**. No real user files, Blender or model data; Python standard library only, no Astra or Codex required.

## Real-world metadata cross-check: R14

We also record read-only **R14 GitHub Actions API snapshots**, distinct from the synthetic holdout. Each exact current B #107/C #108/D #106 head had five workflow families all completed/success and documented job names, and changes confined to respective path sets without file overlap. Latest workflow `updated_at` among those five: C 2026-11-08T03:36:08Z, D 03:36:55Z, B 03:37:40Z; potential overlap windows **92s C +45s D =137 team-seconds**, max single-team lead 92s. These timestamps are **GitHub workflow last-updated proxies**, *not verified human-review start, true job completion, or actual time saved*. R14 has not been merged; no verified `next_first_commit_at`, so real BCD idle time and improvement are **unmeasured**. The per-PR source metadata and URLs are in `observed_r14.json`.

## Trust and failure limits

- No proof that a CI result remained attached to the final SHA at all intervening times; inspect immutable SHA and current refs again before decision. A's exact-head job matrix is necessary.
- `scope_ok` says only the path check passed, not behavior/API compatibility, review, artifact provenance or authorization. A review and combined-head/merged-dev CI remain mandatory. A single SHA changes when new commits arrive and invalidates any matching review cache.
- A delayed/error GitHub API response or unreadable PR fails closed; no automatic queue dispatch. Synthetic concurrency, review durations, human intervention, CI-cost savings, wait hours and throughput improvements **not measured**. A separate field trial needed.
- Source/code/synthetic fixtures contain no credentials, private models, real personal metadata or private source. GitHub public PR metadata only.

## Reproduction (Astra independent)

Python 3.11+:

```sh
cd research/development_intelligence/dil05
python -m unittest -v test_planner
mkdir -p runs
python benchmark.py --output runs/new-result.json
```

Benchmark refuses any changed frozen hash and writes only to a new path. Research tests are **not** automatically included in shared CBDK CI. Existing PR #109's `abdc_preflight` remains the proposed real exact-HEAD source-of-truth; this prototype only simulates early metadata preparation.
