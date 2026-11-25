# R22 / F019-03 — preregistered synthetic detection-limit matrix

Base 2f18de31b63bec91538e557171e9a4dac8065e4a, #125 revision 12.
Measurement-only candidate. No production, schema, CLI, viewer or GL research
changes. Fix the fixtures and independent expectations below before CI; do
not tune thresholds after observations. Coordinates in arbitrary input units.

| family | fixtures | independent surface expectation |
|---|---|---|
| aperture | square sheet [-1,1]^2, centered square cut width .5 / .02 | true max width/2; reverse zero; sampled result may miss |
| aperture control | same sheet, subdivided to 3x3 at +/- .25 without cut | zero; outer boundary count changes 4 to 12, not a hole |
| thin wall | single sheet vs two parallel sheets, separation .02 / .002 | exact max separation; reference-to-candidate zero; not minimum thickness |
| thin wall control | same sheet alternate diagonal | zero |
| joint | two unit boxes touching at x=1; shift second by +.2 / +.02 / -.2 / -.02 | true max absolute shift; gap/contact/penetration known only by constructed boxes |
| joint controls | unchanged touching pair; coincident extra copy of one box | zero observed surface difference; duplicated part identity ambiguous; contact/intersection not proven |
| internal | outer cube [-1,1]^3 plus explicit inner cube half-size .5 / .25 vs outer alone | true max 1-half-size, reference-to-candidate zero; no solid classification |
| internal control | identical outer shell alternate triangulation; no internal surfaces in either input | zero surface difference; hidden physical interior unknowable |
| internal unknown | same outer shell bytes/geometry could describe different unencoded interiors | information absent, not a negative or positive detection target |

Degenerate single triangle rejected separately (Python). Existing R20/R21 cap,
dense budget stop, SHA and legacy regressions are retained, not duplicated.
All cases <=64 triangles and <=3 parts per side; explicit product profile
expanded_2048_parts, existing global and local cumulative budgets separately.
For each case compare fixed/adaptive sampled maxima, reverse directional
maxima, boundary edge counts, exact-coordinate feature hints, R21 ambiguous/
unmatched/suggested counts and supplemental 24+24 probe sensitivity counts.
The latter are sensitivity evidence, not defect detection; use existing
1%/5% scene-diagonal color thresholds and existing 1e-6 global difference
rule; no tuned classification. Count surface TP/miss/FP/negative separately;
unknown hidden interior and contact/physical-thickness conclusions stay
unmeasured, regardless of geometry difference. Analytic maxima are upper
bounds for samples; exact constant-distance cases must match within 2e-5
(roundtrip float tolerance). No exact Hausdorff or solid proof.

Budget: max 16 matrix rows, max 64 triangles/side, 3 parts/side; one R20/R21
parent invocation per native row except one aperture representative
warmup+3 median (three additional invocations) and two compatibility\nprofile calls on that same case: max 21 parent invocations. Retain per parent 180s
timeout, 1MiB report cap, global+local 263744 samples/16M node pops/8M
evaluations and <=130 BVH builds; actual counters logged. Auxiliary
boundary/feature passes linear bounded input except shared-vertex hints
bounded by 64^2; supplemental probe <=96*64^2=393216 exact distance calls
per row and 6144 query samples, by worst-case all-target traversal.
Report this as an upper bound, not measured exact auxiliary work. No
additional scans in production. All auxiliary data local synthetic only;
aggregate marker and JSON no coordinates or names. Native memory not measured.
GL exact static research reference #114 HEAD 6ddda0c84d3fce1ed4a538c148e8e773cb7fd94f
is independent review_only/approved=false; no adoption/import here.
If evidence fails or lacks demonstrated safe improvement, retain current
product and submit measured limitations to A. Actual observations pending CI.
