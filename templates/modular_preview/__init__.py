"""CBDK v0.11 recipe-composed read-only development preview.

Only trusted authored feature modules are loaded, selected at build time.
Do not install two modular-preview variants simultaneously: they share class
and operator identifiers and are intended to replace one another. A partially
failed unregister keeps its class ownership ledger until an explicit retry;
a Scene declaration replaced by a foreign owner is never deleted by CBDK.
"""
bl_info = {
    "name": __CBDK_DISPLAY_NAME__,
    "author": "Chappy Blender DevKit (private development preview)",
    "version": (0, 16, 0),
    "blender": (4, 4, 0),
    "location": "3D View > Sidebar > CBDK",
    "description": "Recipe-built mesh inspection preview; no topology editing",
    "category": "3D View",
}

import importlib
from math import isfinite
import bpy

# importlib.reload() re-executes a module in its existing namespace.  If the
# preview is still registered, resetting the lists below would orphan Blender
# classes and Scene declarations.  Require explicit unregister/disable first.
# Place this check *before* recreating the operator/Panel classes and ledgers.
if any(globals().get(key) for key in (
        "_REGISTERED", "_OWNED_PROPERTIES", "_OWNED_PROPERTY_TOKENS")):
    raise RuntimeError("CBDK preview must be unregistered before module reload")

_FEATURE_IDS = __CBDK_FEATURE_IDS__
_UI_SECTIONS = __CBDK_UI_SECTIONS__
_UI_OPTIONS = __CBDK_UI_OPTIONS__
_FEATURE_CONTRACT = __CBDK_FEATURE_CONTRACT__
_FEATURE_MODULES = {feature: importlib.import_module("." + feature, __name__ + ".features")
                    for feature in _FEATURE_IDS}
_OPERATORS = [_FEATURE_MODULES[feature].OPERATOR_CLASS for feature in _FEATURE_IDS]
_OPERATORS_BY_FEATURE = dict(zip(_FEATURE_IDS, _OPERATORS))
# Generated from code-owned descriptors, never from recipe JSON.
if set(_FEATURE_CONTRACT) != set(_FEATURE_IDS):
    raise RuntimeError("Feature contract does not match generated selection")
for feature_id, operator in _OPERATORS_BY_FEATURE.items():
    if operator.bl_idname != _FEATURE_CONTRACT[feature_id]["operator"]:
        raise RuntimeError("Authored operator registration contract mismatch")
_OBJECT_MODE_FEATURES = frozenset(f for f, d in _FEATURE_CONTRACT.items() if d["mode"] == "OBJECT")
_EDIT_MODE_FEATURES = frozenset(f for f, d in _FEATURE_CONTRACT.items() if d["mode"] == "EDIT_MESH")
assert set(_FEATURE_IDS) <= _OBJECT_MODE_FEATURES | _EDIT_MODE_FEATURES



# This is only a cheap panel hint; every operator must revalidate its live
# context and geometry during execute(). Never scan BMesh in Panel.draw.
# R15 checks this distinction using live Blender Panel.draw enabled flags
# versus real bpy.ops FINISHED/CANCELLED results across selection/mode changes.
# A previous enabled hint is not authorization to bypass execute() guards.
# R16: mode/selection may change after Panel.draw; the trusted operator must
# still reject stale permissions using live Blender context on every call.
def _preview_unavailable_reason(feature_id, context):
    active = getattr(context, "active_object", None)
    mesh = getattr(active, "data", None)
    if active is None or getattr(active, "type", None) != "MESH" or mesh is None:
        return "An active mesh object is required"
    required_mode = "EDIT_MESH" if feature_id in _EDIT_MODE_FEATURES else "OBJECT"
    if getattr(context, "mode", None) != required_mode:
        return "Switch to " + required_mode + " mode"

    hint = _FEATURE_CONTRACT[feature_id]["ui_hint"]
    if hint == "selected_objects":
        # The matching read-only helper refuses a context with no selection
        # collection. This is a context hint, not a scan of selected objects.
        if getattr(context, "selected_objects", None) is None:
            return "Context does not expose selected_objects"
    elif hint == "bounds":
        vertices = getattr(mesh, "vertices", None)
        if vertices is None or len(vertices) == 0:
            return "Active mesh must contain vertices"
        corners = getattr(active, "bound_box", None)
        if corners is None or len(corners) != 8:
            return "Active mesh has no valid bounding box"
        # At most 24 scalar checks, independent of mesh size. A non-finite
        # corner is known to make the bounds helper refuse execution; a
        # finite preview still is NOT a guarantee that its world transform
        # or any subsequent operator calculation will succeed.
        try:
            if any(len(corner) != 3 or any(not isfinite(float(v)) for v in corner)
                   for corner in corners):
                return "Mesh bounding box contains non-finite coordinates"
        except (TypeError, ValueError, OverflowError):
            return "Mesh bounding box contains non-finite coordinates"
    elif hint == "single_edit":
        objects = getattr(context, "objects_in_mode_unique_data", None)
        if objects is None:
            return "Cannot verify multi-object Edit Mode state"
        if sum(1 for obj in objects if getattr(obj, "type", None) == "MESH") != 1:
            return "Exactly one unique mesh must be in Edit Mode"
    elif hint == "nudge":
        return _FEATURE_MODULES[feature_id].ui_unavailable_reason(context)
    elif hint != "mesh":
        return "Unsupported authored context contract"
    return None


