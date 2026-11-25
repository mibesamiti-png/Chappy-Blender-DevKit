# DIL-09 phase 2 — measured result and resume rehearsal

2026-11-25 JST. Research-only, no ABCD adoption. Phase 1 records unchanged.

## Frozen execution

- Frozen research HEAD: bbbb58fe8a112420435f857fb86665b155998382.
- Isolated runner HEAD: 62b5a9138301c222c731d27a935cbd71b2313be9.
- [Run 45515838005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45515838005), job 138874902713, completed/success. Python 3.14.4. All 19 unittest cases passed (0.014 seconds reported for unittest alone).
- Original A candidate #109 checker was retrieved and its Git blob verified by the successful workflow; source remains unchanged.
- Replayed OBSERVED.json: summary_ready, 7/7 exact-context workflow families, no detail requests, all permission flags false.
- Compact UTF-8 JSON: projected workflow metadata 6,790 bytes; checkpoint 1,191 bytes, 82.459499% smaller. This is a storage representation comparison, not network bandwidth, billed tokens, full handoff completeness or task elapsed time. Raw API response sizes were not measured.

## Fresh read-only resume rehearsal

After the isolated run, the frozen fixture was reopened. The public development branch was read before and after a fresh PR/Issue/run/tree observation.

- Dev start/end: 2b8220210c2475239a43354d544b5a6f176fba80, both match fixture.
- PR #25 start/end metadata match fixture, including main base SHA c5b63ba50f4f53e22dea3ddc72486a17aa9dd939.
- Issue #125 start/end data match fixture (revision 1, R16 normal).
- Seven projected run records match fixture after sorting by run ID, total_count=7, all seven completed/success.
- Three source Git blob identifiers match fixture, from a nontruncated recursive Git tree: AGENTS.md b36e5bb815bf3a1a6af3642bbb1cdca3ce5fb02e; docs/R16_ABCD_START.md fd6a107ad87bac61ef9ca6a4c1192462ac16a286; docs/PARALLEL_DEVELOPMENT.md 6f7a8b1bd7d1aaa6024c245afe063e31dd095505.
- 8 live metadata reads (2 HEAD, 2 PR, 2 Issue, 1 workflow list, 1 recursive tree), 1 frozen fixture read, zero detailed CI logs for this rehearsal. The research run's job log was read separately to obtain the actual experiment output, not to revalidate normal green CBDK jobs.
- No new Python execution on the fresh observation; the projected input matched the independently executed fixture. Bracketed reads are not atomic and cannot prove no intervening change. Tree fetch has its own data cost; no actual retrieval savings were measured.

Decision: the narrow phase-2 context-binding/checkpoint and read-only resume rehearsal gates PASS. The current adapter is tied to PR #25, this development branch, normal dispatch, supplied assignment and A candidate checker. It is not a generalized resume or authorization engine. Checkpoint references do not replace mandatory rules/code/test reads, required matrix job evidence, or A decisions. A new real workload pilot remains pending. No integration, shared CI or production changes.
