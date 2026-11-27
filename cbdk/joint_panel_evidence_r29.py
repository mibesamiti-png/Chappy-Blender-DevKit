"""R29 fixed joint panel evidence; no bpy, provider loading or UI authority.

The trusted parent separately observes actual state/operations and the panel
projection. Stub and callback observations never certify production GUI input.
Uses the existing joint integration proposal/number contracts, not a new solver.
"""
from __future__ import annotations

from math import isfinite

from .extension_stage_evidence import VERSIONS, _is_digest
from .parameter_fixture_evidence import _HEX32
from .joint_integration import proposals, number
from .parameter_source_evidence_r27 import _record, _bound, _flags, _fail

FIXTURE = "joint_rotary_fixture_v1"
PARTS = ("rotary_outer", "rotary_axle")
RECIPE = "fixed_rotary_fixture"
STATES = ("IDLE", "RUNNING", "READY", "NO_CANDIDATE", "FAILED", "CANCELLED",
          "REJECTED", "BLOCKED", "ADOPTED_DIMENSION_ONLY", "RESTORED")
REASONS = ("", "provider_configuration_failed", "provider_or_geometry_failure",
           "local_providers_missing", "provider_paths_changed_restart_required",
           "local_provider_hash_mismatch", "external_provider_already_loaded",
           "external_geometry_already_loaded", "provider_size", "provider_path",
           "object_mode_required", "synthetic_origin_required", "synthetic_unit_scale_required",
           "numeric_constraints_unsatisfied", "stale_inputs", "no_current_candidate",
           "rejected_candidate", "fresh_measurement_changed", "cancellation_requested",
           "cancelled_between_trials", "context_scene_changed", "restoration_blocked",
           "history_changed_rerun_required", "cleanup_or_source_changed", "rollback_failed",
           "rna_readback_mismatch", "post_write_changed", "injected_generation_failure",
           "injected_boolean_failure", "injected_interruption", "face_budget_exceeded",
           "gl_unknown_or_intersecting", "unavailable")
DECISIONS = ("regression", "observed_improvement", "target_reached", "uncertain",
             "protected_part_regression", "axial_dimension_regression")
ACCEPTED = ("observed_improvement", "target_reached")
ACTIONS = ("START", "CANCEL", "RETRY", "REJECT", "ADOPT", "RESTORE")
OPERATORS = {"START": "cbdk_a.joint_start", "CANCEL": "cbdk_a.joint_action",
             "RETRY": "cbdk_a.joint_action", "REJECT": "cbdk_a.joint_action",
             "ADOPT": "cbdk_a.joint_dimension", "RESTORE": "cbdk_a.joint_dimension"}
# Independent fixed scenarios. Each starts from the same protected artificial scene;
# parent may prepare the specified starting state using existing operators.
CASES = {
    "adopt_restore": ("START", "COMPLETE", "ADOPT", "RESTORE"),
    "rejected_candidate": ("ADOPT",),
    "stale_candidate": ("ADOPT",),
    "cancel_retry": ("START", "ADOPT", "RESTORE", "CANCEL", "INTERRUPT", "RETRY"),
    "failed_retry": ("START", "FAIL", "RETRY"),
    "blocked": ("START", "CANCEL", "RETRY", "REJECT", "ADOPT", "RESTORE"),
    "explicit_reject": ("REJECT",),
}
IDENTITY = {"run_id", "blender_version", "fixture_id", "mode"}
SNAPSHOT = {"status", "reason", "diameter", "fresh", "selected", "candidates", "scene_sha", "target", "policy", "cancel_requested"}
VIEW = {"fixture_id", "part_ids", "recipe_id", "status", "reason", "available",
        "candidates", "selected", "enabled_actions"}
ROW = {"candidate_id", "diameter", "decision", "score", "accepted_for_review"}
STEP = {"index", "action", "operator", "method", "explicit", "result", "before",
        "after", "view_before", "view_after"}
CASE_FIELDS = IDENTITY | {"case", "steps"}
LIFECYCLE = {"registered", "duplicate_rejected", "unregistered",
             "existing_registration_unchanged", "scene_before", "scene_after", "fixture_settings", "draw_method", "projection_source"}
MODES = ("stub", "native")
METHODS = ("stub", "native_operator", "native_iterator", "callback_simulation")


def _enum(value, choices):
    return type(value) is str and value in choices


def _identity(run_id, blender_version, mode):
    if (type(run_id) is not str or _HEX32.fullmatch(run_id) is None
            or not _enum(blender_version, VERSIONS) or not _enum(mode, MODES)):
        _fail("identity_mismatch")
    return dict(run_id=run_id, blender_version=blender_version, fixture_id=FIXTURE, mode=mode)


