# DIL-06 — Publication interval versus unverifiable human idle (preregistration)

2026-11-11 JST. Research-only. **No additional work, monitoring, or CI requested of coordinator A.** Existing A-owned draft #109 already implements CI timing/preflight; this study does not copy or replace its operational tooling. User specifically requested continuing DIL research; no A operational authorization is inferred. DIL-05 cautioned that speculative earlier work increased total preparation by 71.4% in artificial cases; do not introduce a scheduler without proven benefit.

## Research decision

The requested full field study of true A review minutes, team idle, token cost, or counterfactual development throughput cannot be measured from GitHub PR and CI timestamps alone. Instead, complete **one bounded prerequisite**: evidence-label a GitHub-visible interval and demonstrate that missing causal/human data is explicitly unknown. The purpose is to prevent a persuasive-looking 2-day time gap from becoming a false claim of A overwork or potential time savings.

Compare two historical, public, already-completed CBDK rounds (R13 specialist B#100/C#102/D#103 → A integration PR #104; R14 B#107/C#108/D#106 → A integration PR #117), plus a third *censored* R15 snapshot (B#120/C#121/D#119, no integration PR observed). For each completed round, manually capture **all five named CI workflow families and all ten required matrix jobs** for each of B/C/D from GitHub REST at exact final SHA. Some runs are `workflow_dispatch` rather than PR-triggered (notably R13 B Blender); do not ignore them merely because a first-page PR-only helper omitted them. Keep run IDs, sha, updated timestamps, job completion timestamps and URLs in `observed.json` for replay.

## Pre-specified metric and stop gate

Define `all_required_ci_at` = maximum `completed_at` across the thirty required successful matrix jobs for B,C,D, only if every run and required job is on the recorded exact team SHA and has completed/success evidence. Skipped nonrequired helper jobs are allowed but never counted green. Define `integration_pr_created_at` = creation timestamp of the specifically corresponding A integration PR; never substitute its later `updated_at`/merged time. Then `observed_publication_gap_seconds` = integration PR created minus all required jobs completed if nonnegative; otherwise unavailable. **This is NOT A review time, total waiting, CPU time, processing time or speedup.** It includes all unobserved human/user/other work and intentional pauses. It says nothing about causality.

`measure.py` is a small offline reproducibility/checking function on the **saved public records**, not a live gate, and not a new CI collector. Production CI claims remain subject to current #109's job-level preflight and fresh GitHub verification. It explicitly reports unknown fields as null (`a_review_minutes`, actual worker idle, instruction wait, actual saved time, model compute/usage, repeat CI cost). `can_skip_ci` and `can_authorize_merge` are always false.

Narrow acceptance **before the first evaluated full dataset**: (a) both completed rounds have exactly five required completed/success CI workflow families per specialist and their required matrix jobs and same head SHA, (b) result from R13 and R14 is a nonnegative reproducible publication interval, (c) R15 has missing integration/CI data and **no** fabricated duration, (d) wrong SHA, missing job, missing family, incomplete listing and timestamp reversal fail closed in focused tests, (e) all 15 tests pass, (f) no causal human/AI efficiency claim in any report. If not, record negative outcome and stop. No post-measure optimization.

Budget: three static, public, cited historical round records; 30 workflow runs in the two completed rounds; no new workflows; 15 focused unit tests; one offline evaluation; max 60s evaluation, no broad API sweep. SHA256 freeze of source, dataset, unit tests, METHOD and evaluator before first full evaluation. No third-party dependencies or Astra. No private GLB, personal data, tokens, source path, unconsented images, or credential collection. No edited state of B/C/D, #109, Geometry #114, A's STATE/HANDOFF, shared CI or main.

## Safety limits

Static snapshots prove only their recorded SHA/time; newer PR commits invalidate their 'latest' interpretation. All durations are UTC. API job `completed_at` is job completion, whereas workflow `updated_at` may lag; manual review start/end has no reliable GitHub event. PR creation time shows publishing a candidate, not review initiation. 2 rounds cannot infer rate, expectation or effect of future process changes; A's R15 work may be ongoing or paused independently of GitHub. No user permission to continuously monitor or have A fill in a timesheet is assumed. No intervention deployed.

## Reproduction

From this directory, Python 3.11+ stdlib only:

```sh
python -m unittest -v test_measure
python evaluate.py --output results/new-unique-filename.json
```

`evaluate.py` verifies `FREEZE.json` against exact source/dataset hashes, performs one offline evaluation and creates output exclusively. The recorded `results/first-pass.json` is this cycle's evidence. Future #109 changes should be read from GitHub before any operational proposal.
