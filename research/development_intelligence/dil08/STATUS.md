# DIL-08 status — complete first full-corpus SQLite field experiment

2026-11-11 JST. **Independent frozen research: completed; prototype remains NOT adopted in production**.

## Done

- Frozen METHOD/TAG_CATALOG/SCENARIOS/selector/evaluator SHA256 recorded before any field score (`FREEZE.json`).
- Real GitHub Actions one-shot [run #42963844005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42963844005) on isolated branch; 35/35 unittests, pinned 12 Git blob sources, genuine SQLite FTS5 engine and full-source scored comparison succeeded.
- Original 70,410-byte first-run JSON preserved permanently as `results/first-full-sqlite.json.gz` with SHA256/runner evidence in [RESULTS.md](RESULTS.md).
- On 12 hand-labeled operational scenarios: candidate selected 37/37 evidence; 29/29 mandatory action, 8/8 additional; 0 R15 current; candidate/full byte ratio 46.72%; exact sets 7/12.
- On 15 already-seen free-form DIL-07 questions: candidate only 10/16 evidence (DIL04 hybrid 11/16). **This is the main failure preventing adoption.**

## Not done / blocked from real use

- Freeform Japanese intent/topic classification with independent blind gold; context accuracy or AI agent obeying instructions; live role/CI/HEAD checks, permissions, current source freshness, token/cost/time or end-to-end productivity validation.
- No shared ABCD/CBDK code changes, research adoption, production CI edits, main merge, real mesh or private data handling. `limited_field_pass` is only for the small authored dataset.

## Next

Design **DIL-09** as a new preregistered experiment using blind questions, ambiguous/incorrect tags, comparison against authority-first alone, lexical fallback and protected-reference routing. Verify document omission cost and human tagging overhead. Keep PR #115 Draft and avoid modifying frozen DIL-08 method/results.