class VIEW3D_PT_cbdk_modular_preview(bpy.types.Panel):
    bl_label = "CBDK Modular Preview"
    bl_idname = "VIEW3D_PT_cbdk_modular_preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CBDK"

    def draw(self, context):
        col = self.layout.column(align=True)
        # Snapshot the UI mode once for consistent composition during a mode
        # switch. A missing/non-string mode is unsupported, never ready.
        raw_mode = getattr(context, "mode", None)
        visible_mode = raw_mode.lower() if type(raw_mode) is str else None
        visible_sections = 0
        panel_indices = getattr(self, "_cbdk_section_indices", None)
        for index, (title, buttons) in enumerate(_UI_SECTIONS):
            if panel_indices is not None and index not in panel_indices:
                continue
            style = _UI_OPTIONS["section_styles"][index]
            if style["visible_in"] not in ("always", visible_mode):
                continue
            control_modes = _UI_OPTIONS["control_visibility"][index]
            visible_buttons = [(feature_id, label) for (feature_id, label), mode in
                               zip(buttons, control_modes)
                               if mode in ("always", visible_mode)]
            if not visible_buttons:
                continue
            visible_sections += 1
            group = col.box() if style["boxed"] else col.column(align=True)
            group.label(text=title)
            body = group.row(align=True) if style["layout"] == "row" else group
            for feature_id, label in visible_buttons:
                button_row = body.row(align=True)
                reason = _preview_unavailable_reason(feature_id, context)
                spec = _FEATURE_CONTRACT[feature_id]["input_spec"]
                if spec is not None:
                    # A disabled nudge action must not also disable its XYZ
                    # editor. Only disable the input for invalid mesh/mode.
                    active = getattr(context, "active_object", None)
                    button_row.enabled = (
                        getattr(active, "type", None) == "MESH"
                        and getattr(active, "data", None) is not None
                        and getattr(context, "mode", None) == _FEATURE_CONTRACT[feature_id]["mode"]
                    )
                    button_row.prop(context.scene, spec["rna"], text=spec["label"])
                    action = button_row.row(align=True)
                    action.enabled = reason is None
                    button = action.operator(
                        _OPERATORS_BY_FEATURE[feature_id].bl_idname, text=label
                    )
                    if spec["operator_arg"] is not None:
                        setattr(button, spec["operator_arg"], getattr(context.scene, spec["rna"]))
                else:
                    button_row.enabled = reason is None
                    button_row.operator(_OPERATORS_BY_FEATURE[feature_id].bl_idname, text=label)
                if reason is not None:
                    body.label(text=label + ": " + reason)
        if not visible_sections:
            col.label(text="No preview controls for this mode")
        col.label(text=context.scene.cbdk_modular_result)


# The legacy class remains the only registered panel for schema 1.
# Schema 2 selects only two code-owned panel classes, never user class names.
if "panels" in _UI_OPTIONS:
    class VIEW3D_PT_cbdk_modular_primary(bpy.types.Panel):
        bl_idname = "VIEW3D_PT_cbdk_modular_primary"
        bl_label = "CBDK Primary"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "CBDK"
        draw = VIEW3D_PT_cbdk_modular_preview.draw

    class VIEW3D_PT_cbdk_modular_secondary(bpy.types.Panel):
        bl_idname = "VIEW3D_PT_cbdk_modular_secondary"
        bl_label = "CBDK Secondary"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "CBDK"
        draw = VIEW3D_PT_cbdk_modular_preview.draw

    _SLOTS = {"primary": VIEW3D_PT_cbdk_modular_primary,
              "secondary": VIEW3D_PT_cbdk_modular_secondary}
    _panels = []
    for order, panel in enumerate(_UI_OPTIONS["panels"]):
        cls = _SLOTS[panel["slot"]]
        if cls.bl_idname != panel["panel_id"] or cls in _panels:
            raise RuntimeError("Authored panel registration contract mismatch")
        cls.bl_label = panel["label"]
        cls.bl_order = order
        cls._cbdk_section_indices = panel["section_indices"]
        _panels.append(cls)
    if len(_panels) != 2 or sorted(index for cls in _panels
            for index in cls._cbdk_section_indices) != list(range(len(_UI_SECTIONS))):
        raise RuntimeError("Authored panel section coverage mismatch")
    _PANEL_CLASSES = tuple(_panels)
else:
    _PANEL_CLASSES = (VIEW3D_PT_cbdk_modular_preview,)

_CLASSES = tuple(_OPERATORS) + _PANEL_CLASSES
_REGISTERED = []


