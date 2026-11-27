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

## Phase 212-B through H: limited cam engine proven
- Common C2 motion tracks, sampled radial roller profile audit, native annular part construction, native stack kinematics.
- Single actuator and two-station ideal rigid camshaft contact fixtures passed engaged, separated and motor-off tests. Gravity return and ideal guides remain laboratory assumptions.
- Integrated fixture: source cd966c260d0c9ba75dcd995c0c965062f97b5e42; run 45965339628 (all five jobs successful, 23 Python tests). Compact candidate rejected at geometry; reference candidate passed geometry, screen, physical motion and controls. Artifact 15182413700.
- This is bounded selection of declared candidates, not arbitrary mechanism invention. All seven regression workflows on that source passed; historical walk gate remains false.

## Phase 212-I: separate external Geneva indexing adapter
Analytic external Geneva centerline model for 3–12 slots. One drive revolution advances 360/N degrees; motion fraction 1/2-1/N, dwell fraction 1/2+1/N. Conservative preliminary slot envelope and independent Cartesian pin/slot projection audit. Compare finite candidates against explicit indexing requirements (advance, minimum dwell, hub/web envelope and continuity).
A conventional Geneva has continuous angle and velocity but a nonzero acceleration jump at engagement/disengagement. Do not disguise this as the Phase212-B C2 quintic motion track: reject a strict C2 request instead. No solid wheel, locking disk, actual contact, load capacity or fabrication validation yet. Next after analytic gate: wheel/driver/locking geometry and native independent verification before integration with cam drive. Main/dev unchanged.
