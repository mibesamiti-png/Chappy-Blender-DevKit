# DIL-03 — cooperative writer handoff and checkpoint research

**Synthetic, bounded, standalone experiment; not production edit authorization.**

Reading order: [METHOD](METHOD.md) (preregistered scope and acceptance) → [RESULTS](RESULTS.md) (actual outcomes and limits) → [QUEUE](QUEUE.md) (future research). [Source](handoff.py), [focused unit tests](test_handoff.py), [synthetic benchmark](benchmark.py), [freeze manifest](FREEZE.json), [case fixtures](fixtures/), and [raw run details](results/dil03-first-run.json) are included.

Run with Python 3.11+ from this directory:

```
python -m unittest -v test_handoff
mkdir -p runs
python benchmark.py --output runs/new-run.json
```

The program only touches a temporary synthetic SQLite DB; it does not access CBDK project data, private assets, actual OS editors, real Blender sessions, or GitHub. `recover()` only checks a local checkpoint; it does not restart or restore work. It cannot kill old writers or bind writer names to human accounts. Accepted **only within its artificial acceptance conditions**. See RESULTS for evidence limits.
