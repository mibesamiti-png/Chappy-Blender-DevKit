# DIL-08 status — preregistration and read-only prototype

2026-11-11 JST.

## Completed in this conversation

- Preregistered [METHOD.md](METHOD.md), 12-document [TAG_CATALOG.json](TAG_CATALOG.json), 12 frozen-intent [SCENARIOS.json](SCENARIOS.json) **before any scored holdout execution**. Prior DIL-07 15 questions are **already-seen development**, not blind test cases.
- Added [selector.py](selector.py) read-only deterministic authority-first tag selector and [test_selector.py](test_selector.py) with **21/21 unit tests passing in an isolated local Python 3 runtime**. This does *not* establish real-world document retrieval quality.
- Added path+Git-blob-SHA identity checks against DIL-07's pinned manifest before future first scored evaluation. No LLM auto-classifier, live GitHub activity, autonomous permissions or text summaries implemented.

## Still not done

- `FREEZE.json` with final SHA256 of spec/code/questions has **not been committed**: a GitHub connector request timed out during the attempt. Do not score the 12 preregistered operational scenarios until this freeze is completed and verified.
- `evaluate.py` actual full-corpus SQLite FTS5 comparison and first scored run do **not exist** yet. DIL-07's earlier literal-substring proxy is not a substitute.
- No separate human reviewer, independent blind labels, observed intent-classification error rate, production HEAD/CI race test or actual token/cost/user-time estimate. Do not claim any efficiency gain for DIL-08.
- No 21-test run has been confirmed in GitHub Actions for this exact DIL-08 commit; the 21/21 are local tests only.

## Next safe actions

1. Freeze the GitHub versions of METHOD/CATALOG/SCENARIOS/selector/test as hashes; verify immutable manifest and source commit.
2. Build and run actual read-only SQLite field evaluator, using the pinned public Git objects and original DIL-04 implementation, with no tuning after viewing held-out results.
3. Record exact first-run JSON including recall, false-current or unsafe-permission flags, input bytes, reproducibility environment and failures.
4. Keep research [PR #115](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/115) Draft, and do not touch A-owned state, normal ABCD, Geometry #114 or main.

**Pilot acceptance:** 0 unsafe grants; 0 R15-as-current; 100% mandatory action sources; >=95% optional evidence; <=50% full-context bytes as a separate efficiency gate. Any missed gate is a real negative finding, not a reason to retune the frozen holdout.
