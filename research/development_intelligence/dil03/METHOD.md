# DIL-03 — Cooperative checkpoint and fenced ownership: preregistration

2026-11-11 JST. Dedicated research-only synthetic experiment. No permissions are granted by this prototype.

## Selected scope and alternatives

The most important missing boundary after DIL-01/02 is handing a cooperative writer over without lost checkpoints or stale writes. Existing `docs/GLB022_RUN_REVIEW.md` already retains failed/incomplete synthetic checkpoints, but does not guarantee atomic save, process survival, old-writer exclusion, or autonomous resumption. Do not reimplement the existing GLB workflow.

|method|benefit|limitation|
|---|---|---|
|Owner name only|minimal|stale attempts and split save|
|Owner + revision CAS|protects stale revision|ABA when same writer name reused; split save|
|SQLite atomic transaction + owner epoch + revision CAS + checkpoint checksum|chosen for bounded single-host experiment, stdlib only|cooperative API only; not a process/permission lock|
|File lock + lease timestamp|simple local contention in some scenarios|stale writer not fenced by expiry; recovery complexity; deferred|

## Goal and preregistered success criteria

Compare 12 development and 12 **unused** artificial event traces (same cases and manually prepared gold for each method). Each gold includes the sequence of event statuses, final owner/epoch/revision/payload, and recovery validity. Two baseline implementations are deliberately simple comparators, **not CBDK's real implementation**. Gold was designed by this researcher, not by an independent blind assessor.

Accept prototype iff (1) guarded SQLite matches >=11/12 holdout cases; (2) beats each baseline by at least 3 holdout cases; (3) guarded has 0 incorrect final states and 0 incorrect recovery classifications in holdout; (4) all 14 focused unittest cases pass, including racing two SQLite connections and a child process exiting midtransaction; (5) no DIL-01/02 modifications. Stop and report even if negative.

Budget: 24 synthetic cases (12+12), one benchmark run per variant (3 variants evaluated once on each split), 14 unit tests, benchmark <=60 seconds, 0 post-holdout tuning. Source and both fixture SHA256 hashes are frozen in `FREEZE.json` **before the first holdout run**. At most 1 research cycle. No real Blender model/data.

## Trust boundary

`Store` uses SQLite `BEGIN IMMEDIATE` to compare claimed writer, epoch, and revision; updates the synthetic live state and checksum-bound checkpoint within one transaction. `recover()` **only checks** a checkpoint's digest and equality to live state; it never restores files or restarts jobs. Every successful transfer increments epoch. A previous epoch is rejected even if the same writer label returns (ABA). `before_checkpoint` is a controlled injected Python exception after the live UPDATE; uncommitted SQLite transaction is rolled back. A separate child-test uses `os._exit(23)` midtransaction to check the DB's rollback on process exit. Two threads submit competing cooperative writes using separate SQLite connections.

**Not implemented:** authentication; binding a token to the OS process; killing a still-running old writer; bypass-proof file/Blender protection; external file/GLB checkpoint consistency; power loss or disk-full recovery; network/multi-host coordination; post-COMMIT lost acknowledgments; automatic restart/resume; production performance; human approval. Claiming `actor='H'` is not proof a human acted. Hash detects accidental corruption, not malicious replacement of both data and hash. Successful simulation cannot guarantee production safety.

## Reproduce

Python >=3.11 and stdlib `sqlite3`, no Astra/LLM/network; run from this directory:

```
python -m unittest -v test_handoff
mkdir -p runs
python benchmark.py --output runs/unique-result.json
```

`benchmark.py` checks the immutable manifest hashes before scoring, and uses exclusive output creation to avoid overwriting recorded results. The fixture construction helper is for documentation only; changing/rebuilding fixtures invalidates the freeze.
