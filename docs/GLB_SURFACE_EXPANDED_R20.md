# R20 / F019-01 — explicit expanded surface review (candidate)

Base 547678bfec9b4c1d11aa9d7fb828977ab6d89119; #125 revision 8 active, B-only.
Default legacy_512 path remains schema 1, unchanged CLI. Opt-in Python API:
`run_glb_surface_review(blender, ref, cand, output, profile="expanded_2048")`.
The parent passes the fixed profile name to the trusted Blender subprocess. A owns
the public CLI hook; no shared CLI or CI change in this PR.

## Candidate implementation and verification status

- One canonical validation per input, two deterministic BVH builds shared by fixed
  and adaptive comparisons; all four directed comparisons keep existing sample rules.
- 2048 triangles per input scene is a candidate ceiling, not verified capacity.
  The existing 24 MiB/100000 vertex-reference preflight and parent timeout remain.
- The cumulative sample ceiling 131872 derives from 2*2048*(24+8)+2*10*(48-8).
  Node visits 8000000 and precise triangle evaluations 4000000 are provisional,
  code-owned ceilings pending real measurements; no user-supplied work limits.
  Nodes popped (including pruned pops) and precise distance calls are counted.
  Input size bounds build/feature collection; parent timeout also covers import.
- Work exhaustion returns skipped/not_measured and no partial distance metrics;
  the parent checks status, counts, nested schema, safety, finite metrics,
  sample/evaluation totals and exhaustion evidence. Timeout rejects the report.
- Native smoke adds synthetic 512/1024/2048 scenes, warmup+3 same-condition parent
  roundtrip timings, alternative triangulation, analytic Z=.25 displacement,
  2x2 planar opening with max distance <=1, legacy parity and cap, 2049 rejection,
  dense-overlap budget refusal and original GLB SHA preservation. Core tests
  include a small exhaustive control and forged report/counter negatives.
- No native measurements or CI claims until exact HEAD actual job logs succeed.
  Timing includes Blender startup/import and is not a speedup guarantee; native
  memory and user GLB accuracy remain unmeasured. Fixed vs adaptive metrics
  are separate; a sampled zero is never exact geometry identity.
- No GL research adoption, private inputs, part matcher/viewer expansion,
  automatic source changes, or formal release. All existing gates remain.
