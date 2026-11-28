"""R29 A native fixed panel observations, independently checked by D.

Separate actual RNA and draw reads on both sides of each single operation.
Controlled callback pumping is not a GUI event; only actual iterator work
is marked native_iterator. No synthetic results or new production operators.
"""
import json
from pathlib import Path
from types import SimpleNamespace as NS
from uuid import uuid4

import bpy
from cbdk.joint_panel_evidence_r29 import reduce_panel_evidence, CASES
from parts.blender import joint_preview as preview, joint_panel_r29 as panel
from parts.blender import joint_panel_bridge_r29 as bridge
from scripts.blender_joint_panel_r29_smoke import capture_draw, bindings


def summary(row):
    return dict(candidate_id=row["id"], diameter=row["diameter"],
                decision=row["decision"], score=row["score"],
                accepted_for_review=row["accepted_for_review"])


def snapshot(ctx):
    s = ctx.scene.cbdk_a_joint
    p = preview.RUNS.get(ctx.scene.as_pointer())
    rows = [summary(dict(id=x["id"], diameter=x["diameter"],
                         decision=x["review"]["decision"], score=x["review"]["score"],
                         accepted_for_review=x["review"]["accepted_for_review"]))
            for x in p["rows"]] if p and s.status == "READY" else []
    sig = preview.scene_signature(ctx)
    requested = (Path(bpy.path.abspath(s.provider_zip)).resolve(),
                 Path(bpy.path.abspath(s.geometry_root)).resolve())
    fresh = bool(s.status == "READY" and p and preview.PROVIDERS is not None
                 and not preview.HISTORY_BLOCKED and requested == preview.PROVIDER_PATHS
                 and ctx.mode == "OBJECT" and tuple(ctx.scene.cursor.location) == (0.,0.,0.)
                 and ctx.scene.unit_settings.scale_length == 1.
                 and (s.diameter,s.target,s.policy,sig) ==
                     (p["original"],p["target"],p["policy"],p["signature"])
                 and s.result_json == json.dumps(p))
    return dict(status=s.status, reason=s.reason, diameter=float(s.diameter),
                target=float(s.target), policy=s.policy, fresh=fresh,
                selected=int(s.candidate) if 0 <= s.candidate < len(rows) else None,
                candidates=rows, scene_sha=sig, cancel_requested=bool(s.cancel_requested))


def observe(ctx):
    state = snapshot(ctx)
    trace = capture_draw(ctx)
    labels = [x["text"] for x in trace if x["kind"] == "label"]
    assert "joint_rotary_fixture_v1" in labels
    assert "rotary_outer：外側 / rotary_axle：軸" in labels
    assert "固定人工回転関節 — 開発プレビュー" in labels
    status = next(x.removeprefix("状態: ") for x in labels if x.startswith("状態: "))
    reason = next((x.removeprefix("理由: ") for x in labels if x.startswith("理由: ")), "")
    available = "表示データ unavailable" not in labels
    data = bridge.project(ctx, **panel.projection_input(ctx))
    rows = [summary(x) for x in data["candidates"]] if available else []
    displayed = [x for x in labels if " / 外径 " in x]
    assert displayed == [f'{x["candidate_id"]} / 外径 {x["diameter"]:.4f} / {x["decision"]} / score {x["score"]:.5f}' for x in rows]
    selector = any(x["kind"] == "prop" and x["key"] == "candidate" for x in trace)
    inverse = {v:k for k,v in panel.OPERATOR_BINDINGS.items()}
    actions = [inverse[tuple(x)] for x in bindings(trace)]
    view = dict(fixture_id=data["fixture_id"], part_ids=data["part_ids"],
                recipe_id="fixed_rotary_fixture", status=status, reason=reason,
                available=available, candidates=rows,
                selected=int(ctx.scene.cbdk_a_joint.candidate) if selector else None,
                enabled_actions=actions)
    return state, view


class ControlledContext:
    """Delegate actual Blender context; replace only the modal event scheduler."""
    def __init__(self, context):
        self.context = context
        self.timer = object()
        self.added, self.removed, self.handlers = [], [], []
        self.window_manager = NS(event_timer_add=self.add_timer,
                                 event_timer_remove=self.removed.append,
                                 modal_handler_add=self.handlers.append)
        self.area = None

    def add_timer(self, seconds, *, window):
        self.added.append(seconds)
        return self.timer

    def __getattr__(self, name):
        return getattr(self.context, name)


