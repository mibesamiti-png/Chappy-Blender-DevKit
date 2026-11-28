# R13 B — first-probe threshold and late-density review

Base: `20ef39e43c9f9079ef638aa4b418ca164740fcbf`, R13 assignment after #99.
Only authored synthetic tests and this evidence document change. No new product
algorithm is justified by these measurements; the R10 filter remains intact.

## Added evidence

Three new unittest methods exercise:

- 64 cases: actual first-64 exclusions 6/7/8/9, reproducible prefix seeds
  6/7/8/9, late dense/sparse block rotation offsets 0/1/63/64. Equal segment
  multisets yield the same complete layout result under adaptive R10, fixed
  R8 and unpruned R2. The observed decision receives the expected exclusion
  count once. Each contour has 193 target segments, below the 256 edge cap.
- Independent analytic calibration of the inherited R12 projection tracer:
  three source samples scan 129 opposing lines, then the first reverse sample
  scans one line. R2 performs 388 nondegenerate projections, fixed R8 performs
  `3*(65-exclusions)`, and disabled adaptive performs `388-exclusions`.
  Tracing never enters timed runs; previous trace state is restored.
- Float32 opening shifts and near-contact component changes with four seeds
  preserve full report dictionary equality against R8 and unpruned R2.
  The independently computed R3 component mismatch remains present; false
  auto-apply and identity flags stay false. Existing R11/R12 zero-length,
  255/256/257 edge, 64 part and 512 face guards remain in the regression suite.

## Local measured observation

Python 3.12.14, focused tests: 3 passed in 0.714 seconds. Six warm samples per
mode, balanced cyclic mode order, wall-clock medians in milliseconds below.
Tracemalloc is used separately for allocation peaks, not timing.

| First64 exclusions | adaptive projections / ms | fixed R8 projections / ms | unpruned R2 projections / ms |
| --- | ---: | ---: | ---: |
| 6 | 382 / 1.171 | 177 / 1.169 | 388 / 1.068 |
| 7 | 381 / 1.189 | 174 / 1.159 | 388 / 1.091 |
| 8 | 171 / 1.058 | 171 / 1.049 | 388 / 1.091 |
| 9 | 168 / 1.015 | 168 / 1.004 | 388 / 1.011 |

Peak traced Python heap: adaptive 37,904 B, R8/R2 39,344 B for each case,
below the existing 32 MiB test guard. This includes wrappers, is not RSS,
and is not a total resource bound. The first-64 switch changes work, not
geometry. Fewer projections do not necessarily mean less wall-clock time:
for example fixed R8 at six exclusions does fewer projections but is slower
than the R2 wrapper in this sample. No speed threshold is asserted and no
representative real-GLB benefit is claimed. CI records per-version timings.

No false geometry result or stable improvement requiring a production change
was established. Sample agreement is not a proof of exact geometry, actual
holes, true part identity or addon causality. No private source/model was used.

The dedicated PR must separately pass Python3, Windows2, Blender3, Chromium
and Handoff. A verifies its combined HEAD and postmerge seven families;
local results do not imply those gates passed. Shared status is A-owned.

Related local suite `python -m unittest discover -s tests -p 'test_glb_match*.py' -v`:
62 passed in 32.996 seconds, including all inherited matching regressions.
The second run's timings varied (e.g. adaptive six-exclusion median 1.008 ms
vs 1.171 ms above), reinforcing that projection counts are not speed promises.
