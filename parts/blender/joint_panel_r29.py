"""Opt-in R29 fixed artificial rotary review panel; no new execution operator."""
import json
import math

import bpy
from parts.blender import joint_preview as preview

FIXTURE_ID = "joint_rotary_fixture_v1"
PART_IDS = ("rotary_outer", "rotary_axle")
RECIPE_LABEL = "固定人工回転関節"
STATUSES = {"IDLE", "RUNNING", "READY", "NO_CANDIDATE", "FAILED", "CANCELLED",
            "REJECTED", "ADOPTED_DIMENSION_ONLY", "RESTORED", "BLOCKED"}
IDS = ("negative_control", "midpoint", "declared_target")
DECISIONS = {"regression", "protected_part_regression", "axial_dimension_regression",
             "observed_improvement", "target_reached", "uncertain"}
OPERATOR_BINDINGS = {
    "START": ("cbdk_a.joint_start", None, "INVOKE_DEFAULT"),
    "RETRY": ("cbdk_a.joint_action", "RETRY", "EXEC_DEFAULT"),
    "REJECT": ("cbdk_a.joint_action", "REJECT", "EXEC_DEFAULT"),
    "CANCEL": ("cbdk_a.joint_action", "CANCEL", "EXEC_DEFAULT"),
    "ADOPT": ("cbdk_a.joint_dimension", "ADOPT", "EXEC_DEFAULT"),
    "RESTORE": ("cbdk_a.joint_dimension", "RESTORE", "EXEC_DEFAULT"),
}
OWNED = False
_PROJECTION = None


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100


def _rows(payload):
    if type(payload) is not dict or type(payload.get("rows")) is not list:
        return []
    rows = payload["rows"]
    if len(rows) > 3:
        raise ValueError("candidate_count")
    out = []
    for index, row in enumerate(rows):
        if type(row) is not dict or type(row.get("review")) is not dict:
            raise ValueError("candidate_shape")
        review = row["review"]
        if (row.get("id") != IDS[index] or not _number(row.get("diameter"))
                or row["diameter"] <= 0 or not _number(review.get("score"))
                or review.get("decision") not in DECISIONS
                or type(review.get("accepted_for_review")) is not bool):
            raise ValueError("candidate_fields")
        out.append(dict(id=row["id"], diameter=row["diameter"], decision=review["decision"],
                        score=review["score"], accepted_for_review=review["accepted_for_review"]))
    return out


def _fixed_context(context, settings):
    return (context.mode == "OBJECT" and tuple(context.scene.cursor.location) == (0., 0., 0.)
            and context.scene.unit_settings.scale_length == 1.
            and float(settings.diameter) == 5. and float(settings.target) == 4.
            and settings.policy == "FREE")


def projection_input(context):
    """Adapter: read current RUNS only; never reconstruct candidate authority from JSON."""
    s = context.scene.cbdk_a_joint
    payload = preview.RUNS.get(context.scene.as_pointer())
    try:
        candidates = _rows(payload) if s.status in ("READY", "NO_CANDIDATE") else []
        valid = payload is None or type(payload.get("rows")) is list
        current = bool(valid and s.status in ("READY", "NO_CANDIDATE") and payload is not None and _fixed_context(context, s)
                       and (s.diameter, s.target, s.policy) ==
                       (payload.get("original"), payload.get("target"), payload.get("policy"))
                       and preview.scene_signature(context) == payload.get("signature")
                       and len(s.result_json) <= 1_000_000
                       and s.result_json == json.dumps(payload))
    except (AttributeError, TypeError, ValueError, KeyError, OverflowError, RuntimeError):
        candidates, current = [], False
    return dict(status=s.status, reason=s.reason, result_json=s.result_json,
                candidates=candidates, current_inputs_match=current, selected_index=int(s.candidate))


def _safe_reason(reason):
    return (reason if type(reason) is str and len(reason) <= 80 and reason.isascii()
            and all(c.isalnum() or c == "_" for c in reason) else "unavailable")


def _checked_projection(data, source):
    """The A adapter may translate B's schema to this narrow display contract."""
    if (type(data) is not dict or data.get("fixture_id") != FIXTURE_ID
            or data.get("part_ids") != list(PART_IDS) or data.get("recipe_label") != RECIPE_LABEL
            or data.get("status") != source["status"] or data.get("status") not in STATUSES
            or data.get("available") is not True
            or type(data.get("current_inputs_match")) is not bool
            or data["current_inputs_match"] != source["current_inputs_match"]
            or type(data.get("can_adopt")) is not bool
            or data.get("candidates") != source["candidates"]
            or (data["can_adopt"] and (data["status"] != "READY" or not data["current_inputs_match"]))):
        return None
    return data