def _dimension(value):
    if type(value) not in (int, float) or not 3.6 <= value <= 10:
        _fail("dimension_invalid")
    return number(value)


def _score(value):
    return type(value) in (int, float) and 0 <= value <= 100 and isfinite(value)


def _rows(rows):
    if type(rows) is not list or len(rows) > 3:
        _fail("candidate_inventory_invalid")
    expected = proposals(5., 4., "FREE")
    for index, row in enumerate(rows):
        _record(row, ROW)
        candidate_id, diameter = expected[index]
        if (row["candidate_id"] != candidate_id or _dimension(row["diameter"]) != diameter
                or not _enum(row["decision"], DECISIONS) or not _score(row["score"])
                or type(row["accepted_for_review"]) is not bool
                or row["accepted_for_review"] != (row["decision"] in ACCEPTED)):
            _fail("candidate_invalid")
        if row["decision"] == "target_reached" and row["score"] > 1e-5:
            _fail("candidate_invalid")
        if row["decision"] == "target_reached" and index != len(rows)-1:
            _fail("candidate_order_invalid")


def _snapshot(s, scene_sha):
    _record(s, SNAPSHOT)
    if not _enum(s["status"], STATES) or not _enum(s["reason"], REASONS):
        _fail("state_invalid")
    _dimension(s["diameter"])
    if _dimension(s["target"]) != 4. or s["policy"] != "FREE":
        _fail("fixture_settings_mismatch")
    _flags(s, {"fresh", "cancel_requested"})
    _rows(s["candidates"])
    selected = s["selected"]
    if selected is not None and (type(selected) is not int or not 0 <= selected < len(s["candidates"])):
        _fail("selection_invalid")
    if s["fresh"] and (s["status"] != "READY" or len(s["candidates"]) != 3
                       or not any(row["accepted_for_review"] for row in s["candidates"])):
        _fail("freshness_invalid")
    if not _is_digest(s["scene_sha"]) or s["scene_sha"] != scene_sha:
        _fail("scene_changed")


def _can_adopt(s):
    return (s["status"] == "READY" and s["fresh"] and s["selected"] is not None
            and s["candidates"][s["selected"]]["accepted_for_review"])


def _view(v, s):
    _record(v, VIEW)
    if (v["fixture_id"] != FIXTURE or v["part_ids"] != list(PARTS)
            or v["recipe_id"] != RECIPE or v["status"] != s["status"]
            or not _enum(v["reason"], REASONS) or v["reason"] != s["reason"]):
        _fail("projection_mismatch")
    _flags(v, {"available"})
    _rows(v["candidates"])
    if v["available"]:
        if v["candidates"] != s["candidates"] or v["selected"] != s["selected"]:
            _fail("projection_mismatch")
        if v["selected"] is not None and type(v["selected"]) is not int:
            _fail("selection_invalid")
    elif v["candidates"] or v["selected"] is not None:
        _fail("projection_mismatch")
    if s["status"] == "READY" and not s["fresh"] and v["available"]:
        _fail("stale_projection")
    if s["fresh"] and not v["available"]:
        _fail("projection_mismatch")
    enabled = v["enabled_actions"]
    if (type(enabled) is not list or any(not _enum(x, ACTIONS) for x in enabled)
            or len(set(enabled)) != len(enabled)):
        _fail("operation_invalid")
    enabled = set(enabled)
    status = s["status"]
    if status == "BLOCKED":
        if enabled:
            _fail("blocked_operation")
        return
    if status == "RUNNING":
        if enabled != {"CANCEL"}:
            _fail("busy_operation")
        return
    allowed = {"RESTORE"}
    required = set()
    if status in ("FAILED", "CANCELLED", "REJECTED", "NO_CANDIDATE"):
        allowed.add("RETRY")
        required.add("RETRY")
    else:
        allowed.add("START")
        if status == "IDLE":
            required.add("START")
    if status == "READY":
        allowed.add("REJECT")
    if _can_adopt(s) and v["available"]:
        allowed.add("ADOPT")
        required.add("ADOPT")
    if status == "ADOPTED_DIMENSION_ONLY":
        required.add("RESTORE")
    if not required <= enabled <= allowed:
        _fail("operation_invalid")


