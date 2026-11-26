# DIL-10 — phase 1 protocol walkthrough and calibration example

2026-11-26 JST. Research only. Frozen v0.1 protocol/cases commit bc3700fabd244895c2e1b25df63af8842a446974; exact-head three ordinary CI workflows passed (45804097545, 45804097203, 45804097243). Those workflows do not test AI behavior.

## Eight fixed cases: manual design walkthrough

The same assistant authored and read the cases and answers, so this is a white-box walkthrough, NOT an independent A/B trial or eight independently measured AI successes. No new code-task output was generated. The ordinary good development method is allowed to make the same decisions; no invented baseline failures.

| Case | Trigger | First action | Guard against overreaction |
|---|---|---|---|
| S01 | Identical input contradicts distance | Hold machining changes; confirm identical coordinate frame/settings; calibrate zero and known nonzero cases; independently compare surface quantity | Do not dismiss a real nonzero difference or equate equal bytes with equal world placement |
| S02 | Optional precision improvement | End this improvement: 0.002 mm vs specified 0.4 mm and all mandatory criteria met | The stated tolerance is case-specific, not a default for printers |
| S03 | Simpler existing method | Trial inverse rotation, existing local operation, forward rotation; verify constraints and outputs | World-fixed constraints can make this inappropriate; no unconditional equivalence |
| S04 | Integrated output fails | Continue minimal interference correction after isolating cause; rerun combined acceptance | Green component tests are not completion; do not halt required development |
| S05 | Completion evidence | Close the completed goal; no unapproved additional feature | A new explicitly approved task can start normally |
| S06 | Simpler options already ruled out | Continue bounded new method; preserve gates | No repeated comparison on unchanged evidence, no anti-complexity ban |
| S07 | No trigger | Normal continuation and remaining mandatory tests | No separate audit/report or new mandatory check |
| S08 | Acceptance tolerance unknown | Retrieve specification; request necessary judgment if unresolved | Do not invent acceptable tolerance or fix indefinitely |

All eight map coherently to the current written procedure in this walkthrough, including two explicit continue cases (S06/S07) and the necessary repair S04. No numerical behavioral success rate, causal improvement, or audit-time reduction inferred. Important interpretation: calibration/mandatory failures take priority over closing a goal; "continue" is not necessarily continuing the current method; expensive methods remain allowed when simpler candidates demonstrably fail. No protocol rewrite required on this evidence.

## Exploratory numerical calibration (actual JS execution in Code Mode)

A unit square in plane z=0 is sampled at A={(0,0),(1,0),(0,1),(1,1),(.5,.5)} and B={(0,0),(1,0),(0,1),(1,1),(.25,.25),(.75,.75)}. Compare maximum of the two directed nearest-point distances using Euclidean distance (finite point sets); compare with exact analytic surface Hausdorff distance for identical XY unit squares in parallel planes, abs(z shift). This is a toy quantity mismatch, NOT a reproduction of GL's actual instrument, a claim that finite-set Hausdorff is mathematically wrong, or a general mesh distance algorithm. Coordinates and threshold 0.002 are arbitrary synthetic units.

| Control | Finite samples distance | True surface distance | Sample/analytic pass |
|---|---:|---:|---|
| identical samples | 0 | 0 | yes/yes |
| same surface, independent samples | 0.3535533905932738 | 0 | no/yes |
| translated surface (0.01), independent samples | 0.3536947836765479 | 0.01 | no/no |
| translated surface (0.01), same samples | 0.01 | 0.01 | no/no |

One of four exploratory classifications disagrees. Both nonzero controls remain rejected. A zero test reusing the exact samples alone would miss the mismatch; include a geometry-equivalent but differently sampled input as well as a known positive distance control. The analytic oracle here is exact only for this simple surface family. The observed values are actual executed JS results; not a preregistered independent test or the user's reported 156 comparisons. No production code, additional CI, or measurement engine created.

## Next decision

The lightweight protocol has no obvious contradiction in the authored cases, and the example concretely demonstrates the value of calibrating measurement semantics. It has NOT demonstrated improved LLM decisions versus a competent baseline. Independent model contexts, comparable tool access, blind scoring and actual code-task outcomes are not available within this one conversation. No fake baseline and no invented time/quality metrics.

Use at most one owner-approved real task or a small paired comparison in separate contexts if the user wants actual behavioral evidence. Give both arms the same task and gates; add only the short audit cue in the intervention arm, permit normal sound judgment in both, withhold evaluation key. Record quality, unnecessary changes, human corrections and audit cost; if no difference, stop. No framework expansion, production rollout, mandatory A action, or GL/ABCD changes. Do not keep inventing artificial tests merely to claim progress.
