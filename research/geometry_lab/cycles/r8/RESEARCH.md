# R8 pre-registration: tapered intermediate-ring density (no boundary mutation)

## Decision recorded before R8 fresh holdout execution

- **Research question:** R7 uses one uniform k=max(n,m,12) vertices at each of 3 intermediate rings. For n=37,m=12, the last 37-to-12 fan creates elongated triangles and fails q=0.061831 <0.1, even though CGAL reports no crossings and shape error passes.
- **Only candidate:** tapered density per internal ring h/4: `k_h=max(12,round((1-u)*len(a)+u*len(b)))`, `u=h/4`, with independently sampled 3D radial source contours at each ring's k_h angles. Keep R7 seam choice, _ordered3d/_ray_sample3d/_connect and 3 cuts. No boundary coordinates or original boundary edge modifications. No remeshing or optimizing after the holdout. This is *adaptive to relative endpoint vertex counts*, not curvature-based meshing. It can yield varying face counts.
- **Already-seen diagnostic only:** an offline reproduction from the R7 saved raw mesh artifacts was tried on the 4 development and 6 previous R7 holdouts (ALL are now seen/development): all 10 existing min triangle quality scores increased; old R7 `r7_slender_offset` from 0.06183 to ~0.12952 on that offline reproduction. This helped select the one frozen design but is *not* fresh holdout proof or CGAL-verified.
- **Comparators:** frozen R7 `warped_radial_loft`, and official Blender 4.4.3 native 3-cut LINEAR. Same original nonplanar inputs converted to float32, 1 warmup + 3 timed runs each.
- **Synthetic split:** all R7 10 old cases count as **seen development**. Six new R8 holdout cases, separately authored in `cycles/r8/fixtures.py`, are frozen before first benchmark. No user/private/third-party models. No tuning on these.
- **Oracle and geometry:** external CGAL self-intersections=0; exact original 3D boundary vertices **and boundary edge coordinate sets**; component=1, Euler=0, nonmanifold=0; min triangle quality>=0.1, 3D analytic sampled loft RMS<=0.12, max<=0.28 (the same researcher-authored target as R7). Keep min-quality deltas and absolute values for failures. Face-count and run time are diagnostic not production time.
- **Gate set now:** (1) old failing `r7_slender_offset` q>=0.1 and full quality pass; (2) no regression among 9 prior R7 successes; (3) R8 new holdout pass count >= frozen R7 pass count and at least 4/6; (4) min-quality improves by >=0.015 on at least **2** new R8 cases; (5) CGAL crossings=0 and topology/boundary checks hold for every generated R8 result. No per-case "best of method" selection. If any condition fails, report not adopted even if average score improves.
- **Budget:** 16 fixtures × 3 methods = 48 mesh configurations, 3 timed repeats each and one warmup, one Blender 4.4.3 and independent CGAL eval per shape. ≤10 s each, existing 60,000 vertex / 20,000 face guard. 14 minute job max. No R9 auto-start.
- **Limitations:** XY radial/star-shaped, global Z-separated boundaries only; no arbitrary 3D contour orientation, UV, normals, existing editable mesh, third-party validation, or production user study. No argument that adaptive ring counts always wins. Candidate explicitly `approved=false`, PR #114 stays Draft and unmerged.

## Reproduction

```bash
# within research/geometry_lab using official SHA256-verified Blender 4.4.3
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r8/blender_run.py -- --output runs/ci-r8-raw.json
python -m cycles.r8.evaluate --input runs/ci-r8-raw.json --output runs/ci-r8-eval.json
```

After first holdout, algorithm and cases are frozen; errors or bad configurations are counted as not verified rather than dropped. Only research-owned files and dedicated Geometry Lab workflow may change, not R1–R7 results, main, ABCD, Development Intelligence Lab, STATE or Handoff.
