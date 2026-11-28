# R20 — joint geometry and constrained UV rescue: scoped gate passed

**Known-corpus feasibility gate passed: 12/12 selected outputs safe under the specified checks; 9/12 achieved at least 5% boundary-normal p95 reduction (required >=6). Product approval remains false.**

Same-run R19 repeated its earlier result exactly: 180 trials, 42 normal rejects, 133 UV rejects, 5 preliminary survivors, 1/12 improved. R20 used the same R18 candidate assemblies and R19 geometry proposals, invoking frozen R17 interior UV refinement only on proposals failing the original anisotropy screen. All source coordinates and UV, boundary and seam corner UVs, connectivity, material and seam metadata remain fixed. No threshold relaxation.

| Case | Before p95 (deg) | After p95 (deg) | Reduction | UV rescue preliminarily admitted / attempted | Selected method |
|---|---:|---:|---:|---:|---|
| r16_circle | 19.451 | 15.231 | 21.70% | 0/6 | smooth1.0_step1.0_fixed_uv |
| r16_ellipse | 36.081 | 13.888 | 61.51% | 15/15 | smooth0.05_step1.0_reoptimized_uv |
| r16_sparse | 27.654 | 18.838 | 31.88% | 3/12 | smooth0.05_step0.5_reoptimized_uv |
| r16_skew | 35.640 | 25.104 | 29.56% | 1/11 | smooth0.05_step0.5_reoptimized_uv |
| r17_round | 18.227 | 18.227 | 0.00% | 0/12 | baseline |
| r17_oval | 31.560 | 26.687 | 15.44% | 7/14 | smooth0.05_step0.25_reoptimized_uv |
| r17_lobed | 16.629 | 12.266 | 26.24% | 10/10 | smooth0.25_step0.5_reoptimized_uv |
| r17_offset | 39.582 | 34.907 | 11.81% | 8/8 | smooth1.0_step0.75_reoptimized_uv |
| r17_taper | 47.557 | 47.557 | 0.00% | 0/12 | baseline |
| r17_sparse | 25.643 | 15.853 | 38.18% | 12/12 | smooth0.25_step0.75_reoptimized_uv |
| r17_wave | 20.002 | 20.002 | 0.00% | 0/9 | baseline |
| r17_skew | 35.132 | 19.584 | 44.26% | 12/12 | smooth0.05_step0.75_reoptimized_uv |

- 68/133 previously UV-rejected proposals passed the added UV rescue screen (51.13%). This is preliminary admission, not a claim that all were independently CGAL-validated. 73 total preliminary survivors versus 5 in R19; remaining 65 UV rejects and 42 normal rejects. 0 rescue exceptions. Only selected/fallback outputs count for safety.
- Eight selected outputs use reoptimized UV, one uses unchanged UV with the original R19 geometry correction, three use unchanged R18 baseline.
- Mean per-case relative p95 reduction including fallbacks 23.38%; improved cases only 31.17%. Worst remaining boundary angle max 54.111 degrees. Mean time 3.806 seconds/case for the entire search including checks on this CI runner, not interactive Blender latency.
- All 12 final outputs passed the R19 original shape, normal, UV and CGAL acceptance checks plus exact source and seam UV preservation. Detached Python on previously seen artificial assemblies; no new holdout, no Blender roundtrip after R20 displacement, no visual shading/texture quality claim. UV density not a gate. R17 refinement changes interior bridge UV, not arbitrary original texture content. Three fallbacks show remaining limitations.
- The evidence supports combining the algorithms on this corpus, not general superiority. Next proposed R21: freeze this combined method; test unseen compatible synthetic geometries and verify actual Blender roundtrip, preserving all source data. No automatic R21.

## Evidence
R20 job success: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45521354483/job/138894133623 . Same-run R19 comparison: https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45521354483/job/138894133574 (expected failed improvement gate). R18 dependency succeeded. Do not describe entire workflow as green. Source hashes: {"cycles/r20/refine.py":"d15a3c47c098f7ba79087c213e12799e29d857c0d59b02bf16e366fce776e17c","cycles/r20/run.py":"c83327daafcce7be1ef2d3446e248b06a930b9d6869a2f182cd8ee09a3d31b1f"}. Raw result in CI artifact (14-day retention). Only Geometry Lab research scope; prior cycles unchanged, no A action, Draft PR #114, approved=false.
