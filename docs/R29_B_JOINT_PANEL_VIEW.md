# R29 B — fixed rotary panel projection

Base 8f0659c19e89869f600403bd8422b50b25af273c, #125 revision 26 active.
A/C adapter contract: pure Python, no bpy, provider imports, execution, files,
new geometry/score calculations, operator dispatch or state mutations.

`from cbdk.joint_panel_view_r29 import project_joint_panel`
`view = project_joint_panel(status, reason, result_json, current_rows, current_inputs_match=bool_value, selected_index=0)`

status/reason/result_json are the existing joint_preview RNA values. current_rows
is None if no current scene RUNS, otherwise list (max 3) of exact keys id,
diameter, decision, score, accepted_for_review extracted from the current RUNS
rows (diameter/id at row level; decision/score/accepted_for_review from review).
The adapter must independently check the complete current inputs (fixed 5/4,
policy, scene signature, provider paths, history validity); the explicit bool
is not inferred from serialized result. selected_index is current RNA candidate
index. No provider calls or scene signature calculations inside B.

Output dict: fixture_id=joint_rotary_fixture_v1, part_ids=[rotary_outer,
rotary_axle], recipe_label="固定人工回転関節", status, reason, availability
("available"/"unavailable"), candidates (fresh copied summary list),
selected_index (int or None), actions (dict of bool RUN/RETRY/CANCEL/REJECT/
ADOPT/RESTORE). IDs are roles, not catalog IDs. Recipe and part labels fixed;
axis Z, origin, scale=1, axle=2 and gap=.4 remain existing fixed fixture contract.
UI flags are not permissions; existing operator guard is always final.

READY/NO_CANDIDATE require matching current RUNS summaries and bounded parsed
result_json. Strict fixed enum, finite numeric values, ordered unique IDs,
complete sequence/early target, LOCKED empty sequence, best/status and
accepted_for_review consistency, explicit false approval flags. No geometry
or score recomputation, no validation of actual provider measurement from
display summaries, no display of raw JSON/signature/provider paths. Unknown
reason mapped to reason_unavailable, unknown state to UNAVAILABLE. Reject
duplicate JSON keys, nonfinite constants, oversize/malformed data; stale or
missing candidate data unavailable and adoption disabled. RUNNING takes
priority (CANCEL only); BLOCKED takes priority (all false); IDLE/RESTORED RUN;
FAILED/CANCELLED/REJECTED explicit RETRY and RESTORE; ADOPTED_DIMENSION_ONLY
RESTORE; READY/NO_CANDIDATE RETRY/REJECT/RESTORE plus ADOPT only for a
fresh selected accepted READY row. RESTORE always delegated to the existing
operator, never a B action. Non-ready states never expose stale candidates.

Seven synthetic Python tests cover fixed IDs, selected accepted/rejected,
busy/blocked precedence, explicit retry/restore, stale/missing/contradictory
inputs, malformed/duplicate/nonfinite/unknown data, LOCKED/no-candidate and
false approval. Tests are not provider/native GUI evidence. B specialist CI
must retain existing 3-version native regression; A connects actual B/C/D
with fixed provider and separate GUI/native evidence. CI pending. No C/D,
shared CI, catalog, registry, existing panel, official release changes.
