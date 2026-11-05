"""Read modifier stack; requires BLCTX-001 and BLMOD-001."""
from collections import Counter

import bpy

from ..helpers.context import BlenderContextError
from ..helpers.modifiers import modifier_snapshot


class CBDK_OT_modular_modifier_summary(bpy.types.Operator):
    bl_idname = "cbdk.modular_modifier_summary"
    bl_label = "Inspect Modifiers"
    bl_description = "Summarize modifiers on active mesh without changing them"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        try:
            snapshot = modifier_snapshot(context)
        except BlenderContextError as exc:
            self.report({"WARNING"}, str(exc))
            return {"CANCELLED"}
        groups = Counter(item.type for item in snapshot)
        types = ", ".join(f"{kind}:{count}" for kind, count in sorted(groups.items()))
        message = f"Modifiers: {len(snapshot)}" + (f" ({types})" if types else " (none)")
        context.scene.cbdk_modular_result = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


OPERATOR_CLASS = CBDK_OT_modular_modifier_summary
