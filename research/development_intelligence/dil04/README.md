# Development Intelligence Lab — DIL-04

Synthetic-only, reproducible evidence retrieval experiment. No production or permission authority.

Read in this order:

1. `METHOD.md`: hypothesis, four comparison methods, preregistered thresholds, budget, trust boundaries.
2. `RESULTS.md`: measured results, negative outcomes, limits, adoption recommendation.
3. `FREEZE.json`: original source and fixture hashes checked by benchmark.
4. `retrieval.py`: baseline/all-context, exact metadata, FTS5 and hybrid.
5. `fixtures/` and `corpus.json`: human-authored gold IDs and artificial source text.
6. `test_retrieval.py`, `benchmark.py`, `results/dil04-first-run.json`: offline replay.
7. `QUEUE.md`: only next-cycle candidates, not active implementation.

All code is standalone Python standard library (SQLite FTS5 required for query fallback). No network, AI, Astra, Blender or external packages. The 12/12 held-out result applies only to artificial cases. Input bytes reduction is not AI token/cost reduction. No official STATE/HANDOFF edits, CI wiring, merges or real user data.