def run_evidence_smoke(output, zip_path, gl_root):
    ctx = bpy.context
    assert bpy.app.background and not preview.OWNED and not panel.OWNED
    identity = dict(run_id=uuid4().hex, blender_version=".".join(map(str,bpy.app.version)),
                    fixture_id=panel.FIXTURE_ID, mode="native")
    origins = [preview.scene_signature(ctx) for _ in range(2)]
    assert origins[0] == origins[1]
    handlers_before = {n:tuple(getattr(bpy.app.handlers,n)) for n,_ in preview.HISTORY_HANDLERS}
    records, measured = [], {}
    fixture_reads = [[], []]
    preview.register()
    old_build = None
    try:
        s = ctx.scene.cbdk_a_joint
        s.provider_zip, s.geometry_root = zip_path, gl_root
        preview.configure(zip_path, gl_root)
        provider = preview.PROVIDERS[0].common_tools
        old_build = provider.build_rotary

        def observed_build(context, settings, collection):
            for log in fixture_reads:
                log.append(dict(axis=settings.axis, origin=list(context.scene.cursor.location),
                                unit_scale=float(context.scene.unit_settings.scale_length),
                                axle_diameter=float(settings.axle_diameter),
                                clearance=float(settings.radial_clearance), mode=context.mode))
            return old_build(context, settings, collection)

        provider.build_rotary = observed_build
        original_classes = tuple(preview.CLASSES)
        original_handlers = {n:tuple(getattr(bpy.app.handlers,n)) for n,_ in preview.HISTORY_HANDLERS}
        bridge.register()
        registered = [bool(panel.CBDK_PT_joint_panel_r29.is_registered and panel.OWNED) for _ in range(2)]
        duplicate = False
        try:
            try:
                bridge.register()
            except RuntimeError as exc:
                assert str(exc) == "r29_duplicate_or_foreign_panel"
                duplicate = True
            assert duplicate
            modal = scheduler = None

            def reset():
                # Independent synthetic scenario setup, not a claimed operation.
                s.diameter, s.target, s.policy = 5.,4.,"FREE"
                s.provider_zip,s.geometry_root = zip_path,gl_root
                s.restore_diameter,s.candidate = 5.,2
                s.status,s.reason,s.result_json = "IDLE","",""
                s.cancel_requested = False
                preview.RUNS.clear()

            def ready(index=2):
                reset()
                assert bpy.ops.cbdk_a.joint_action(action="RETRY") == {"FINISHED"}
                assert s.status == "READY"
                s.candidate = index

            def start():
                nonlocal modal,scheduler
                modal,scheduler = NS(),ControlledContext(ctx)
                result = preview.CBDK_A_OT_start.invoke(modal,scheduler,NS(type="NONE"))
                if result == {"RUNNING_MODAL"}:
                    assert scheduler.added == [.1] and scheduler.handlers == [modal]
                else:
                    assert not scheduler.added and not scheduler.handlers
                return result

            def tick():
                return preview.CBDK_A_OT_start.modal(modal,scheduler,NS(type="TIMER"))

            def complete():
                for _ in range(8):
                    result = tick()
                    if result != {"RUNNING_MODAL"}:
                        assert scheduler.removed == [scheduler.timer]
                        return result
                raise AssertionError("fixed iterator did not stop")

            def fail():
                original = preview.trial
                def injected(*a,**kw):
                    return original(*a,**dict(kw,fault="generation"))
                preview.trial = injected
                try:
                    return complete()
                finally:
                    preview.trial = original

            def native(action):
                if action in ("ADOPT","RESTORE"):
                    return bpy.ops.cbdk_a.joint_dimension(action=action)
                return bpy.ops.cbdk_a.joint_action(action=action)

            for case, sequence in CASES.items():
                reset()
                if case == "rejected_candidate":
                    ready(0)
                elif case == "stale_candidate":
                    ready(0)
                    s.provider_zip = zip_path + ".changed"
                elif case == "explicit_reject":
                    ready()
                elif case == "blocked":
                    s.status,s.reason = "BLOCKED","restoration_blocked"
                paths = [[],[]]
                for index, action in enumerate(sequence):
                    before = [observe(ctx),observe(ctx)]
                    if action == "START":
                        result,method = start(),"callback_simulation"
                    elif action == "COMPLETE":
                        result,method = complete(),"native_iterator"
                    elif action == "INTERRUPT":
                        result,method = complete(),"callback_simulation"
                    elif action == "FAIL":
                        result,method = fail(),"callback_simulation"
                    else:
                        result,method = native(action),"native_operator"
                    assert len(result)==1
                    after = [observe(ctx),observe(ctx)]
                    for i in range(2):
                        paths[i].append(dict(index=index, action=action,
                            operator=panel.OPERATOR_BINDINGS[action][0] if action in panel.OPERATOR_BINDINGS else None,
                            method=method, explicit=action in panel.OPERATOR_BINDINGS,
                            result=next(iter(result)), before=before[i][0], after=after[i][0],
                            view_before=before[i][1], view_after=after[i][1]))
                records.append(dict(**identity,case=case,steps=paths[0]))
                measured[case]=dict(**identity,case=case,steps=paths[1])
        finally:
            bridge.unregister()
        unregistered = [not panel.OWNED and not panel.CBDK_PT_joint_panel_r29.is_registered for _ in range(2)]
        preserved = [tuple(preview.CLASSES)==original_classes and all(c.is_registered for c in original_classes)
                     and all(tuple(getattr(bpy.app.handlers,n))==v for n,v in original_handlers.items())
                     for _ in range(2)]
    finally:
        if old_build is not None:
            provider.build_rotary = old_build
        preview.unregister()
    assert not hasattr(bpy.types.Scene,"cbdk_a_joint")
    assert all(tuple(getattr(bpy.app.handlers,n))==v for n,v in handlers_before.items())
    lifecycles = []
    for i, log in enumerate(fixture_reads):
        assert log and all(x==log[0] for x in log)
        lifecycles.append(dict(**identity, registered=registered[i], duplicate_rejected=duplicate,
            unregistered=unregistered[i], existing_registration_unchanged=preserved[i],
            scene_before=origins[i],scene_after=preview.scene_signature(ctx),
            fixture_settings=log[0], draw_method="native_panel_draw_recording_layout",
            projection_source="real_projection"))
    report = reduce_panel_evidence(records, run_id=identity["run_id"],
        blender_version=identity["blender_version"],mode=identity["mode"],scene_sha=origins[1],
        measured=measured,lifecycle=lifecycles[0],measured_lifecycle=lifecycles[1])
    result=dict(report=report, records=records, measured=measured,
                lifecycle=lifecycles[0],measured_lifecycle=lifecycles[1],
                observation_scope="two separate RNA/draw reads, shared actual operation return")
    with output.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    assert report["status"]=="verified_native_observations", report
    print("CBDK_R29_D_EVIDENCE_PASS "+json.dumps(report,ensure_ascii=True),flush=True)
