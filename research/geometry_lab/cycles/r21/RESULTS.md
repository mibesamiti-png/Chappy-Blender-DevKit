# R21 — frozen R20 on eight unseen synthetic geometries, Blender roundtrip: PASS

**First frozen holdout gate passed: 8/8 final outputs pass specified checks; 5/8 improve boundary-angle p95 by >=5% (required 4). Product approval remains false.**

Eight new shape specifications were committed with the preregistered protocol before first execution at 0a8823a63ce61514bb7d3f5e681f8c5b76bedfad. Frozen R10/R16/R17 prepared baseline strips; R18 harness imported these into Blender 4.4.3 source collars. After baseline audit, frozen R20 selected geometry/UV; the final strip was imported into independently recreated original source collars using R18. External evaluator compared actual Mesh arrays to the selected output and original source, including oriented triangle/corner correspondence, seam flags and pin preservation, R7 geometry rubric, CGAL and R14 UV checks, and original R20 normal and anisotropy acceptance. All eight prepared and passed both Blender rounds. No retuning or omitted shape.

| Case | Before p95 (deg) | After p95 (deg) | Relative reduction | UV rescue preliminarily admitted / attempted | Selected method |
|---|---:|---:|---:|---:|---|
| r21_round | 18.184 | 18.184 | 0.00% | 0/10 | baseline |
| r21_oval | 25.032 | 12.655 | 49.44% | 14/14 | smooth0.05_step0.75_reoptimized_uv |
| r21_lobed | 20.464 | 20.464 | 0.00% | 0/12 | baseline |
| r21_offset | 38.964 | 34.033 | 12.66% | 8/8 | smooth1.0_step0.75_reoptimized_uv |
| r21_taper | 39.357 | 33.453 | 15.00% | 8/12 | smooth1.0_step0.75_reoptimized_uv |
| r21_sparse | 22.506 | 10.873 | 51.69% | 13/13 | smooth0.25_step1.0_reoptimized_uv |
| r21_wave | 18.658 | 14.340 | 23.14% | 10/10 | smooth0.25_step0.5_reoptimized_uv |
| r21_skew | 26.126 | 26.126 | 0.00% | 0/15 | baseline |

- Mean per-case relative p95 reduction including fallbacks 18.99%; among improved shapes 30.39%. Five selected interior-UV reoptimization, three unchanged baseline. Largest improvement 51.69%.
- 53/94 UV rescue proposals admitted at preliminary screen; this does not imply independent CGAL validation of every proposal.
- All 8: source triangle XYZ/UV/material equality, exact selected oriented triangles and float32 corner UV roundtrip, seam flags equal selected, original pins exact, source-to-bridge continuity, original R20 normal and UV anisotropy nonregression constraints, original triangle quality and R7 rubric, joined CGAL zero, full-plane UV overlap zero. Max remaining boundary angle 39.076 degrees. Actual final arrays used to compute angles.
- These are unseen *parameter combinations in the same favorable synthetic geometry and rectangular boundary UV family*, not arbitrary artist models. Source collars are recreated, not an arbitrary existing .blend. No rendered appearance, custom normals, repeat-tile safety, multi-UV-layer, Undo or operator registration tested. No claim of universal quality or production readiness.
- Next proposed R22: inspect actual rendered checker texture and smooth/hard shading on controlled examples, measuring geometric versus shading normal continuity separately. Freeze the proven pipeline; do not expand another algorithm optimization cycle merely to improve metrics. R22 not started.

## Evidence

First R21 job completed successfully: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45521992586/job/138895893799 . Artifact 14980447665 (geometry-lab-r21-0dcbe06b4d5b2bd87306fa84720294dfc9f69746, 394293 bytes), containing baseline, baseline-raw, selected, selected-raw and eval JSON (14-day retention). Independent R18 rerun in the same workflow failed at Blender acquisition, and its dependent R19/R20 jobs were skipped; R21 independent job succeeded. Whole workflow not green. Final report commit verification separate. Only research-owned paths, no user data, no A action, no product changes. Draft PR #114 unmerged, approved=false.