_PROPERTY_NAMES = ("cbdk_modular_result",) + tuple(spec["rna"] for spec in _UI_OPTIONS["typed_inputs"])
if len(set(_PROPERTY_NAMES)) != len(_PROPERTY_NAMES):
    raise RuntimeError("Duplicate authored Scene property")
_OWNED_PROPERTIES = []
# Blender's registered bpy.props declarations also remain in Scene.__dict__.
# Keep the exact descriptor to avoid deleting a foreign replacement by name.
_OWNED_PROPERTY_TOKENS = {}


def register():
    # Refuse collisions before touching another add-on's Scene data.
    if (_REGISTERED or _OWNED_PROPERTIES or _OWNED_PROPERTY_TOKENS
            or any(hasattr(bpy.types.Scene, name) for name in _PROPERTY_NAMES)):
        raise RuntimeError("CBDK preview is already registered or Scene properties conflict")
    # Blender can replace a foreign panel with a matching identifier. Refuse
    # before any owned property/class changes in the new multi-panel path.
    if _UI_OPTIONS.get("panels") and any(
            hasattr(bpy.types, panel["panel_id"]) for panel in _UI_OPTIONS["panels"]):
        raise RuntimeError("CBDK preview panel registration conflict")
    try:
        bpy.types.Scene.cbdk_modular_result = bpy.props.StringProperty(
            name="Last CBDK preview result", default="No inspection yet"
        )
        _OWNED_PROPERTIES.append("cbdk_modular_result")
        _OWNED_PROPERTY_TOKENS["cbdk_modular_result"] = (
            bpy.types.Scene.__dict__.get("cbdk_modular_result"))
        for parameter in _UI_OPTIONS["typed_inputs"]:
            kwargs = {key: parameter[key] for key in
                      ("name", "description", "default", "min", "max")}
            if parameter["type"] == "float_vector":
                declaration = bpy.props.FloatVectorProperty(
                    **kwargs, size=parameter["size"], subtype=parameter["subtype"])
            elif parameter["type"] == "int":
                declaration = bpy.props.IntProperty(**kwargs)
            else:
                raise RuntimeError("Unsupported authored RNA input type")
            name = parameter["rna"]
            setattr(bpy.types.Scene, name, declaration)
            _OWNED_PROPERTIES.append(name)
            _OWNED_PROPERTY_TOKENS[name] = bpy.types.Scene.__dict__.get(name)
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
            _REGISTERED.append(cls)
    except Exception as error:
        # A class-registration callback may fail after one operator attaches,
        # while a Scene declaration has been removed or replaced. Reuse the
        # ownership-aware unregister path: preserve foreign replacements,
        # release only still-owned declarations, and retain failed ledgers for
        # an explicit retry instead of silently resetting them.
        try:
            unregister()
        except Exception as cleanup_error:
            # Keep the original registration error and retain failed entries
            # in the ownership lists so a later cleanup can be retried.
            error.add_note("CBDK preview rollback was incomplete; retry unregister()")
            raise error from cleanup_error
        raise


def unregister():
    # A failing operator unregister must not prevent owned Scene property
    # cleanup. Entries are removed only after a successful detach so a caller
    # can retry without touching foreign add-on registrations. R10 checks
    # that simultaneous failures keep both independent class/property
    # ledgers until each cleanup step succeeds, even across multiple retries.
    # R13: addon_utils may evict this module after an enable failure. A
    # separately imported copy cannot see these original ownership lists:
    # the caller must keep the old module reference for explicit recovery.
    # R14: multiple evicted copies can each own different Blender classes.
    # Empty lists in a new import say nothing about those older instances;
    # only explicit cleanup of every retained original can establish release.
    failures = []
    for cls in reversed(tuple(_REGISTERED)):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as error:
            failures.append(error)
        else:
            _REGISTERED.remove(cls)
    for name in reversed(tuple(_OWNED_PROPERTIES)):
        try:
            # A different addon may have removed/replaced our declaration.
            # Blender retains assigned bpy.props on the type __dict__; a
            # replacement has a different descriptor even with the same name.
            # Releasing a lost ownership claim must NOT delete the new value.
            current = bpy.types.Scene.__dict__.get(name)
            token = _OWNED_PROPERTY_TOKENS.get(name)
            # A missing descriptor is never proof of ownership. In particular
            # "None is None" must not authorize deleting an inherited or
            # otherwise foreign RNA property with a matching name.
            if token is not None and current is token:
                if hasattr(bpy.types.Scene, name):
                    # If Blender RNA deletion raises, keep the ownership
                    # ledger for a later explicit unregister() retry.
                    # R9's CBDK-only probe shadows this module's builtin
                    # delattr to simulate the error without altering Blender.
                    delattr(bpy.types.Scene, name)
        except Exception as error:
            failures.append(error)
        else:
            _OWNED_PROPERTIES.remove(name)
            _OWNED_PROPERTY_TOKENS.pop(name, None)
    if failures:
        raise RuntimeError("CBDK preview cleanup incomplete; retry unregister()") from failures[0]