def _step(step, index, action, case, identity, scene_sha):
    _record(step, STEP)
    if type(step["index"]) is not int or step["index"] != index or step["action"] != action:
        _fail("step_order_mismatch")
    if step["operator"] != OPERATORS.get(action):
        _fail("delegation_mismatch")
    method = step["method"]
    if not _enum(method, METHODS):
        _fail("method_invalid")
    if identity["mode"] == "stub":
        if method != "stub":
            _fail("method_invalid")
    elif action in OPERATORS:
        if method != "native_operator":
            _fail("method_invalid")
    elif method not in ("native_iterator", "callback_simulation"):
        _fail("method_invalid")
    # Callback simulations can test interruption/failure, never successful native generation.
    if action == "COMPLETE" and identity["mode"] == "native" and method != "native_iterator":
        _fail("method_invalid")
    _flags(step, {"explicit"})
    if step["explicit"] != (action in OPERATORS):
        _fail("explicit_operation_required")
    result = step["result"]
    if not _enum(result, ("FINISHED", "CANCELLED", "RUNNING_MODAL")):
        _fail("result_invalid")
    before, after = step["before"], step["after"]
    _snapshot(before, scene_sha); _snapshot(after, scene_sha)
    _view(step["view_before"], before); _view(step["view_after"], after)
    a,b = before["status"], after["status"]
    diameter_before, diameter_after = before["diameter"], after["diameter"]
    if case == "blocked":
        if (a,b,result) != ("BLOCKED","BLOCKED","CANCELLED") or before["fresh"] or after["fresh"]:
            _fail("blocked_operation")
    elif case == "cancel_retry" and action in ("ADOPT", "RESTORE"):
        if (a,b,result) != ("RUNNING","RUNNING","CANCELLED") or after["cancel_requested"] != before["cancel_requested"]:
            _fail("busy_operation")
    elif case in ("rejected_candidate", "stale_candidate"):
        if (a != "READY" or _can_adopt(before) or result != "CANCELLED"
                or b not in ("FAILED", "READY") or after["fresh"] and b != "READY"):
            _fail("invalid_adoption")
        if case == "rejected_candidate":
            if (not before["fresh"] or before["selected"] is None
                    or before["candidates"][before["selected"]]["accepted_for_review"]):
                _fail("invalid_adoption")
        elif before["fresh"]:
            _fail("invalid_adoption")
    elif action == "START":
        if (a,b,result) != ("IDLE","RUNNING","RUNNING_MODAL") or after["cancel_requested"]:
            _fail("state_transition_invalid")
    elif action == "RETRY":
        # Existing joint_action(RETRY) is synchronous, unlike joint_start.
        if a not in ("FAILED","CANCELLED") or b != "READY" or result != "FINISHED" or not after["fresh"]:
            _fail("state_transition_invalid")
        if after["cancel_requested"] or [r["decision"] for r in after["candidates"]] != ["regression","observed_improvement","target_reached"]:
            _fail("fixed_review_mismatch")
    elif action == "COMPLETE":
        if (a,b,result) != ("RUNNING","READY","FINISHED") or not after["fresh"]:
            _fail("state_transition_invalid")
        if [r["decision"] for r in after["candidates"]] != ["regression","observed_improvement","target_reached"]:
            _fail("fixed_review_mismatch")
    elif action == "ADOPT":
        if (a,b,result) != ("READY","ADOPTED_DIMENSION_ONLY","FINISHED") or not _can_adopt(before):
            _fail("invalid_adoption")
        if (diameter_before != 5. or before["candidates"][before["selected"]]["candidate_id"] != "declared_target"
                or diameter_after != before["candidates"][before["selected"]]["diameter"] or diameter_after != 4.):
            _fail("dimension_transition_invalid")
    elif action == "RESTORE":
        if (a,b,result) != ("ADOPTED_DIMENSION_ONLY","RESTORED","FINISHED") or (diameter_before,diameter_after)!=(4.,5.):
            _fail("restoration_invalid")
    elif action == "CANCEL":
        if (a,b,result) != ("RUNNING","RUNNING","FINISHED") or not after["cancel_requested"]:
            _fail("state_transition_invalid")
    elif action in ("INTERRUPT","FAIL"):
        expected = "CANCELLED" if action == "INTERRUPT" else "FAILED"
        if (a,b,result) != ("RUNNING",expected,"CANCELLED") or (action == "INTERRUPT" and not before["cancel_requested"]):
            _fail("state_transition_invalid")
    elif action == "REJECT":
        if (a,b,result) != ("READY","REJECTED","FINISHED"):
            _fail("state_transition_invalid")
    if not (case == "adopt_restore" and action in ("ADOPT","RESTORE")):
        if diameter_before != 5. or diameter_after != diameter_before:
            _fail("unexpected_dimension_change")
    if after["fresh"] and b != "READY":
        _fail("freshness_invalid")