def visible_actions(status, *, available, current, selected, fixed_context):
    """Presentation only; existing operators retain all authorization."""
    if status == "BLOCKED":
        return ()
    if status == "RUNNING":
        return ("CANCEL",)
    if not available or status not in STATUSES:
        return ()
    if status == "IDLE":
        return ("START",) if fixed_context else ()
    if status == "RESTORED":
        return (("START",) if fixed_context else ()) + ("RESTORE",)
    if status == "READY":
        return (("ADOPT",) if current and selected and fixed_context else ()) + ("REJECT", "RESTORE")
    if status in ("FAILED", "CANCELLED", "NO_CANDIDATE", "REJECTED"):
        return (("RETRY",) if fixed_context else ()) + ("RESTORE",)
    if status == "ADOPTED_DIMENSION_ONLY":
        return ("RESTORE",)
    return ()


LABELS = dict(START="候補生成・形状検査", RETRY="明示的に再試行", REJECT="候補を拒否",
              CANCEL="中断（候補境界で停止）", ADOPT="選択候補の寸法だけ採用", RESTORE="元の寸法へ復元")


def draw_panel(layout, context):
    s = getattr(context.scene, "cbdk_a_joint", None)
    layout.label(text="固定人工回転関節 — 開発プレビュー")
    layout.label(text="joint_rotary_fixture_v1")
    layout.label(text="rotary_outer：外側 / rotary_axle：軸")
    layout.label(text="目標外径4 / 元外径5 / 軸径2 / 隙間0.4 / Z軸・原点")
    if s is None:
        layout.label(text="unavailable", icon="ERROR")
        return
    source = projection_input(context)
    data = None
    if _PROJECTION is not None:
        try:
            data = _checked_projection(_PROJECTION(**source), source)
        except Exception:
            data = None
    layout.label(text="状態: " + (s.status if s.status in STATUSES else "unavailable"))
    if s.reason:
        layout.label(text="理由: " + _safe_reason(s.reason), icon="ERROR")
    if data is None:
        layout.label(text="表示データ unavailable", icon="ERROR")
    else:
        for row in data["candidates"]:
            layout.label(text=f'{row["id"]} / 外径 {row["diameter"]:.4f} / {row["decision"]} / score {row["score"]:.5f}')
        if s.status == "READY" and data["current_inputs_match"] and data["candidates"]:
            layout.prop(s, "candidate", text="候補行")
    selected = bool(data and data["can_adopt"] and 0 <= s.candidate < len(data["candidates"])
                    and data["candidates"][s.candidate]["accepted_for_review"] is True)
    actions = visible_actions(s.status, available=data is not None,
        current=source["current_inputs_match"], selected=selected, fixed_context=_fixed_context(context, s))
    # No editing of fixture parameters/provider paths here; configure explicitly
    # with the existing preview. No custom execution or additional Undo.
    for action in actions:
        op_id, argument, invocation = OPERATOR_BINDINGS[action]
        row = layout.row()
        row.operator_context = invocation
        op = row.operator(op_id, text=LABELS[action])
        if argument is not None:
            op.action = argument
    layout.label(text="寸法採用のみ・メッシュ確定なし")


class CBDK_PT_joint_panel_r29(bpy.types.Panel):
    bl_label = "CBDK 統合操作 — 固定回転関節"
    bl_idname = "CBDK_PT_joint_panel_r29"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CBDK"

    def draw(self, context):
        draw_panel(self.layout, context)


def register(projection):
    """Explicit opt-in only, after existing joint_preview.register()."""
    global OWNED, _PROJECTION
    if OWNED or CBDK_PT_joint_panel_r29.is_registered or hasattr(bpy.types, CBDK_PT_joint_panel_r29.__name__):
        raise RuntimeError("r29_duplicate_or_foreign_panel")
    if not callable(projection):
        raise TypeError("r29_projection_required")
    if not preview.OWNED or not hasattr(bpy.types.Scene, "cbdk_a_joint"):
        raise RuntimeError("r29_existing_preview_required")
    bpy.utils.register_class(CBDK_PT_joint_panel_r29)
    OWNED, _PROJECTION = True, projection


def unregister():
    global OWNED, _PROJECTION
    if not OWNED or not CBDK_PT_joint_panel_r29.is_registered:
        raise RuntimeError("r29_registration_not_owned")
    bpy.utils.unregister_class(CBDK_PT_joint_panel_r29)
    OWNED, _PROJECTION = False, None
