"""Safe declarative panel layout for the five CBDK-authored preview features.

UI JSON only controls labels and grouping; it NEVER selects Python modules,
operator class names, source paths, or executes user-supplied expressions.
"""
from __future__ import annotations

import json
from pathlib import Path

from .addon_builder import _trusted_read
from .feature_catalog import TRUSTED_FEATURES

UI_CATALOG = "catalog/ui_layouts.json"
MAX_BYTES = 20_000


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
        if type(section) is not dict or set(section) != {"id", "title", "controls"}:
            raise ValueError("Invalid authored UI section")
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
            if type(control) is not dict or set(control) != {"feature_id", "label"}:
                raise ValueError("Unexpected authored UI control fields")
            feature_id = control["feature_id"]
            if (not isinstance(feature_id, str)
                    or feature_id not in TRUSTED_FEATURES
                    or feature_id in seen_features
                    or not _label(control["label"])):
                raise ValueError("Unknown, repeated or invalid authored UI control")
            seen_features.add(feature_id)
            entries.append((feature_id, control["label"]))
        output.append((title, tuple(entries)))
    if seen_features != set(TRUSTED_FEATURES):
        raise ValueError("Authored UI layout must cover exactly all allowed features")
    return tuple(output)


def plan_ui_layout(requested_features: object, *, root: Path) -> tuple:
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
    layout = validate_ui_layout(
        json.loads(source.decode("utf-8"), object_pairs_hook=_strict_object)
    )
    chosen = set(requested_features)
    visible = tuple(
        (title, tuple((feature_id, label) for feature_id, label in controls
                      if feature_id in chosen))
        for title, controls in layout
    )
    return tuple((title, controls) for title, controls in visible if controls)
