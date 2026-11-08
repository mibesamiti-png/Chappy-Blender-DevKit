# Team B R14 — anonymous GLB cross-evidence triage (NEXT-008 / GLB-020–022)

**Source:** latest `feature/v0.18-shape-diagnostics` development HEAD
`8665a3c136ae81efbd28a820e7de50ef6ee59332`, verified to descend
from R13 integrated commit `0a306a85d6f84ef434eb6b54f12cb4ce93251a6c`.
A's R13 integration PR #104 and R14 formal milestone PR #105 were merged.
The **seven independently triggered workflow families at the exact
R14 base** were success before this B specialist branch was created.
The historical R13 individual PR #100 remains a reference, not a new
dependency or a duplicate merge.

## Purpose and practical boundary

Previously a reviewer had to switch among separate GLB metadata,
silhouette IoU, open-edge audit, sampled surface, and static AST
property-candidate reports. The new **pure Python, no-I/O**
`cbdk.glb_evidence_triage.build_glb_evidence_triage(...)`
collects bounded, **anonymous** facts in one review-only result.

This does **not** combine the reports into a new geometry oracle. In
particular the reports could have been made from different GLB files,
builds or runs. The function **does not verify** that their provenance
matches and always marks
`evidence_sources_verified_same_run=false`. Callers must verify
input provenance separately before using aggregate observations
as a human investigation aid. The API never accesses user files,
Blender, a network, AST original source, or writes report files.

Use with already generated, locally available CBDK aggregate dicts:

```python
from cbdk.glb_evidence_triage import build_glb_evidence_triage

review = build_glb_evidence_triage(
    comparison=scene_comparison,          # optional cbdk_glb_scene_comparison
    boundary_reference=ref_audit,         # optional, paired boundary_audit outputs
    boundary_candidate=cand_audit,
    sampled_surface=sampled_report,       # optional CBDK surface-distance report
    static_property_triage=private_ast_review,  # optional validated existing triage
)
assert review["status"] == "review_only"
assert not review["safety"]["auto_apply"]
```

No new CLI or common UI is included; A would need to approve any
shared-orchestrator/UI integration separately.

## The five separate channels

| Channel | Anonymous output | What is explicitly **not** established |
| --- | --- | --- |
| `metadata_differences` | Count of severity, known difference code vocabulary, number of unknown codes; whether metadata comparison passed | Metadata success is not geometric equality, model names/paths never copied |
| `silhouette_iou` | Count of measured views and worst IoU on reported masks | Unmeasured views remain `not_measured`, IoU=1 does not prove missing holes/internal surface equality |
| `boundary_counts` | Reference/candidate observed boundary and weld-collapse counts; differing aggregate fields | Equal counts are not edge layout, hole location, watertightness, or part identity; no raw segments |
| `sampled_surface_distance` | Sampled max/observed signal or explicit skipped triangle-limit | Samples may miss small openings and cavities; no exact Hausdorff/volume proof |
| `static_property_candidates` | Count of already validated AST-syntax families and ambiguous families | No declaration names, source labels, selected property, parameter effect or source execution |

Missing channels are returned as `status="not_measured"` and collected
in `unobserved_channels`; surface-limit skips remain unmeasured rather
than "same". A reported zero difference is `no_difference_reported`,
not "equivalent". Observed changes contribute only to an ordered
`review_topics` list; the list is **not** a ranking of causes.

Validation is conservative: existing GLB diagnosis and private AST
triage validators are reused; comparison errors/warnings/info counts
and Boolean `passed` must agree; IoU must be finite in [0,1].
Boundary parts must be anonymous, well formed and individually/combined
under 64 parts / 512 triangles, with row-level incidence and totals
consistent and proof flags false. A surface report must be one of
the two known CBDK schema shapes, show only finite sampled values and
false authorization flags, and a skipped surface must not pretend
to contain measured values. Unknown difference codes are counted
rather than copied into user-visible data. All output keys are fixed;
no object labels, model filenames, source paths, coordinates,
candidate source declarations, private snippets or raw report sections
are passed through.

`auto_apply`, `authorizes_parameter_values`,
`proves_part_identity`, `proves_exact_geometry`,
`proves_causality`, `authenticates_evidence` and
`licenses_or_release_approved` are all always false.

## R14 authored negative controls

`tests/test_glb_evidence_triage_r14.py` is a new pure-Python
test module. It derives all geometric evidence from CBDK-authored
triangles and CBDK's existing comparator/auditor/sampler, with
four independent conditions:

1. **Identical** planar annulus: metadata passes, IoU=1,
   boundary counts agree, sampled distance zero *at sampled points*.
   The triage must nevertheless remain review-only.
2. **Displacement**: translated annulus; changed scene/part
   centers and nonzero sampled surface distance, but an unchanged
   silhouette mask and unchanged boundary counts.
3. **Opening location**: inner rectangular opening shifted
   with identical outer bounds and the same open-edge counts.
   Synthetic IoU masks flag a difference and sampled distance
   measures a difference, while boundary counts alone cannot
   localize an opening.
4. **Missing part**: a second self-authored triangle/object is
   present only in reference; metadata reports missing object,
   aggregate part/edge counts change and sampled distances
   differ. No identity or explanation is asserted.

Further cases check exact anonymous output schema, explicit
unobserved channels, private AST family *counts only*, forged
`passed`/severity totals, NaN/Boolean IoU, contradictory
boundary audit rows, missing paired boundary evidence, forged
surface signals, triangle-limit skip, nonfinite surface distances,
raw source-name and unknown-code injection, and output invariance
to input difference ordering.

`tests/test_glb_regression.py` has one GLB-owned mocked orchestration
guard asserting that triage can *never* approve a comparison or invent
missing surface evidence. Its path is an existing trigger of the
Blender 4.4.3/4.5.15/5.2.1 CI, which runs the repository's **pre-existing
self-authored GLB export/import smoke**. The new R14 four-case
geometric regressions themselves run in Python, **not** through
newly exported native Blender R14 assets.

## Validation and release gates

Check exact specialist PR HEAD workflows: Python
3.11/3.12/3.13, Windows PowerShell 3.11/3.13,
Blender 4.4.3/4.5.15/5.2.1, Chromium offline and
Handoff. Kit/Skill must **not** be counted unless
actually triggered on this same SHA. A's combined B/C/D
HEAD and separate post-merge 7-family CI must be
reverified independently; the successful R13 and R14
baseline CI does not substitute for R14 implementation.

**Limitations:** The new API has no authenticated binding among
inputs, no native GUI integration, no end-to-end real private GLB
coverage, no true hole/solid/part equivalence validation, no
direct original-addon attribution, and no source-license or
Blender Extensions publication authority. Sampled surface evidence
can miss small features. Formal main/v0.17.0 and v0.19 are unchanged.
A owns STATE/Handoff/PROGRESS, common workflows/scripts, Notion,
main and project publication.

**R15 candidate (design only):** A-controlled, privacy-safe provenance
linkage of local aggregate report **session IDs / digest basis**
for this triage, with deliberately invalid mixed-run/mismatched
mesh-count fixtures. No raw GLB provenance or filenames in a
portable report. This would require explicit new A assignment and
independent CI; this R14 result intentionally reports
`evidence_sources_verified_same_run=false`.