def _summary(status, reasons, identity=None, cases=(), methods=()):
    return dict(schema_version=1, suite="fixed_joint_panel_evidence_r29", status=status,
                reason_codes=list(reasons), **(identity or dict.fromkeys(sorted(IDENTITY))),
                verified_cases=list(cases), observed_methods=sorted(set(methods)),
                native_fixed_panel_evidence_verified=status=="verified_native_observations",
                stub_contract_verified=status=="verified_stub_contract",
                safety=dict(authenticates_observations=False, production_panel_gui_click_verified=False,
                            windows_gui_verified=False, native_undo_redo_verified=False,
                            arbitrary_model_verified=False, mesh_commit=False, auto_apply=False,
                            auto_adopt=False, auto_approve=False, provider_distribution_authorized=False))


def reduce_panel_evidence(records, *, run_id, blender_version, mode, scene_sha,
                          measured, lifecycle, measured_lifecycle):
    """Independent parent identity, measured cases and lifecycle required.

    The parent must capture real operator returns, RNA and scene signatures,
    actual view and delegation, not infer observations from expected outcomes.
    Each case is a separate prepared scenario, not a single continuous run.
    Stub observations cannot certify native panel operations or GUI events.
    No raw paths, arbitrary JSON, external providers or execution here.
    """
    try:
        identity = _identity(run_id, blender_version, mode)
        if not _is_digest(scene_sha):
            _fail("scene_digest_invalid")
        records = [] if records is None else records
        measured = {} if measured is None else measured
        if (type(records) is not list or len(records) > len(CASES)
                or type(measured) is not dict or not set(measured) <= set(CASES)):
            _fail("case_inventory_invalid")
        missing = []
        for value in (lifecycle, measured_lifecycle):
            if value is None:
                missing.append("lifecycle_missing")
                continue
            _record(value, IDENTITY | LIFECYCLE)
            _bound(value, identity)
            boolean_fields = {"registered", "duplicate_rejected", "unregistered", "existing_registration_unchanged"}
            _flags(value, boolean_fields)
            if not all(value[k] for k in boolean_fields):
                _fail("lifecycle_unverified")
            fixture = value["fixture_settings"]
            _record(fixture, {"axis", "origin", "unit_scale", "axle_diameter", "clearance", "mode"})
            if (fixture["axis"] != "Z" or fixture["mode"] != "OBJECT"
                    or type(fixture["origin"]) is not list or len(fixture["origin"]) != 3
                    or any(type(x) not in (int, float) or x != 0 for x in fixture["origin"])
                    or any(type(fixture[k]) not in (int, float) or abs(fixture[k]-expected)>1e-6
                           or not isfinite(fixture[k]) for k,expected in (("unit_scale",1.),("axle_diameter",2.),("clearance",.4)))):
                _fail("fixture_settings_mismatch")
            draw = "native_panel_draw_recording_layout" if mode == "native" else "stub"
            projection = "real_projection" if mode == "native" else "stub"
            if value["draw_method"] != draw or value["projection_source"] != projection:
                _fail("method_invalid")
            if any(value[k] != scene_sha for k in ("scene_before","scene_after")):
                _fail("scene_changed")
        if lifecycle is not None and measured_lifecycle is not None and lifecycle != measured_lifecycle:
            _fail("parent_measurement_mismatch")
        verified, methods = [], []
        for index, record in enumerate(records):
            case = tuple(CASES)[index]
            for observed in (record, measured.get(case)):
                if observed is None:
                    missing.append("parent_measurement_missing")
                    continue
                _record(observed, CASE_FIELDS)
                _bound(observed, identity)
                if observed["case"] != case:
                    _fail("case_order_mismatch")
                steps = observed["steps"]
                if type(steps) is not list or len(steps)>len(CASES[case]):
                    _fail("step_order_mismatch")
                if len(steps)!=len(CASES[case]):
                    missing.append("step_missing")
                for j, step in enumerate(steps):
                    _step(step,j,CASES[case][j],case,identity,scene_sha)
                    if j and (steps[j-1]["after"] != step["before"]
                              or steps[j-1]["view_after"] != step["view_before"]):
                        _fail("transition_discontinuity")
            if case in measured:
                if record != measured[case]:
                    _fail("parent_measurement_mismatch")
                if len(record["steps"])==len(CASES[case]):
                    verified.append(case)
                    methods.extend(step["method"] for step in record["steps"])
        if set(measured)-set(tuple(CASES)[:len(records)]):
            _fail("case_order_mismatch")
        if len(verified)!=len(CASES):
            missing.append("case_missing")
        if missing:
            return _summary("incomplete",dict.fromkeys(missing),identity,verified,methods)
        status = "verified_native_observations" if mode=="native" else "verified_stub_contract"
        return _summary(status,[],identity,verified,methods)
    except ValueError as exc:
        return _summary("rejected",[str(exc)])
