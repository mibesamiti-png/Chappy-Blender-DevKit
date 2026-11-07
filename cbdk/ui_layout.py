"""Safe declarative panel layout for the five CBDK-authored preview features.

UI JSON controls labels, grouping, fixed visibility and bounded defaults.
It NEVER selects Python modules,
operator class names, source paths, or executes user-supplied expressions.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .addon_builder import _trusted_read
from .feature_catalog import TRUSTED_FEATURES

UI_CATALOG = "catalog/ui_layouts.json"
MAX_BYTES = 20_000
NUDGE_PARAMETER = {"type": "float_vector", "size": 3, "min": -10.0,
                   "max": 10.0, "default": (0.0, 0.0, 0.1)}


def validate_nudge_default(value):
    if (not isinstance(value, (tuple, list)) or len(value) != NUDGE_PARAMETER["size"]
            or any(type(v) not in (int, float)
                   or not NUDGE_PARAMETER["min"] <= v <= NUDGE_PARAMETER["max"]
                   or not math.isfinite(v) for v in value)
            or all(v == 0 for v in value)):
        raise ValueError("Nudge default must be three finite nonzero-vector components within +/-10")
    return tuple(float(v) for v in value)


def validate_nudge_settings(value):
    """Code-owned type/size; declarative bounds may only narrow safe limits.

    Legacy vector-only defaults remain valid. No arbitrary RNA names, types,
    expressions or expanded operator limits can enter the generated package.
    """
    settings = dict(NUDGE_PARAMETER)
    if type(value) is dict:
        if set(value) != {"default", "min", "max"}:
            raise ValueError("Expected default/min/max for authored nudge settings")
        for bound in (value["min"], value["max"]):
            if (type(bound) not in (int, float)
                    or not NUDGE_PARAMETER["min"] <= bound <= NUDGE_PARAMETER["max"]
                    or not math.isfinite(bound)):
                raise ValueError("Nudge bounds may only narrow the finite +/-10 range")
        if not value["min"] <= 0 <= value["max"] or value["min"] >= value["max"]:
            raise ValueError("Nudge bounds must be ordered and include zero")
        settings.update(min=float(value["min"]), max=float(value["max"]))
        value = value["default"]
    settings["default"] = validate_nudge_default(value)
    if any(not settings["min"] <= component <= settings["max"] for component in settings["default"]):
        raise ValueError("Nudge default lies outside declared bounds")
    return settings


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key in authored UI layout: " + key)
        result[key] = value
    return result


def _label(value, *, limit=72):
    return (
        isinstance(value, str)
        and 1 <= len(value) <= limit
        and value.isprintable()
    )


def validate_ui_layout(data: object) -> tuple:
    """Validate all five known feature placements before filtering a recipe."""
    if (type(data) is not dict or set(data) != {
            "schema_version", "kind", "preview_only", "sections"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
            or data["kind"] != "cbdk_authored_preview_ui_layout"
            or data["preview_only"] is not True):
        raise ValueError("Unsupported authored UI layout schema")
    sections = data["sections"]
    if type(sections) is not list or not 1 <= len(sections) <= 4:
        raise ValueError("Expected 1..4 authored UI sections")
    seen_section_ids = set()
    seen_features = set()
    output = []
    for section in sections:
        if (type(section) is not dict or not {"id", "title", "controls"} <= set(section)
                or set(section) - {"id", "title", "controls", "layout", "boxed", "visible_in"}):
            raise ValueError("Invalid authored UI section")
        if section.get("layout", "column") not in ("column", "row") or type(section.get("boxed", True)) is not bool:
            raise ValueError("Unsupported authored section presentation")
        if section.get("visible_in", "always") not in ("always", "object", "edit_mesh"):
            raise ValueError("Section visibility must be always/object/edit_mesh")
        section_id = section["id"]
        title = section["title"]
        if (not isinstance(section_id, str)
                or not section_id.isascii() or not section_id.isidentifier()
                or not 1 <= len(section_id) <= 32
                or section_id in seen_section_ids or not _label(title)):
            raise ValueError("Invalid or repeated authored UI section")
        seen_section_ids.add(section_id)
        controls = section["controls"]
        if type(controls) is not list or not 1 <= len(controls) <= len(TRUSTED_FEATURES):
            raise ValueError("Invalid authored UI section controls")
        entries = []
        for control in controls:
            if (type(control) is not dict or not {"feature_id", "label"} <= set(control)
                    or set(control) - {"feature_id", "label", "parameters", "visible_in"}):
                raise ValueError("Unexpected authored UI control fields")
            feature_id = control["feature_id"]
            if (not isinstance(feature_id, str)
                    or feature_id not in TRUSTED_FEATURES
                    or feature_id in seen_features
                    or not _label(control["label"])):
                raise ValueError("Unknown, repeated or invalid authored UI control")
            seen_features.add(feature_id)
            required_mode = "edit_mesh" if feature_id in {"edit_selection", "vertex_nudge"} else "object"
            control_mode = control.get("visible_in", "always")
            if type(control_mode) is not str or control_mode not in ("always", required_mode):
                raise ValueError("Control visibility must be always or its authored operator mode")
            if section.get("visible_in", "always") not in ("always", required_mode):
                raise ValueError("Section visibility would make an authored control unreachable")
            if "parameters" in control:
                parameters = control["parameters"]
                if feature_id != "vertex_nudge" or type(parameters) is not dict or set(parameters) != {"offset"}:
                    raise ValueError("Only the authored nudge offset parameter is configurable")
                validate_nudge_settings(parameters["offset"])
            entries.append((feature_id, control["label"]))
        output.append((title, tuple(entries)))
    if seen_features != set(TRUSTED_FEATURES):
        raise ValueError("Authored UI layout must cover exactly all allowed features")
    return tuple(output)


def plan_ui_layout(requested_features: object, *, root: Path, include_options=False) -> tuple:
    """Return ordered visible sections for a validated preview feature subset."""
    if (not isinstance(requested_features, (tuple, list))
            or not 1 <= len(requested_features) <= len(TRUSTED_FEATURES)
            or any(type(f) is not str or f not in TRUSTED_FEATURES
                   for f in requested_features)
            or len(set(requested_features)) != len(requested_features)):
        raise ValueError("Invalid authored UI feature selection")
    source = _trusted_read(UI_CATALOG, root=root.resolve())
    if len(source) > MAX_BYTES:
        raise ValueError("Authored UI layout exceeds size limit")
    data = json.loads(source.decode("utf-8"), object_pairs_hook=_strict_object)
    layout = validate_ui_layout(data)
    chosen = set(requested_features)
    visible = tuple(
        (title, tuple((feature_id, label) for feature_id, label in controls
                      if feature_id in chosen))
        for title, controls in layout
    )
    result = tuple((title, controls) for title, controls in visible if controls)
    if not include_options:
        return result
    styles = tuple({"layout": s.get("layout", "column"), "boxed": s.get("boxed", True),
                    "visible_in": s.get("visible_in", "always")}
                   for s in data["sections"] if any(c["feature_id"] in chosen for c in s["controls"]))
    offset = NUDGE_PARAMETER["default"]
    for section in data["sections"]:
        for control in section["controls"]:
            if control["feature_id"] == "vertex_nudge" and "vertex_nudge" in chosen:
                offset = control.get("parameters", {}).get("offset", offset)
    control_visibility = tuple(
        tuple(control.get("visible_in", "always") for control in section["controls"]
              if control["feature_id"] in chosen)
        for section in data["sections"]
        if any(control["feature_id"] in chosen for control in section["controls"])
    )
    return result, {"section_styles": styles,
                    "control_visibility": control_visibility,
                    "nudge_offset": validate_nudge_settings(offset)}
