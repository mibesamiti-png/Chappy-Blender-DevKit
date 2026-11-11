# DIL-05 Results — read-only, SHA-pinned early review (NOT deployed)

2026-11-11 JST. **Research-only synthetic acceptance; actual development productivity improvement unmeasured.** PR #109 already owns real CI metrics/preflight, so this cycle only prototypes *when* a read-only metadata review could be prepared, never a duplicate safety/merge tool.

## Frozen experiment and execution

Prior to first holdout, freeze manifest `FREEZE.json` records 8 SHA256 values for source, builder, tests, development and holdout fixture, observed R14 evidence and METHOD. Development 12 / unused holdout 12, 3 policies, one holdout replay per policy, **0 post-holdout tuning**. Linux, Python 3.13.5, Python standard library only; benchmark wall 0.002271s locally (not real CI/work speed). All **15 focused unittest methods passed locally**. Detailed per-case evidence: `results/dil05-first-run.json`.

The manually authored gold labels are final valid team sets after all synthetic status events. Every strategy should classify current eligibility correctly; the interesting difference is earlier work vs stale reuse. `scope_ok` and `ci` are assumed synthetic inputs, not independently attested. `sha_pinned` cannot authorize or execute code, and it always requires final A review and combined-head CI.

## Held-out measurements (12 cases; 7 have all B/C/D green at final state)

| Strategy | Current-valid sets matching manual gold | Cases with unsafe reuse of stale prepared evidence | Metadata prep units remaining after final all-green (7 cases) | Total metadata-prep units (all 12) | Potential overlap windows sum (7 cases) |
|---|---:|---:|---:|---:|---:|
| `late_only` (safe serial baseline) | 12/12 | 0 | 21 | **21** | 0s |
| `eager_unpinned` (deliberately unsafe) | 12/12 | **4** | 7 | 33 | 977 team-seconds |
| `sha_pinned` (candidate) | **12/12** | **0** | **9** | **36** | 977 team-seconds |

`sha_pinned` moves **12/21 = 57.1%** of the *abstract metadata-preparation units* to earlier points in the synthetic traces, but increases total preparation from 21 to **36 units** (+15, or +71.4%). The last team becoming green at the exact all-green moment counts as work remaining, not done early. The 977 team-seconds are *opportunities*, not work performed or elapsed time saved. The static labeled scenarios contain no human review durations, actual CI reruns, merge delays or development productivity data.

- Development 12: `sha_pinned` gold match 12/12, unsafe reuse 0, eligible completed batches 5, late-only post-ready units 15, pinned 7; negative unpinned stale cases 4.
- Holdout 12: exact match 12/12 and 15 focused tests passed. Heldout is authored by the same researcher; independent blind evaluation was **not** performed.
- Narrow preregistered success criteria achieved (12/12, no unsafe reuse, >=30% reduction of post-ready prep units, 15/15 tests). This does **not** establish an overall resource/speed gain; in this corpus speculative work **increases**. **Do not deploy automatically.**

## Real public R14 metadata — limited observational proxy

[observed_r14.json](observed_r14.json) lists exact-head PRs B #107, C #108, D #106, changed file paths and five completed/success GitHub Actions workflow URLs for each. The five independent workflow run *updated_at* maxima were C **03:36:08 UTC**, D **03:36:55**, B **03:37:40** on 2026-11-08. On this snapshot, C could have been inspected at most **92 seconds** earlier than the last team's evidence, D **45 seconds**, sum **137 team-seconds**. This is a *hypothetical window based on updated_at*, not verified CI job completion, actual start of human review or saved A idle time. Changed paths do not overlap, but behavioral dependencies and ownership still need A's real preflight and manual review. All three draft R14 PRs are still unmerged in the inspected snapshot; combined-head integration, subsequent `next_first_commit_at`, true A review durations, and wait-time reduction **not observed**.

R14 is a particularly cautionary case: a best-case 92-second lead may not justify an orchestrator if checking the advance state requires expensive polling/extra reviews. The earlier R13 timeline is not used to infer causality because final per-head CI and A-human effort timestamps are insufficient.

## What was and was not solved

**Solved within simulation:** an exact final SHA/CI/base-bound snapshot can be selected for provisional use; later changes invalidate old evidence; no policy ever auto-merges or runs CI. A future A-controlled process could call existing `scripts/abdc_preflight.py` at the actual integration decision, and use a reviewer status cache as a suggestion only.

**Not solved:** trustworthy live CI/scope mapping (booleans are inputs), actual A review or worker scheduling, expensive polling/caching overhead, dynamic dependencies, GitHub webhook delivery, Codex limits, team-idle or throughput measurement, merging, permission/authentication, real developer burden. No real CI runs were skipped or eliminated: `dispatched_ci=0` in the simulator; this is not a CI-saving result.

## Practical costs and A proposal

Advantages: bounded early read-only prep while waiting for later specialist CI; stale SHA cannot be treated as a current prepared review by the candidate. No new dependencies and Astra-free.

Disadvantages: in the heldout simulation **71% more total preparation units** under head churn/blocked rounds; A already has rolling review instructions and real #109 preflight. A should *not* adopt a new scheduler solely on this result. If wanted, A may test an **optional human-invoked shadow log** on the next formally approved round, collecting: exact PR/head/five-CI-gate time, actual reviewer minutes, time until combined-head CI, old-head invalidations, number of duplicate CI runs and next team's first commit. Define an actual productivity threshold before a trial and stop if review overhead grows. No scheduled background task or organization changes were created.

## Safety/ownership and CI

Files are only under `research/development_intelligence/dil05/`. DIL-01/02/03/04 source and fixture are unchanged; no shared STATE/HANDOFF/AGENTS/common CI, A PR #109, Geometry Lab #114, BCD specialist PRs, main, releases or Notion edits. PR #115 stays Draft. All dedicated focused DIL-05 tests and frozen benchmark are **local**, not run by GitHub's common CI. If normal GitHub workflows pass at the new PR head, they cannot be described as DIL-05 test coverage.

## Conclusion

**Narrow experimental acceptance, automatic production adoption withheld.** The evidence supports provisional SHA-pinned read-only preparation mechanics under invented inputs; whether it actually reduces waiting or CI use is unknown and may be worse in total review effort. Stop this research cycle and record follow-ups in [QUEUE.md](QUEUE.md).
