"""A-owned explicit R29 connection; no new execution or registration side effect."""
from pathlib import Path

import bpy
from cbdk.joint_panel_view_r29 import project_joint_panel
from parts.blender import joint_panel_r29 as panel, joint_preview as preview


def provider_inputs_match(context):
    """Read-only comparison with the existing configured provider identity."""
    s = context.scene.cbdk_a_joint
    if preview.PROVIDERS is None or preview.HISTORY_BLOCKED or not preview.OWNED:
        return False
    try:
        requested = (Path(bpy.path.abspath(s.provider_zip)).resolve(),
                     Path(bpy.path.abspath(s.geometry_root)).resolve())
        return requested == preview.PROVIDER_PATHS
    except (OSError, RuntimeError, ValueError, TypeError):
        return False


def project(context, **source):
    """Translate B's bounded display contract to C; no provider calls in draw."""
    s = context.scene.cbdk_a_joint
    current = bool(source["current_inputs_match"] and provider_inputs_match(context))
    rows = source["candidates"]
    if preview.RUNS.get(context.scene.as_pointer()) is None:
        rows = None
    view = project_joint_panel(source["status"], source["reason"], source["result_json"],
                               rows, current_inputs_match=current,
                               selected_index=source["selected_index"])
    return dict(fixture_id=view["fixture_id"], part_ids=view["part_ids"],
                recipe_label=view["recipe_label"], status=view["status"],
                reason=view["reason"], available=view["availability"] == "available",
                candidates=view["candidates"], current_inputs_match=current,
                can_adopt=view["actions"]["ADOPT"])


def projection(**source):
    return project(bpy.context, **source)


def register():
    """Call after explicit joint_preview.register(); do not register on import."""
    panel.register(projection)


def unregister():
    panel.unregister()
