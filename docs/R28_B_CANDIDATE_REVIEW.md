# R28 B — fixed measured-candidate review

Base ae0531946b402c372242623c19d83fd97adf1cd0, #125 revision 24 active.
Internal pure evaluator, no source/GLB I/O, execution, copy changes, search
or automatic application. Reuses R27's fixed two-part measurement validator
and GLB-022's bounded review/strict improvement/protected-part veto principles
and four-attempt limit. The old surface-distance metric is not a dimension
metric; do not reuse its threshold.

A/D integration contract:
`from cbdk.parameter_candidate_review_r28 import review_fixed_candidates`
`review_fixed_candidates(baseline, target, trials, budget=4)`
baseline and target: R27 measurements with exactly glb_sha256, generated_mesh,
imported_glb_mesh; each phase contains the fixed Sphere and BevelCube rows
with mesh_vertex_count, mesh_polygon_count, mesh_coordinate_sha256,
world_dimensions. trials: ordered list of {trial_id, measurement}, at most
budget entries; IDs wrong_direction, cross_part, intermediate, target.
Use actual independently bound measurements, not assertion flags. No caller
best or claimed decision accepted. The evaluator does not establish run,
source, GLB authenticity or restoration; A/D must establish those first.

Output case_id, status, stop_reason, reason_codes, budget, validated_attempts,
margin, baseline_scores, trials, best_trial_id, best_scores,
observed_target_reached, safety. Score dict keys generated_mesh and
imported_glb_mesh, raw max absolute axis difference (no rounding beyond
existing measurements). Per row trial_id, decision, scores, protected_unchanged
and target_measurement_match (phase->bool), accepted_as_measured_progress,
best_trial_before, best_trial_after. All safety flags false. Initial virtual
best baseline; protected cube full measurement equality first, then strict
improvement/regression by >1e-5 in both phases. Mixed, tie, insufficient
difference or dimensions-only match is uncertain and leaves best unchanged.
Only fourth trial with full target match, unchanged cube and strict progress
can stop as observed_target_reached. Early apparent target is uncertain.
GLB SHA equality is not required for matching mesh observations.
Budget 1/2/3: review the measured prefix only, budget_exhausted when consumed.
Missing suffix/last None -> incomplete, invalid or reordered or forged
record -> rejected (no best claim); all supplied prefix rows validated first.
No physical source ever adopts virtual best.

Python synthetic controls: expected four decisions and scores, prefix budgets,
protected veto either phase, ties/mixed/margin, dimensions-only/early target,
missing/invalid evidence, bool/nonfinite, wrong order/duplicate, forged best,
different valid GLB SHA. These are controls, not native measurements.
B's specialist Blender gate is existing R26/R27 regression only; actual R28
4x3 isolated-copy measurements, independent linkage/replay belong to C/D/A.
No shared CI/CLI, fixture or other team edits. CI pending.
