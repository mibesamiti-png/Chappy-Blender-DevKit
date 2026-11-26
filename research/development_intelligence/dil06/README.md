# DIL-06 — GitHub publication interval evidence boundary

Small offline, read-only research code and exact-sha public snapshots. **This is not a developer speedup tool, process liveness monitor, merge authorization, CI gate, or actual waiting-time recorder.** The real #109 is A-owned and has the existing CI preflight.

- [METHOD.md](METHOD.md): preregistered narrow metric, alternatives, success/failure/stop conditions.
- [observed.json](observed.json): 3 historical stages, 30 exact-head workflows and required job finish times for completed R13/R14, R15 censored.
- [construct_snapshot_local.py](construct_snapshot_local.py): explicit transcription of public GitHub API times and URLs; not a background updater.
- [measure.py](measure.py): an offline evidence classifier that leaves unobservable causal fields null and refuses unsupported timing claims.
- [test_measure.py](test_measure.py): 15 negative/consistency controls.
- [FREEZE.json](FREEZE.json): SHA of frozen implementation, method and input before first complete evaluation.
- [evaluate.py](evaluate.py): one frozen, exclusive-file offline evaluation.
- [results/first-pass.json](results/first-pass.json), [RESULTS.md](RESULTS.md): reproducible evidence, limits and non-adoption decision.
- [QUEUE.md](QUEUE.md): independent next candidates (not started).

From this folder (Python 3.11+, stdlib):

```sh
python -m unittest -v test_measure
python evaluate.py --output results/new-unique-name.json
```

No private user files/GLB, credentials, external source, third-party code or model inference used. No A-owned docs or CI are changed. PR #115 remains unmerged Draft.
