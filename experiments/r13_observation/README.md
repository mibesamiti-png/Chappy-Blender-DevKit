# R13 diagnostic — isolated, not an integration candidate

Base candidate: a637d673ba673e1f996d0141bff01f1bcce564e8 (Draft PR #196).
R13 file blob 5b32b837001c78c52ef2dfd8333803be6743f831 is identical to dev 24099ec3aea32302f30dbcefa935d5e8b2a54594.
R27 Windows 3.13 run 45768313401 attempt 1 failed; attempt 2 passed. Prior record identifies the root case-alias positive test. PR #196 records two local full-suite failures, then one retained changed-source negative test; raw local assertions and fingerprints have not been obtained. Final public Windows 3.11/3.13 CI passed 1369 tests each (16 skips).

Hypothesis only: path metadata and open-handle metadata may differ before mutation, or the final metadata may not reflect the expected mutation. Separate early refusal from final change detection. A failure in the negative test does not by itself establish that stale data was returned.

Run the existing full suite once and 20 repetitions of each of three existing focused controls in separate processes, on Windows 2022 Python 3.11 and 3.13. Record field equality at the original comparisons and whether the mutation callback actually ran. Do not add sleeps, re-read metadata, change existing tests, weaken comparisons, or change test/product code. Diagnostic wrappers can alter timing; a clean run cannot prove absence of the original failure. No CJM data, production or shared-state modifications. No automated repeat on non-reproduction; request the original local failure log before a fix. Public CI cannot reproduce the original local host exactly.

Run: python experiments/r13_observation/observe.py full or focused.
