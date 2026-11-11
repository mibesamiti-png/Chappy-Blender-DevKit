# DIL-03 Results — checkpoint + cooperative handoff fault experiment

2026-11-11 JST. **Research prototype accepted on synthetic test only, not integrated into CBDK.**

## Experiment control

- Pre-registered objective, thresholds, budget and limits: [METHOD.md](METHOD.md).
- 12 development + 12 held-out synthetic traces. The 24 gold labels were authored by the same developer and are not independent blind evidence.
- Source, test, evaluation harness, fixture authoring code, both fixture files and METHOD: 7 SHA256 hashes frozen in [FREEZE.json](FREEZE.json) **before** executing holdout. Exactly one holdout benchmark run; post-holdout modifications to frozen items: **0**.
- Environment: Linux, Python 3.13.5, sqlite3 standard library, local file database, no third-party Python packages or network. No Astra, LLM, Blender or private user data.
- Local focused unittest: 14 passed (including 2 competing threads with separate SQLite connections, one winning the revision and the other rejected; and a child `os._exit(23)` while SQLite transaction is open, with its uncommitted update rolled back).
- Serialized detailed per-case results in [results/dil03-first-run.json](results/dil03-first-run.json). The benchmark did not record meaningful wall-clock time; genuine development productivity / AI tokens remain **unmeasured**.

## Per-case exact-gold match

Exact match means event status sequence, final state (writer, epoch, revision, payload), and recovery classification all match the manually specified gold.

| split (12 each) | method | exact matches | wrong-event scenarios | wrong-final-state scenarios | wrong-recovery scenarios |
|---|---|---:|---:|---:|---:|
| Development | owner name only | 6 | 3 | 5 | 1 |
| Development | owner+revision CAS | 8 | 1 | 3 | 1 |
| Development | guarded SQLite+epoch+revision | **12** | **0** | **0** | **0** |
| Held-out | owner name only | 2 | 6 | 8 | 1 |
| Held-out | owner+revision CAS | 2 | 9 | 8 | 1 |
| Held-out | guarded SQLite+epoch+revision | **12** | **0** | **0** | **0** |

**Pre-registered narrow acceptance achieved.** Guarded held-out 12/12, +10 over each toy baseline, final-state mismatches 0, recovery misclassifications 0, and 14 focused unittest passed. Stop this research cycle; do not add features beyond evaluation.

### What failed in the baselines

Owner-name-only allows an earlier invocation of A to write if the owner label cycles A → B → A; it does not bind a writer generation. It also ignores a stale expected revision. Owner+revision CAS avoids some stale edits but still permits the A → B → A old attempt when no intervening revision increments. Both reference models split live mutation and checkpoint update. The injected exception after live UPDATE leaves an inconsistent or unintended final state. Their `recover` falsely interprets a tampered checkpoint as present/valid. These simple comparators intentionally lack features and do **not** quantify a measured shortcoming of the real CBDK.

### What was demonstrated

Within a **cooperatively enforced, single-file SQLite API**: an old epoch/revision cannot overwrite a new owner, a valid handoff preserves the checkpoint and revision, an injected mid-transaction error leaves the original live/checkpoint state, a child's uncommitted SQLite transaction is lost on abrupt process exit, and a simultaneous two-client write race gives one winner. A simulated `H` owner's change survives a stale `A` write. Corrupt checkpoint content is classified invalid by read-only inspection.

### Limitations / negative evidence / non-goals

- `H` is merely a string; no real human authorization, cryptographic identity, OS process binding or ACL was implemented. Any actor able to bypass this API and edit DB/files/Blender is not fenced. **Old writer is rejected only at cooperating API boundary; the process is not killed.**
- The per-case dataset is small and adversarially enriched; percentages cannot be extrapolated to production incident rates. The same researcher authored all gold and implementation. Race tested once, not a stress guarantee.
- Child abrupt exit validates SQLite rollback before COMMIT, **not** whole-application recovery under power loss, disk-full, filesystem corruption, or long-running Blender save.
- `recover` checks checksum+agreement with current DB state; it neither restores previous versions nor restarts work. The hash is not tamper-proof authentication; an attacker could replace both payload and hash.
- Missing proof: multi-machine coordinator, real process liveness, expired lease takeover, network partitions, dead client detection, automatic safe resumption, file-version conflict, human unsaved state, checkpoint assets outside one SQLite transaction, post-COMMIT acknowledgment loss, Blender 4.x/5.x or Windows behavior, real AI integration, cost, latency under load, human interventions and productivity.
- No real CI was attached for DIL-03; 14 Python tests were run **locally**, not under CBDK's common workflow. Ordinary CI success at the PR HEAD must not be called DIL-03 CI coverage.

## Adoption recommendation

**Keep as independent research, not production.** A can consider a gated single-writer adapter contract for a *future* local work-item orchestrator, using existing checkpoint semantics rather than rewriting the GLB experiment recorder. Require authentic writer identity, verified durable file snapshots, recovery UX and Windows/Blender tests before enabling edits. Geometry Lab may reuse the *design constraints* for experiment ownership, but #114 stays untouched.

## Conclusion

Astra-free: synthetic state transitions, CAS, SQLite transactions, SHA-256 integrity check, manual test fixtures and result comparison all work under Python stdlib. Runtime autonomy and user-benefit improvement have **not** been demonstrated. Follow-up topics are in [QUEUE.md](QUEUE.md); do not start another experiment in this cycle.
