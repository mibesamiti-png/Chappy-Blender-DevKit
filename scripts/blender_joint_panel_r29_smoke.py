"""R29 native panel registration / draw recorder / existing operator boundary.

The projection is a fixed test stub, the layout is a recorder, not a GUI click.
Existing provider native regression runs independently in the original smoke.
"""
import json
from types import SimpleNamespace as NS

import bpy
from parts.blender import joint_preview as preview
from parts.blender import joint_panel_r29 as panel


def stub_projection(**source):
    return dict(fixture_id=panel.FIXTURE_ID, part_ids=list(panel.PART_IDS),
                recipe_label=panel.RECIPE_LABEL, status=source["status"],
                reason=source["reason"], available=source["status"] in panel.STATUSES,
                candidates=source["candidates"], current_inputs_match=source["current_inputs_match"],
                can_adopt=source["status"] == "READY" and source["current_inputs_match"])


class Layout:
    """Record actual Panel.draw calls; does not simulate user clicks."""
    def __init__(self, log=None):
        self.log = [] if log is None else log
        self.operator_context = "EXEC_DEFAULT"

    def label(self, **kwargs):
        self.log.append(dict(kind="label", **kwargs))

    def prop(self, settings, key, **kwargs):
        self.log.append(dict(kind="prop", key=key, **kwargs))

    def row(self):
        return Layout(self.log)

    def operator(self, op_id, **kwargs):
        call = NS(kind="operator", op_id=op_id, invocation=self.operator_context, **kwargs)
        self.log.append(call)
        return call


def capture_draw(context):
    """A may use this recorder with real projection, or actual GUI separately."""
    layout = Layout()
    panel.CBDK_PT_joint_panel_r29.draw(NS(layout=layout), context)
    return [vars(row) if isinstance(row, NS) else row for row in layout.log]


def bindings(trace):
    return [(row["op_id"], row.get("action"), row["invocation"])
            for row in trace if row["kind"] == "operator"]


