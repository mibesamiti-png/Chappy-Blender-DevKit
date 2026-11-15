# DIL-06 results — observed CI→integration PR publication gap, not actual A idle

2026-11-11 JST. **One bounded historical public-data study completed. Evidence classification PASS; actual productivity improvement NOT MEASURED; no operational adoption.**

## Frozen conditions and local validation

- Read-only historical snapshots of R13, R14, and censored R15. Source: public GitHub PRs and exact-head workflow/job REST responses. Source PR/run links are stored in [observed.json](observed.json); [construct_snapshot_local.py](construct_snapshot_local.py) documents manual transcription of run IDs, required job times, and SHA.
- In two completed historical rounds, **3 specialist PRs × 5 required workflow families = 15 workflows per round; each PR has 10 required matrix jobs (30 jobs/round)**. All relevant actual run/job records were checked for success and immutable final SHA. R13 B's Blender run was `workflow_dispatch` and would be missed by a PR-only run helper; here it was included using the exact-head runs query.
- Frozen SHA256 of six sources/observations/tests/method/evaluator in [FREEZE.json](FREEZE.json) **before** one complete dataset evaluation. Post-evaluation tuning of frozen items: **0**.
- Linux Python 3.13.5, standard library only. **15/15 focused unittests successful locally**; tests cover wrong SHA, missing matrix jobs, missing family, duplicate family, incomplete job listing, reversed integration time, UTC strictness, optional skipped handoff helper, pending R15, no unauthorized permissions, input preservation. One offline report in [results/first-pass.json](results/first-pass.json). No third-party dependencies, Astra, LLM or Blender. **No dedicated DIL-06 CI wired to shared workflows**.

## Actual public GitHub timestamp measurements (UTC)

| Round | Latest required specialist CI job completed | A integration PR created | Observable elapsed | Interpretation |
|---|---|---|---:|---|
| **R13** B #100 / C #102 / D #103 → A [#104](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/104) | 2026-11-08 **02:35:37** | 2026-11-08 **02:44:01** | **504 s = 8m 24s** | CI-to-PR-publication gap only |
| **R14** B #107 / C #108 / D #106 → A [#117](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/117) | 2026-11-08 **03:37:40** | 2026-11-10 **21:24:36** | **236,816 s = 65h 46m 56s** | CI-to-PR-publication gap only |
| **R15** B [#120](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/120), C [#121](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/121), D [#119](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/119) | CI not collected in this bounded historical snapshot | No integration PR observed | **null** | Censored: neither failure nor measured waiting |

GitHub Actions primary sources include [R13 D Blender run](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42439001915) (last required job 02:35:37 UTC) and [R14 B Blender run](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42443283072) (last required job 03:37:40 UTC). The report also checks all other required CI families and their exact heads; see saved run links per specialist in `observed.json`.

**Critical caveat:** The R14 ~66-hour interval is **not** 66 hours of A processing, 66 hours of BCD idle, or 66 hours that an automatic scheduler could save. Actual user instruction timing, intentional pauses, other projects, A review start/end, human minutes, background execution, and causal reason for the interval are unobserved. No causal comparison is possible from two rounds. A PR's `created_at` means a candidate was published, not that review started. Both historical rounds had differing calendars, task content and development processes. R15 lacks a corresponding integration publication in this snapshot. No estimate of real speedup, human effort or usage cost is justified.

## Safety and practical findings

**Positive, bounded result:** a 30-required-job/round exact-head snapshot can produce a reproducible publication interval without conflating workflows with matrix success or pretending missing causal fields were measured. `measure.py` refuses to emit the interval when required jobs, workflow families, head SHA or integration timing evidence is missing or inconsistent. `can_skip_ci=false` and `can_authorize_merge=false` always.

**Negative and missing evidence:** GitHub alone does not reveal A review minutes, user's intervals between prompts, BCD actual idle time, actual duplicate CI cost, model inference time, or a counterfactual faster workflow. For both completed rounds these fields are explicit `null`, not 0. `updated_at` may lag real job completion, so exact job `completed_at` is used here; R13 manual Blender dispatch is included. If an external tool reads only PR-triggered runs, its apparent completeness may be false.

**Costs:** This study has a small manual public-metadata transcription and snapshot-check cost. No CI was skipped, no optimization deployed, no additional telemetry collected, and no human intervention reduced by this research; the next study would need a *voluntary* A-approved instrumented trial if genuine review/wait minutes are desired. DIL-05 already warned that speculative prep could increase total work. Recommending A collect timesheets unprompted would itself add work, so no such request is sent.

## Adoption and closure

The preregistered bounded evidence-quality criteria were met: 2 observable completed rounds, 1 properly censored round, 15/15 focused tests, all missing human/AI efficiency fields remain unknown, no authorization/CI changes. **Conclude DIL-06 at this point.** The evidence classifier is research-only; do not merge it into A's existing #109 tool or replace #109's real preflight. Official A documents, team branches, current CI and Geometry Lab are unchanged. Real developer efficiency is **unmeasured**; this research should not be promoted as a time-saving result.
