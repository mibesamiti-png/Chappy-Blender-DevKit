# R12 B — threshold, permutation and nearest-projection work

Base: `faab6ab023f50495c719d091b29f320aa6ab36df` (R11 candidate).
No production changes. Four new tests use synthetic bounded data only.

The first 64 real bbox checks include exactly 7 or 8 exclusions. Late density
changes and four fixed-seed permutations preserve the segment multiset.
Fixed R8, adaptive R10 and unpruned R2 return identical issues. Full report
parity is tested separately with float32 triangle fixtures and seeded face
orders at 255/256/257 edges; R3 contact connectivity remains independent.
R11's 64part/512face and zero-length guards remain in the inherited suite.

A test-only line tracer counts nondegenerate nearest-projection evaluations,
without replacing the distance predicate. It observes the one-line norm2
branch, calibrated to exactly six projections for two corresponding segments
(endpoint/midpoint, both directions). The initial local instrumentation on the
multiline factor expression counted repeated line events, so it was corrected
and calibrated BEFORE commit/push; those preliminary counts are not evidence.
Tracing is restored in finally and NEVER used for timing. R2 mode is the
existing no-bbox-rejection wrapper, not historical-source runtime replay.

Local Python 3.12.14, calibrated projection counts:

| First64 exclusions | fixed R8 | adaptive R10 | unpruned R2 |
| --- | ---: | ---: | ---: |
| 7 | 174 | 381 | 388 |
| 8 | 171 | 171 | 388 |

Five warmed untraced samples, median milliseconds:

| Exclusions | fixed R8 | adaptive R10 | unpruned R2 |
| --- | ---: | ---: | ---: |
| 7 | 1.112 | 1.189 | 1.068 |
| 8 | 1.045 | 1.035 | 1.139 |

Traced allocation peaks per case: R8 39,368B, adaptive 37,880B, R2 39,344B
(all below 32MiB bound). This is Python traced heap including wrapper overhead,
not RSS or geometry storage upper-bound proof. CI records each Python version
separately. No repeatable general benefit or semantic defect was established;
changing/reprobing the product algorithm is not justified by these timings.
All four local tests passed. Sample agreement does not prove exact geometry,
physical holes, part identity or causality; auto application remains false.
