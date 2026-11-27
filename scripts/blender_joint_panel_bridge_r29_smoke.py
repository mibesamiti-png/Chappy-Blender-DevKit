"""A R29 real-provider bridge smoke, separate from specialist stub and D evidence."""
import json

import bpy
from parts.blender import joint_preview as preview, joint_panel_r29 as panel
from parts.blender import joint_panel_bridge_r29 as bridge
from scripts.blender_joint_panel_r29_smoke import capture_draw, bindings


def run_bridge_smoke(output, zip_path, gl_root):
    assert not preview.OWNED and not panel.OWNED
    origin = preview.scene_signature(bpy.context)
    records = []
    preview.register()
    try:
        s = bpy.context.scene.cbdk_a_joint
        s.provider_zip, s.geometry_root = zip_path, gl_root
        s.diameter, s.target, s.policy = 5., 4., "FREE"
        s.status, s.reason = "IDLE", ""
        bridge.register()
        try:
            def check(label, expected):
                trace = capture_draw(bpy.context)
                actual = bindings(trace)
                assert actual == [panel.OPERATOR_BINDINGS[a] for a in expected], (label, trace)
                assert preview.scene_signature(bpy.context) == origin
                records.append(dict(case=label, status=s.status, diameter=s.diameter,
                                    bindings=actual, labels=[x["text"] for x in trace if x["kind"]=="label"]))
            check("idle", ["START"])
            # Direct existing synchronous operator, not a production panel click.
            assert bpy.ops.cbdk_a.joint_action(action="RETRY") == {"FINISHED"}
            assert s.status == "READY"
            s.candidate = 0
            check("negative_control", ["REJECT", "RESTORE"])
            s.candidate = 2
            check("selected_target", ["ADOPT", "REJECT", "RESTORE"])
            s.provider_zip = zip_path + ".changed"
            check("stale_provider", [])
            s.provider_zip = zip_path
            check("provider_restored", ["ADOPT", "REJECT", "RESTORE"])
            assert bpy.ops.cbdk_a.joint_dimension(action="ADOPT") == {"FINISHED"}
            assert s.status == "ADOPTED_DIMENSION_ONLY" and s.diameter == 4.
            check("adopted", ["RESTORE"])
            assert bpy.ops.cbdk_a.joint_dimension(action="RESTORE") == {"FINISHED"}
            assert s.status == "RESTORED" and s.diameter == 5.
            check("restored", ["START", "RESTORE"])
        finally:
            bridge.unregister()
        assert not panel.OWNED and all(c.is_registered for c in preview.CLASSES)
    finally:
        preview.unregister()
    assert preview.scene_signature(bpy.context) == origin
    result = dict(blender_version=".".join(map(str,bpy.app.version)), records=records,
                  actual_provider=True, real_projection=True, gui_clicks=False,
                  d_evidence_complete=False, auto_adopt=False, mesh_commit=False)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print("CBDK_R29_BRIDGE_PASS "+json.dumps(result, ensure_ascii=True), flush=True)
