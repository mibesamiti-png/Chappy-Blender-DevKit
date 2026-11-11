# DIL-08 — development status after freeze and source-metadata probe

2026-11-11 JST. **Research-only; PR #115 Draft; never integrated into ABCD.**

## Completed

- Pre-registered [METHOD.md](METHOD.md), twelve [SCENARIOS.json](SCENARIOS.json) and twelve tagged public documents [TAG_CATALOG.json](TAG_CATALOG.json).
- Implemented deterministic read-only [selector.py](selector.py) with policy/round/CI-authority-first source routing; missing authority and old rounds fail closed. Python test: [test_selector.py](test_selector.py).
- Added executable [evaluate.py](evaluate.py) for true full-text SQLite FTS5 comparison using DIL07 SHA-verified `git show` source bodies; Python smoke tests in [test_evaluate.py](test_evaluate.py).
- **Immutable source + method + code hash freeze** at `e8a74c327dc146952c338fa066ab5dd01ab2aa6a` recorded in [FREEZE.json](FREEZE.json) before the first scored metadata source probe.
- Implemented [source_probe.py](source_probe.py), a *secondary* recorded DIL07-metadata scoring route, and [test_source_probe.py](test_source_probe.py). All **35/35** local unittests passed. No claim of GitHub CI for these tests.
- First source-metadata probe recorded in [PROBE_RESULTS.md](PROBE_RESULTS.md): **37/37** selected required evidence IDs; approx **46.72%** of full-context byte volume; **7/12** exact document sets; **0** old R15 as current. Not a SQLite field result.

## NOT completed

- Preregistered **real public-source SQLite** comparison has not been run; direct git clone blocked by DNS/network in current working container. This is the main remaining DIL-08 execution gate.
- New question labels not independently blind; 12 scenarios include manually provided intents/topics and are not representative real user prompts.
- No verified live dispatch of Issue #125, source HEAD freshness under concurrent commits, CI/current PR validity, human permission, model-answer quality, actual token count, real time savings, production benchmark or editor-side Blender validation.
- Tag search may return extra docs; exact doc-set 7/12 despite complete evidence recall in this small structured metadata probe.

## Reproduction from a CBDK clone

```bash
python -m unittest discover -s research/development_intelligence/dil08 -p 'test_*.py' -v
python research/development_intelligence/dil08/source_probe.py --output /tmp/dil08-source-probe.json
python research/development_intelligence/dil08/evaluate.py --repo /path/to/Chappy-Blender-DevKit --output /tmp/dil08-full-sqlite-first.json
```

`evaluate.py` requires the source commit `2b822021...` in the local git checkout; the command does not fetch it. Both evaluators use exclusive output creation and verify frozen source metadata. Do not retune the 12 scenarios after seeing a result. Failures warrant separate DIL-09 study.

**Next:** exact SQLite corpus run, separately recorded evidence, and independent reviewer evaluation before considering a limited A trial.