def run_stub_smoke(output):
    if not bpy.app.background or preview.OWNED or panel.OWNED:
        raise AssertionError("R29 fresh native smoke required")
    origin = preview.scene_signature(bpy.context)
    handlers_before = {name: tuple(getattr(bpy.app.handlers, name))
                       for name, _ in preview.HISTORY_HANDLERS}
    records = []
    preview.register()
    try:
        s = bpy.context.scene.cbdk_a_joint
        s.diameter, s.target, s.policy = 5., 4., "FREE"
        s.restore_diameter = 5.
        s.status, s.reason, s.result_json = "IDLE", "", ""
        s.provider_zip, s.geometry_root = "", ""
        s.cancel_requested = False
        panel.register(stub_projection)
        try:
            assert panel.CBDK_PT_joint_panel_r29.is_registered
            assert all(cls.is_registered for cls in preview.CLASSES)
            try:
                panel.register(stub_projection)
                raise AssertionError("duplicate panel accepted")
            except RuntimeError as error:
                assert str(error) == "r29_duplicate_or_foreign_panel"

            def check(case, expected):
                trace = capture_draw(bpy.context)
                assert bindings(trace) == [panel.OPERATOR_BINDINGS[a] for a in expected], trace
                records.append(dict(case=case, status=s.status, bindings=bindings(trace),
                                    labels=[row["text"] for row in trace if row["kind"] == "label"],
                                    candidate_selector=any(row["kind"] == "prop" and row["key"] == "candidate" for row in trace)))

            check("idle", ["START"])
            s.status = "RUNNING"
            check("running", ["CANCEL"])
            assert bpy.ops.cbdk_a.joint_action(action="CANCEL") == {"FINISHED"}
            assert s.cancel_requested and s.status == "RUNNING" and s.diameter == 5.
            # Controlled callback at the next timer boundary; not a GUI event.
            timer = object(); removed = []
            op = NS(_scene=bpy.context.scene, _timer=timer,
                    _steps=preview.iter_run(bpy.context, s), _epoch=preview.HISTORY_EPOCH)
            ctx = NS(scene=bpy.context.scene, window_manager=NS(event_timer_remove=removed.append), area=None)
            assert preview.CBDK_A_OT_start.modal(op, ctx, NS(type="TIMER")) == {"CANCELLED"}
            assert removed == [timer] and s.status == "CANCELLED"
            check("cancelled", ["RETRY", "RESTORE"])
            # Existing retry rejects missing or changed provider configuration.
            assert bpy.ops.cbdk_a.joint_action(action="RETRY") == {"CANCELLED"}
            assert s.status == "FAILED" and s.diameter == 5.
            check("failed", ["RETRY", "RESTORE"])
            s.status, s.reason = "READY", ""
            fake = dict(original=5., target=4., policy="FREE", signature=preview.scene_signature(bpy.context),
                        rows=[dict(id="negative_control", diameter=5.5, review=dict(decision="regression", score=1.5, accepted_for_review=False)),
                              dict(id="midpoint", diameter=4.5, review=dict(decision="observed_improvement", score=.5, accepted_for_review=True)),
                              dict(id="declared_target", diameter=4., review=dict(decision="target_reached", score=0., accepted_for_review=True))], best=2)
            key = bpy.context.scene.as_pointer()
            preview.RUNS[key] = fake
            s.result_json = json.dumps(fake)
            s.candidate = 0
            check("ready_rejected_row", ["REJECT", "RESTORE"])
            s.candidate = 2
            check("ready_current_row", ["ADOPT", "REJECT", "RESTORE"])
            s.target = 4.25
            check("ready_stale", ["REJECT", "RESTORE"])
            s.target = 4.
            # No fabricated candidate is passed to provider adoption.
            preview.RUNS.clear()
            assert bpy.ops.cbdk_a.joint_dimension(action="ADOPT") == {"CANCELLED"}
            assert s.diameter == 5. and s.status == "FAILED"
            s.status = "READY"
            assert bpy.ops.cbdk_a.joint_action(action="REJECT") == {"FINISHED"}
            assert s.status == "REJECTED" and s.diameter == 5.
            check("rejected", ["RETRY", "RESTORE"])
            s.diameter = 4.
            s.status = "ADOPTED_DIMENSION_ONLY"
            check("adopted_dimension_only_stub_state", ["RESTORE"])
            assert bpy.ops.cbdk_a.joint_dimension(action="RESTORE") == {"FINISHED"}
            assert s.diameter == 5. and s.status == "RESTORED"
            check("restored", ["START", "RESTORE"])
            s.status = "BLOCKED"
            check("blocked", [])
            for action in ("RETRY", "REJECT", "CANCEL"):
                assert bpy.ops.cbdk_a.joint_action(action=action) == {"CANCELLED"}
            for action in ("ADOPT", "RESTORE"):
                assert bpy.ops.cbdk_a.joint_dimension(action=action) == {"CANCELLED"}
            assert s.status == "BLOCKED" and s.diameter == 5.
            s.status = "UNRECOGNIZED"
            check("unknown", [])
            s.status = "READY"; s.result_json = "not a projection"
            check("ready_missing", ["REJECT", "RESTORE"])
            assert preview.scene_signature(bpy.context) == origin
        finally:
            panel.unregister()
        assert not panel.CBDK_PT_joint_panel_r29.is_registered and panel._PROJECTION is None
        assert all(cls.is_registered for cls in preview.CLASSES)
        assert all(getattr(bpy.app.handlers, name).count(callback) == 1 for name, callback in preview.HISTORY_HANDLERS)
        try:
            panel.unregister()
            raise AssertionError("unowned unregister accepted")
        except RuntimeError as error:
            assert str(error) == "r29_registration_not_owned"
    finally:
        preview.unregister()
    assert not hasattr(bpy.types.Scene, "cbdk_a_joint")
    assert all(tuple(getattr(bpy.app.handlers, name)) == old for name, old in handlers_before.items())
    assert preview.scene_signature(bpy.context) == origin
    result = dict(fixture_id=panel.FIXTURE_ID, blender_version=".".join(map(str, bpy.app.version)),
                  projection_origin="fixed_stub", draw_mode="panel_draw_layout_recorder",
                  records=records, native_operator_calls=["CANCEL", "RETRY_REFUSED", "ADOPT_REFUSED", "REJECT", "RESTORE", "BLOCKED_REFUSALS"],
                  timer_boundary="controlled_callback", registration_verified=True,
                  duplicate_registration_refused=True, unregister_verified=True, existing_panel_preserved=True,
                  original_scene_unchanged=True, actual_provider_panel_chain=False, gui_clicks=False,
                  auto_adopt=False, mesh_commit=False)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print("CBDK_R29_JOINT_PANEL_STUB_PASS " + json.dumps(result, ensure_ascii=True, sort_keys=True), flush=True)
    return result
