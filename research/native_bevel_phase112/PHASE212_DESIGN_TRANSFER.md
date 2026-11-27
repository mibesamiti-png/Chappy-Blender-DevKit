# Phase 212 — reusable mechanical design evaluation

## Close Phase 211 (first demonstrator, user accepted research stop)
The user confirmed motion on their own PC and explicitly agreed to move on.
Preserve the demonstrator, not a claim of qualified walking.
- Source: 57f60ba748e4e2364abcef91f8188aa780c5fe0a
- Native Blender 4.4.3 run: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45929746273
- Artifact: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45929746273/artifacts/15168282701
- 1201 frames; 3 completed cycles; forward distance 3.556543 model units; maximum tilt 5.634404 degrees.
- 10/12 motion checks pass. Foot error 0.097379 > 0.04; two-pad geometric support fraction 0.810991 < 0.95.
- Full-motion gate false; frictionless and motor-off controls skipped. User observation is supplemental, not a replacement gate.
- Ideal offset constraints and rigid camshaft assembly; no manufacturing certification.
- Prior diagnostic: run 45916020672 demonstrated identical separated motor-on/off outputs, but retained the original separated-test failure.

## Transferable techniques (bounded scope)
| Technique | Evidence | Generalization target |
|---|---|---|
| Inverse roller profile from motion law, normal offset, independent segment audit | phase210_inverse_cam.py | Arbitrary prescribed motion input, explicit geometry constraints |
| Static support candidate screening | phase211_support_design.py | Candidate specification, independent dense verification |
| Integrated rigid camshaft | run 45879625049 | Rigid group assembly only where relative motion is not required; retain separate collision surfaces |
| First-error localization and paired controls | runs 45879109761, 45916020672, 45920121053 | Time-ordered observations and causal controls |
| Fixed candidate budget, stop when no candidate passes | runs 45925281376, 45928061863 | Bounded screen and explicit redesign action |
| Distinguish motion demonstration and certification | run 45929746273 | Independent geometry/screen/full-motion/negative-control stages |

## Phase 212-A
Backend-neutral pure Python evaluator: finite observations, inclusive numeric limits, earliest observed violation, pass/fail/unverified states, predeclared candidate budget and rank, separate qualification gate. Tested independently of Blender; the historical summary fixture is a replay of reported aggregate values, not a reconstruction of native per-frame evidence.

Next: general-purpose motion specification and geometry adapters; validate each on small fixtures before composing a design engine. Do not launch another robot tuning loop. Geneva plus cam is a possible future composition challenge, not a selected requirement. Main/dev unchanged.
