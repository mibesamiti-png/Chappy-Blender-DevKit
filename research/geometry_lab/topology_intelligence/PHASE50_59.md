# Topology Intelligence: research checkpoint, Phases 50–59

Status: research only; approved=false. No production change, no private reference assets. Native workflow success is not whole-project approval; independent Geometry Lab research validation remains failed.

## Verified native evidence (Blender 4.4.3)

| Phase | Workflow run | Evidence | Decision |
|---|---|---|---|
| 50 | 45641557233 | 160/160 controls, 272/272 full nonincident result equality; 17.3903 to 2.1454 seconds, 8.1059x | Preserve batch SAT, do not prune by strain |
| 51 | 45643045367 | 2400/2400 controls, 272/272 full audit equality and anchors; 113.2602 to 27.7326 seconds, 4.0840x; 197 uncertain controls preserved | Preserve rank-batched incident test and uncertainty |
| 54 | 45646579779 | 300/300 controls, 9/9 larger meshes, 48/48 posed meshes, dense candidate count/checksum match at 2,096,128; peak candidate batch 16,384; 1.9675x additional speed on larger meshes | Adopt as research reference, not product; output and incident-pair storage still unbounded |
| 57 | 45694966123 | 129-bone calibration 35/35, max error 0.0007965001; 15/15 groups, 75 candidates, 68 eligible; 45 held-out pose pairs: 32 better, 9 same, 4 worse, 2 maximum-error regressions; zero newly flagged contact/degenerate/uncertain conditions | Evidence for equal-budget ring selection on prescribed synthetic axial motion only |

All timing ratios are comparisons within their respective experiments, not a multiplicative speedup claim. Numerical equality is not a proof of exact collision predicates. Phase 54 larger meshes had zero nonincident contacts; posed cases and controls supply separate positive-contact evidence.

## Phase 59 local development experiment

Compared uniform rings, cylinder-derived density, and shape-aware density on the four Phase 58 synthetic tube shapes (taper, ellipse, bent, bulged_bent), five motion fields, and 4/8/16 axial intervals at 24 rim vertices. Reused shapes are development fixtures, not independent holdouts. Both arms select using the same five mixture values (0, .25, .5, .75, 1), design angles 30/60/90/120 degrees, and same shape-specific constraints.

Shape-aware density: sample the maximum axial second-derivative magnitude of the rest surface and displacement fields over the rim and design angles; take its square root, floor at .25 of mean density, invert normalized trapezoidal cumulative integral to obtain ring positions. Mix with uniform knots, keep end loops exact. Eligibility: max rest edge ratio <=6, min/max spacing .35/2.5 times uniform, design rest P95 and max <=1.05x uniform, worst design displacement max <= uniform. Among eligible candidates minimize worst design displacement P95, then max, then mix. Both diagonal triangulations evaluated. Eval angles 45/75/105, different sample grid; no selection using eval results.

Actual local results: 60 groups, 600 candidate evaluations (including shared uniform candidates), 720/720 selection and boundary checks. 156 cylinder-density and 162 shape-aware candidates eligible.

| Comparison | Better | Same | Worse | Median gain | Best gain | Worst gain |
|---|---:|---:|---:|---:|---:|---:|
| Cylinder-density router vs uniform | 72 | 96 | 12 | 0% | 44.39% | -14.40% |
| Shape-aware router vs uniform | 101 | 69 | 10 | 2.71% | 58.12% | -14.28% |
| Shape-aware vs cylinder-density router | 66 | 69 | 45 | 0% | 45.26% | -7.94% |

Shape-aware maximum displacement error vs uniform: 104 better, 69 same, 7 worse. Held-out rest P95/max gate violations: 0/60. Elliptical shape comparisons against cylinder density: 6 better, 15 same, 24 worse (median -0.053%). Do not claim universal dominance. Both arms reselect on target shape and use rest guards; neither is identical to the frozen-layout transfer in Phase 58.

Local implementation and JSON were generated in the conversation runtime; not native Blender evidence. No collision test, physical material model, arbitrary topology or anatomy in Phase 59.

## Next research gate

Do not keep tuning on these 60 groups. Freeze both density rules and gates; use new noncircular tubular geometries and motion profiles. Compare native evaluated meshes at equal quad budgets, rest error, displacement P95/max, intersection/degeneracy/uncertainty and boundary integrity. Include a conventional low-bone bending case to separate skinning limitations from sampling errors. Do not approve a router that introduces new contact flags. After the gate, choose a bounded synthetic limb/joint prototype instead of indefinite microbenchmark expansion.
