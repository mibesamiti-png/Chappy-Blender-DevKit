# Team A staged integration candidate

Base: `24099ec3aea32302f30dbcefa935d5e8b2a54594` (2026-11-26 JST).
GL reference: PR #114 `6cdb85f4c97bf4cdbb4693a7b1bc180149b4ca2b`.
DIL reference: PR #115 `70fb5701d65449839bcccacffd0d55d0afcf27a9`.
Dedicated branch only; no merge, release, shared STATE/HANDOFF or dispatch changes.

## Stage gates

| Stage | Gate | Current observation |
|---|---|---|
| 1 audit | API, units, ownership, dependencies, rollback and approval conflicts recorded | Previous local audit retained; public summary below |
| 2 isolation | Frozen read-only GL and local CJM tests | Previous GL 46/46 conditions; CJM 352/352 offline tests, 61 syntax checks; not rerun |
| 3 native chain | Numeric repair, synthetic native generation, frozen GL, candidate measurements | Local chain passed on all three requested Blender versions |
| 4 candidates | Locks/preferences, protected parts, regression veto, bounded correction | Negative control rejected, midpoint improved, measured target reached and stopped |
| 5 safety | Faults, cleanup, rounding and failed rollback halt | 16 native cases per version, including sticky stop regression; controlled fault injections only |
| 6 limited CBDK candidate | Validated adapter, no private code redistribution | Implemented as opt-in pure reducer and external-provider preview connector |
| 7 bounded UI | Conditions, inspect, compare, adopt/reject, cancel, restore/retry | Native panel/operators and boundary cancellation implemented; Windows mouse/keyboard and normal Undo remain unverified |

## Inherited audit and evidence boundary

GL detached indexed triangles use binary64 coordinates; shared-simplex IDs must not
be replaced by coordinate welding. R2/R3 resource exhaustion means unknown, never clean.
R3 was slower on sparse64: 4.856ms vs R2 1.770ms in the prior Windows experiment;
grid128 R3 537.941ms vs R2 778.435ms (three runs, no warmup, fixed order).
The new adapter will retain explicit method selection and bounds.

CJM dimensions, locks/preferences, numeric correction and readback/rollback are
local external capabilities. Numeric feasibility is not geometric feasibility.
Original CJM code, ZIP, private paths, extracted source inventories and test names
are not published. Prior CJM 352-test result uses mocked Blender/RNA and does not
prove Blender generation, UI, motion or printing. Rights are unresolved: no copying
or redistributing its implementation. A connector may use the locally supplied copy.

R28 is a fixed sphere/cube evidence contract; generic joint dimensions cannot be
submitted as its measured geometry. Reuse bounded trials, independent provenance,
protected-part veto and verified restoration, not its fixture identities/thresholds.
GL CGAL CI evidence is independent validation only, not a runtime dependency.
GL research aggregate CI contains failures/skips despite exact-oracle success.

Detailed implementation, failures and evidence: [RESULTS](RESULTS.md),
[local native observations](native_evidence.json), [usage](USAGE.md).
The local full regression suite has an unresolved R13 observation discrepancy;
it is not claimed green. Final commit CI is recorded in the Draft PR.

The v0.22 plan calls for an integrated Blender UI, candidate confirmation,
interrupt/failure/rerun support and real Windows GUI/Undo verification. This branch
implements only a bounded artificial-joint preview candidate; it cannot certify
the complete v0.22 product milestone. Formal state remains unchanged.
