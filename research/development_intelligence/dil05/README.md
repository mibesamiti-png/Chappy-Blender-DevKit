# DIL-05 — bounded early SHA-pinned metadata-review shadow experiment

**Research only**. No real AI worker, CI dispatcher, live PR polling, merge, permission, or modification of CBDK main. Existing A-owned PR #109 preflight/CI metrics are the proper live read-only tools; this experiment tests only potential early preparation timing and stale-head handling in toy event traces.

- [METHOD.md](METHOD.md): registered alternative comparison, baseline, budget, success criteria, trust boundary.
- [RESULTS.md](RESULTS.md): complete measurements, negative result (extra total work), R14 source-limited proxy, A proposal.
- [QUEUE.md](QUEUE.md): bounded later research candidates, not started.
- [FREEZE.json](FREEZE.json): 8 pre-holdout SHA256 hashes. No post-holdout source changes.
- [observed_r14.json](observed_r14.json): public PR+CI metadata snapshot, not employee time logs.
- [results/dil05-first-run.json](results/dil05-first-run.json): first and only holdout run result.

Reproduce (Python 3.11+, stdlib, no network, no Astra):

```sh
python -m unittest -v test_planner
mkdir -p runs
python benchmark.py --output runs/unique-result.json
```

Use a new output path to avoid overwriting original results. Model code is not wired into common CI. All previous DIL research and A/ABCD/Geometry work remain unchanged.
