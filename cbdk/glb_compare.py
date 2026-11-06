"""Compare trusted Blender GLB scene metadata for shape regression.

The comparator consumes CBDK-generated scene_metadata.json files. It never loads
user geometry, executes Blender code, or follows external resources. Shape mode
focuses on world-space bounds and placement; strict mode also requires topology
counts and exact object-name coverage.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

MAX_METADATA_BYTES = 8 * 1024 * 1024
PROFILES = {"shape", "strict"}


class SceneComparisonError(ValueError):
    pass


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SceneComparisonError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise SceneComparisonError(f"{label} must be finite")
    return number


def _vec3(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise SceneComparisonError(f"{label} must be a length-3 array")
    return [_finite(v, f"{label}[{i}]") for i, v in enumerate(value)]


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _sub(a: list[float], b: list[float]) -> list[float]:
    return [x - y for x, y in zip(a, b)]


def _rel_error(a: list[float], b: list[float]) -> float:
    result = 0.0
    for left, right in zip(a, b):
        denom = max(abs(left), abs(right), 1e-9)
        result = max(result, abs(left - right) / denom)
    return result


def _volume_proxy(size: list[float]) -> float:
    return max(size[0], 0.0) * max(size[1], 0.0) * max(size[2], 0.0)


def _load(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise SceneComparisonError(f"Scene metadata not found: {source}")
    if source.stat().st_size > MAX_METADATA_BYTES:
        raise SceneComparisonError("Scene metadata exceeds safe size limit")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SceneComparisonError(f"Invalid scene metadata: {source}") from exc
    if not isinstance(data, dict) or data.get("kind") != "cbdk_glb_blender_scene_metadata":
        raise SceneComparisonError("Expected CBDK Blender scene metadata")
    return data


def _bounds(value: Any, label: str) -> dict[str, list[float]]:
    if not isinstance(value, dict):
        raise SceneComparisonError(f"{label} must be an object")
    minimum = _vec3(value.get("min"), label + ".min")
    maximum = _vec3(value.get("max"), label + ".max")
    center = _vec3(value.get("center"), label + ".center")
    size = _vec3(value.get("size"), label + ".size")
    if any(lo > hi for lo, hi in zip(minimum, maximum)) or any(x < 0 for x in size):
        raise SceneComparisonError(f"{label} contains invalid bounds")
    return {"min": minimum, "max": maximum, "center": center, "size": size}


def _object_bounds(row: dict, label: str) -> dict[str, list[float]]:
    world = row.get("world_bounds")
    if world is not None:
        return _bounds(world, label + ".world_bounds")

    # Backward-compatible fallback for schema-2 evidence. Blender's object
    # dimensions plus matrix translation are less precise for rotated objects,
    # so the result records that legacy fallback was used.
    size = _vec3(row.get("dimensions"), label + ".dimensions")
    matrix = row.get("world_matrix")
    if (
        not isinstance(matrix, list) or len(matrix) != 4
        or any(not isinstance(r, list) or len(r) != 4 for r in matrix)
    ):
        raise SceneComparisonError(f"{label} lacks world_bounds and valid world_matrix")
    center = [_finite(matrix[i][3], f"{label}.world_matrix[{i}][3]") for i in range(3)]
    half = [x * 0.5 for x in size]
    return {
        "min": [c - h for c, h in zip(center, half)],
        "max": [c + h for c, h in zip(center, half)],
        "center": center,
        "size": size,
    }


def _objects(data: dict, label: str) -> list[dict]:
    rows = data.get("objects")
    if not isinstance(rows, list) or not rows:
        raise SceneComparisonError(f"{label}.objects must be a non-empty array")
    count = data.get("object_count")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(rows):
        raise SceneComparisonError(f"{label}.object_count does not match objects")
    result = []
    names = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SceneComparisonError(f"{label}.objects[{i}] must be an object")
        name = row.get("name")
        if not isinstance(name, str) or not name:
            raise SceneComparisonError(f"{label}.objects[{i}].name is invalid")
        if name in names:
            raise SceneComparisonError(f"{label} contains duplicate object name: {name}")
        names.add(name)
        result.append({
            "name": name,
            "bounds": _object_bounds(row, f"{label}.objects[{i}]"),
            "vertices": row.get("vertices"),
            "edges": row.get("edges"),
            "polygons": row.get("polygons"),
            "legacy_bounds_fallback": "world_bounds" not in row,
        })
    return result


def _topology_value(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SceneComparisonError(f"{label} must be a non-negative integer")
    return value


def _pair_cost(ref: dict, cand: dict, diagonal: float) -> tuple[float, float, float]:
    dim = _rel_error(ref["bounds"]["size"], cand["bounds"]["size"])
    center = _norm(_sub(ref["bounds"]["center"], cand["bounds"]["center"])) / max(diagonal, 1e-9)
    return dim + center, dim, center


def _match_objects(reference: list[dict], candidate: list[dict], diagonal: float,
                   fallback_limit: float) -> tuple[list[tuple[dict, dict, str]], list[dict], list[dict]]:
    ref_by_name = {row["name"]: row for row in reference}
    cand_by_name = {row["name"]: row for row in candidate}
    pairs = []
    matched_ref = set()
    matched_cand = set()

    for name in sorted(set(ref_by_name) & set(cand_by_name)):
        pairs.append((ref_by_name[name], cand_by_name[name], "name"))
        matched_ref.add(name)
        matched_cand.add(name)

    ref_left = [row for row in reference if row["name"] not in matched_ref]
    cand_left = [row for row in candidate if row["name"] not in matched_cand]
    costs = []
    for ri, ref in enumerate(ref_left):
        for ci, cand in enumerate(cand_left):
            cost, dim, center = _pair_cost(ref, cand, diagonal)
            costs.append((cost, dim, center, ref["name"], cand["name"], ri, ci))
    used_r = set()
    used_c = set()
    for cost, _dim, _center, _rn, _cn, ri, ci in sorted(costs):
        if cost > fallback_limit or ri in used_r or ci in used_c:
            continue
        used_r.add(ri)
        used_c.add(ci)
        pairs.append((ref_left[ri], cand_left[ci], "geometry"))

    missing = [row for i, row in enumerate(ref_left) if i not in used_r]
    extra = [row for i, row in enumerate(cand_left) if i not in used_c]
    return pairs, missing, extra


def compare_scene_metadata(
    reference: dict,
    candidate: dict,
    *,
    profile: str = "shape",
    dimension_rel_tol: float = 0.05,
    center_rel_tol: float = 0.03,
    scene_rel_tol: float = 0.05,
    fallback_match_limit: float = 0.60,
    minor_volume_fraction: float = 0.01,
) -> dict:
    if profile not in PROFILES:
        raise SceneComparisonError(f"Unknown comparison profile: {profile}")
    for name, value in (
        ("dimension_rel_tol", dimension_rel_tol),
        ("center_rel_tol", center_rel_tol),
        ("scene_rel_tol", scene_rel_tol),
        ("fallback_match_limit", fallback_match_limit),
        ("minor_volume_fraction", minor_volume_fraction),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
            raise SceneComparisonError(f"{name} must be a non-negative finite number")

    ref_scene = _bounds(reference.get("bounds"), "reference.bounds")
    cand_scene = _bounds(candidate.get("bounds"), "candidate.bounds")
    ref_objects = _objects(reference, "reference")
    cand_objects = _objects(candidate, "candidate")

    diagonal = max(_norm(ref_scene["size"]), 1e-9)
    differences = []

    def add(code: str, severity: str, message: str, **metrics) -> None:
        differences.append({
            "code": code,
            "severity": severity,
            "message": message,
            "metrics": metrics,
        })

    scene_dim_error = _rel_error(ref_scene["size"], cand_scene["size"])
    scene_center_error = _norm(_sub(ref_scene["center"], cand_scene["center"])) / diagonal
    if scene_dim_error > scene_rel_tol:
        add("scene_dimensions", "error", "Overall scene dimensions differ beyond tolerance",
            relative_error=scene_dim_error, tolerance=scene_rel_tol,
            reference=ref_scene["size"], candidate=cand_scene["size"])
    if scene_center_error > center_rel_tol:
        add("scene_center", "error", "Overall scene center differs beyond tolerance",
            relative_error=scene_center_error, tolerance=center_rel_tol,
            reference=ref_scene["center"], candidate=cand_scene["center"])

    pairs, missing, extra = _match_objects(
        ref_objects, cand_objects, diagonal, float(fallback_match_limit)
    )
    ref_total_volume = max(sum(_volume_proxy(x["bounds"]["size"]) for x in ref_objects), 1e-12)
    cand_total_volume = max(sum(_volume_proxy(x["bounds"]["size"]) for x in cand_objects), 1e-12)

    pair_rows = []
    for ref, cand, match_method in sorted(pairs, key=lambda p: p[0]["name"]):
        _cost, dim_error, center_error = _pair_cost(ref, cand, diagonal)
        row = {
            "reference": ref["name"],
            "candidate": cand["name"],
            "match": match_method,
            "dimension_rel_error": dim_error,
            "center_rel_error": center_error,
        }
        pair_rows.append(row)
        if dim_error > dimension_rel_tol:
            add("object_dimensions", "error", f"Dimensions differ for {ref['name']}",
                reference_object=ref["name"], candidate_object=cand["name"],
                relative_error=dim_error, tolerance=dimension_rel_tol,
                reference=ref["bounds"]["size"], candidate=cand["bounds"]["size"])
        if center_error > center_rel_tol:
            add("object_center", "error", f"World position differs for {ref['name']}",
                reference_object=ref["name"], candidate_object=cand["name"],
                relative_error=center_error, tolerance=center_rel_tol,
                reference=ref["bounds"]["center"], candidate=cand["bounds"]["center"])

        topology_changed = []
        for field in ("vertices", "edges", "polygons"):
            left = _topology_value(ref[field], f"reference.{ref['name']}.{field}")
            right = _topology_value(cand[field], f"candidate.{cand['name']}.{field}")
            if left != right:
                topology_changed.append({"field": field, "reference": left, "candidate": right})
        if topology_changed:
            add(
                "object_topology",
                "error" if profile == "strict" else "info",
                f"Topology counts differ for {ref['name']}",
                reference_object=ref["name"], candidate_object=cand["name"],
                changes=topology_changed,
            )
        if match_method != "name":
            add(
                "object_name_fallback",
                "error" if profile == "strict" else "info",
                f"Matched {ref['name']} to {cand['name']} by geometry",
                reference_object=ref["name"], candidate_object=cand["name"],
            )

    for row in missing:
        fraction = _volume_proxy(row["bounds"]["size"]) / ref_total_volume
        severity = "error" if profile == "strict" or fraction > minor_volume_fraction else "warning"
        add("missing_reference_object", severity, f"Reference object is missing: {row['name']}",
            object=row["name"], volume_fraction=fraction)

    for row in extra:
        fraction = _volume_proxy(row["bounds"]["size"]) / cand_total_volume
        severity = "error" if profile == "strict" or fraction > minor_volume_fraction else "warning"
        add("extra_candidate_object", severity, f"Candidate has extra object: {row['name']}",
            object=row["name"], volume_fraction=fraction)

    if profile == "strict" and len(ref_objects) != len(cand_objects):
        add("object_count", "error", "Strict profile requires identical object counts",
            reference=len(ref_objects), candidate=len(cand_objects))

    errors = sum(1 for d in differences if d["severity"] == "error")
    warnings = sum(1 for d in differences if d["severity"] == "warning")
    infos = sum(1 for d in differences if d["severity"] == "info")
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_scene_comparison",
        "profile": profile,
        "passed": errors == 0,
        "reference_source": reference.get("source_name"),
        "candidate_source": candidate.get("source_name"),
        "summary": {
            "reference_objects": len(ref_objects),
            "candidate_objects": len(cand_objects),
            "matched_objects": len(pairs),
            "missing_objects": len(missing),
            "extra_objects": len(extra),
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
            "scene_dimension_rel_error": scene_dim_error,
            "scene_center_rel_error": scene_center_error,
        },
        "tolerances": {
            "dimension_rel_tol": float(dimension_rel_tol),
            "center_rel_tol": float(center_rel_tol),
            "scene_rel_tol": float(scene_rel_tol),
            "fallback_match_limit": float(fallback_match_limit),
            "minor_volume_fraction": float(minor_volume_fraction),
        },
        "matches": pair_rows,
        "differences": differences,
        "evidence": {
            "uses_world_bounds": all(not x["legacy_bounds_fallback"] for x in ref_objects + cand_objects),
            "topology_is_shape_requirement": profile == "strict",
        },
    }


def compare_scene_metadata_files(reference: str | Path, candidate: str | Path, **kwargs) -> dict:
    return compare_scene_metadata(_load(reference), _load(candidate), **kwargs)


def write_scene_comparison(reference: str | Path, candidate: str | Path,
                           output: str | Path, **kwargs) -> dict:
    report = compare_scene_metadata_files(reference, candidate, **kwargs)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
