# R11 B — first-64 adaptive AABB bias

Base: `a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`.

Synthetic dense→sparse and sparse→dense contours have identical segment
multisets. Dense-first disables after 64 boxes (0 rejected); sparse-first
continues (388 boxes, 193 rejected). Both return the same R2 mismatch as
fixed R8 and unpruned R2. This demonstrates order-dependent work, not a
semantic defect. No production algorithm change is justified by this probe.

Local Python 3.11, five warmed samples, median milliseconds:

| Order | Fixed R8 | Adaptive R10 | Unpruned R2 | adaptive traced peak |
| --- | ---: | ---: | ---: | ---: |
| dense first | 1.035 | 0.973 | 1.063 | 37,008 bytes |
| sparse first | 1.120 | 1.125 | 1.349 | 37,008 bytes |

These small measurements are machine-specific observations, not performance
thresholds or proof of benefit for user geometry. CI prints equivalent
measurements separately for each Python version. The 32MiB traced heap bound
is not a process RSS measurement.

Four new tests cover probe decisions, complete report equality under face
reordering/float32 perturbation, 255/256/257 edges, 64 parts/512 faces,
independent R3 contact/gap classification, degenerate edges and the over-budget
fail-closed result. All four passed locally. Existing R10 tests remain intact.
Sampled contour agreement does not prove exact geometry, physical holes or
cross-file identity. Auto application remains false. Target-version CI and
combined candidate results are recorded separately in the R11 benchmark PR.
