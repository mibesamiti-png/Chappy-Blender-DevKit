"""Validation and dependency planning for trusted CBDK-authored preview features.

The catalog is advisory metadata, NOT executable code. Every source file and
part-to-source mapping is also pinned in Python constants. No arbitrary paths,
private scanned code, dynamic imports or new executable modules can be
introduced by editing JSON alone.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .addon_builder import _read_catalog, _trusted_read

CATALOG_PATH = "catalog/addon_features.json"
TRUSTED_FEATURES = {
    "edit_selection": {
        "source": "templates/modular_preview/features/edit_selection.py",
        "parts": frozenset({"BLCTX-001", "BME-001"}),
    },
    "object_selection": {
        "source": "templates/modular_preview/features/object_selection.py",
        "parts": frozenset({"BLCTX-001", "BLCTX-002"}),
    },
}
TRUSTED_PART_SOURCES = {
    "BLCTX-001": "parts/blender/context.py",
    "BLCTX-002": "parts/blender/context.py",
    "BME-001": "parts/blender/edit_mesh.py",
}
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse_version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or len(value) > 32 or not VERSION_RE.fullmatch(value):
        raise ValueError("Blender version must be major.minor.patch, e.g. 4.4.3")
    return tuple(map(int, value.split(".")))


def _version_text(version: tuple[int, int, int]) -> str:
    return ".".join(map(str, version))


def validate_feature_catalog(document: object) -> dict[str, dict]:
    if (not isinstance(document, dict) or set(document) != {
            "schema_version", "kind", "preview_only", "features"}
            or document["schema_version"] != 1
            or document["kind"] != "trusted_authored_feature_catalog"
            or document["preview_only"] is not True):
        raise ValueError("Unsupported feature catalog format")
    listed = document["features"]
    if not isinstance(listed, list) or len(listed) != len(TRUSTED_FEATURES):
        raise ValueError("Feature catalog must list exactly the allowlisted authored features")
    entries: dict[str, dict] = {}
    fields = {"id", "name", "source", "required_parts", "requires_features",
              "min_blender", "max_blender"}
    for entry in listed:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError("Unexpected feature metadata fields")
        feature_id = entry["id"]
        if not isinstance(feature_id, str) or feature_id not in TRUSTED_FEATURES or feature_id in entries:
            raise ValueError("Unknown or duplicate feature ID")
        trusted = TRUSTED_FEATURES[feature_id]
        if entry["source"] != trusted["source"]:
            raise ValueError("Feature source changed outside code allowlist: " + feature_id)
        parts = entry["required_parts"]
        if (not isinstance(parts, list) or any(not isinstance(p, str) for p in parts)
                or len(set(parts)) != len(parts) or set(parts) != trusted["parts"]):
            raise ValueError("Part dependencies disagree with trusted implementation: " + feature_id)
        parents = entry["requires_features"]
        if (not isinstance(parents, list) or any(not isinstance(f, str) for f in parents)
                or len(set(parents)) != len(parents)
                or any(f not in TRUSTED_FEATURES for f in parents)):
            raise ValueError("Unknown or repeated feature dependency: " + feature_id)
        name = entry["name"]
        if (not isinstance(name, str) or not 1 <= len(name) <= 80 or
                any(ord(ch) < 32 or ord(ch) == 127 for ch in name)):
            raise ValueError("Invalid feature name")
        minimum = parse_version(entry["min_blender"])
        maximum = parse_version(entry["max_blender"]) if entry["max_blender"] is not None else None
        if minimum < (4, 4, 0) or (maximum is not None and maximum < minimum):
            raise ValueError("Feature Blender compatibility range is invalid")
        entries[feature_id] = entry
    if set(entries) != set(TRUSTED_FEATURES):
        raise ValueError("Missing trusted feature IDs")

    # Validate all graph components, even when a recipe selects only one.
    pending: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in pending:
            raise ValueError("Cycle in authored feature graph: " + node)
        if node in visited:
            return
        pending.add(node)
        for parent in entries[node]["requires_features"]:
            visit(parent)
        pending.remove(node)
        visited.add(node)
    for feature_id in sorted(entries):
        visit(feature_id)
    return entries


def load_feature_catalog(*, root: Path) -> dict[str, dict]:
    project = root.resolve()
    content = _trusted_read(CATALOG_PATH, root=project)
    if len(content) > 200_000:
        raise ValueError("Feature metadata exceeds size limit")
    return validate_feature_catalog(json.loads(content))


def plan_features(
    requested: object,
    *,
    root: Path,
    target_blender: str | None = None,
) -> dict:
    """Plan feature/part closure before packaging; performs no code execution."""
    if (not isinstance(requested, (tuple, list)) or not requested
            or len(requested) > len(TRUSTED_FEATURES)
            or any(not isinstance(f, str) or f not in TRUSTED_FEATURES for f in requested)
            or len(set(requested)) != len(requested)):
        raise ValueError("Requested features must be unique, nonempty and allowlisted")
    project = root.resolve()
    catalog = load_feature_catalog(root=project)
    authored_parts = _read_catalog(root=project)
    ordered: list[str] = []
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visited:
            return
        for dependency in sorted(catalog[node]["requires_features"]):
            visit(dependency)
        visited.add(node)
        ordered.append(node)
    for item in sorted(requested):
        visit(item)

    used_parts = sorted({part for feature in ordered for part in catalog[feature]["required_parts"]})
    for part in used_parts:
        entry = authored_parts.get(part)
        if not isinstance(entry, dict) or entry.get("source") != TRUSTED_PART_SOURCES[part]:
            raise ValueError("Part missing or source mismatch: " + part)
    minimum = max(parse_version(catalog[f]["min_blender"]) for f in ordered)
    maximums = [parse_version(catalog[f]["max_blender"]) for f in ordered
                if catalog[f]["max_blender"] is not None]
    maximum = min(maximums) if maximums else None
    if maximum is not None and minimum > maximum:
        raise ValueError("Selected features have incompatible Blender requirements")
    target = parse_version(target_blender) if target_blender is not None else None
    if target is not None and (target < minimum or (maximum is not None and target > maximum)):
        raise ValueError(
            f"Blender {target_blender} is outside selected preview features' "
            f"{_version_text(minimum)}..{_version_text(maximum) if maximum else 'latest'} range"
        )

    return {
        "schema_version": 1,
        "requested_features": sorted(requested),
        "ordered_features": ordered,
        "dependency_features_added": sorted(set(ordered) - set(requested)),
        "part_ids": used_parts,
        "part_sources": sorted({TRUSTED_PART_SOURCES[p] for p in used_parts}),
        "minimum_blender": _version_text(minimum),
        "maximum_blender": _version_text(maximum) if maximum else None,
        "target_blender": target_blender,
        "compatible_with_target": True if target is not None else None,
        "preview_only": True,
        "approved": False,
        "redistribution_cleared": False,
        "runtime_verified": False,
        "warning": "Static planning only. Not approval, license clearance, or runtime evidence.",
    }
