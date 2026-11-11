# DIL-07 — field-check of DIL-04 retrieval on real CBDK documents

**Research-only.** Preregistered 15 scenarios and SHA-pinned 12 public authoritative/historical sources from CBDK's development branch. Fixed source-content probe shows **5 of 16 required document appearances missed** by the DIL-04-inspired hybrid selection, despite 88.70% fewer serialized UTF-8 bytes than passing all 12 documents. Do not call it a production-ready or fully reproduced SQLite measurement.

- [Preregistered METHOD](METHOD.md), [frozen docs and source hashes](manifest.json), [fixed questions/required evidence](cases.json), [hash freeze](FREEZE.json)
- [Source/content probe report](RESULTS.md), [first result](results/first-source-probe.json), [source presence matrix](observed_matrix.json)
- [Runnable pinned Git snapshot](snapshot.py), [full Python/SQLite evaluator](evaluate.py), [local tests](test_field.py)
- [Next bounded work](QUEUE.md)

Run `python -m unittest -v test_field` here. To evaluate complete original DIL-04 SQLite on the full real corpus, clone/fetch pinned source commit `2b8220210c2475239a43354d544b5a6f176fba80` and run `python evaluate.py --repo /path/to/clone --output runs/new-local-result.json`. SQLite FTS5 trigram must be available. This *full-corpus run has not occurred here*. Never overwrite first source probe or edit frozen inputs to improve the outcome.

No user/private files, source-derived private metadata, new CI, self-updating daemon, main merge or A work request.
