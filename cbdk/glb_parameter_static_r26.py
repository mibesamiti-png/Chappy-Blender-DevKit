"""R26 fixed-fixture static evidence, not registration or causal proof.

Internal test helper. No arbitrary source path is exposed by the entry point.
The private source helper is used only by synthetic AST regression tests.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from .glb_diagnose import diagnose_comparison
from .glb_repair_plan import build_repair_plan
from .glb_property_map import map_repair_plan_properties

CASE_ID = "parameter_fixture_r26"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cbdk_parameter_experiment.py"
VERSIONS = ("4.4.3", "4.5.15", "5.2.1")
EXPECTED_CLASS = "CBDKParameterExperimentSettings"
# Explicit fixed experiment mapping, NOT a general category-to-property rule.
PROPERTIES = (
    ("sphere_radius", "CBDK_Param_Sphere", "part_size_parameter",
     "bpy.ops.mesh.primitive_uv_sphere_add"),
    ("bevel_width", "CBDK_Param_BevelCube", "topology_or_modifier_difference",
     "modifier.width"),
)


def _fixture_plan(comparison=None):
    # A controlled synthetic diagnosis input only establishes the vocabulary.
    # It does not imply the actual bevel experiment triggered a topology finding.
    if comparison is None:
        comparison = {
            "kind": "cbdk_glb_scene_comparison", "schema_version": 1,
            "passed": False, "summary": {"errors": 2},
            "differences": [
                {"code": "object_dimensions", "severity": "error",
                 "metrics": {"reference_object": "CBDK_Param_Sphere"}},
                {"code": "object_topology", "severity": "error",
                 "metrics": {"reference_object": "CBDK_Param_BevelCube"}},
            ],
        }
    plan = build_repair_plan(diagnose_comparison(comparison))
    # Add fixture identifiers only for an actually present matching category.
    # No fabrication of missing diagnostics, and no changes to public rules.
    for row in plan["recommendations"]:
        row["possible_parameter_families"] = [
            prop for prop, target, category, _ in PROPERTIES
            if row["target"] == target and row["suspected_category"] == category
        ]
    return plan


def _observe_source(source):
    """AST-only observation using existing inventory, usage, and flow reports."""
    plan = _fixture_plan()
    mapping = map_repair_plan_properties(plan, [source])
    rows = []
    for prop, target, category, api in PROPERTIES:
        recommendation = next(row for row in mapping["recommendations"]
                              if row["target"] == target
                              and row["suspected_category"] == category)
        hit = next((item for item in recommendation["exact_name_matches"]
                    if item["candidate_family"] == prop), None)
        result = dict(property=prop, declaration_count=0, same_class_self_count=0,
                      geometry_path_count=0, expected_api_observed=False)
        if hit is not None:
            decls = hit["declarations"]
            result["declaration_count"] = len(decls)
            expected = [d for d in decls if d["class_name"] == EXPECTED_CLASS
                        and d["property_constructor"] == "FloatProperty"]
            if expected:
                scopes = hit["possible_code_references"]["syntactic_self_scopes"]
                result["same_class_self_count"] = sum(
                    s["possible_reference_count"] for s in scopes
                    if s["class_name"] == EXPECTED_CLASS and s["source_label"] == "source_1.py")
                flow = hit["possible_geometry_dataflow"]
                # Existing examples are capped. Never infer an exact scoped
                # count from a truncated list or conflate same-name classes.
                if flow["examples_truncated"]:
                    raise ValueError("fixed_fixture_geometry_paths_truncated")
                paths = [p for p in flow["examples"]
                         if p["class_name"] == EXPECTED_CLASS
                         and p["source_label"] == "source_1.py"
                         and p["function_name"] == "build_geometry"]
                result["geometry_path_count"] = len(paths)
                result["expected_api_observed"] = (
                    len(decls) == len(expected) == 1
                    and result["same_class_self_count"] > 0
                    and any(p["recognized_api"] == api for p in paths))
        rows.append(result)
    return rows


def observe_fixed_parameter_fixture(*, run_id: str, source_sha256: str,
                                    blender_version: str) -> dict:
    """Return only fixed contract observations; SHA is consistency, not authority."""
    if (type(run_id) is not str or re.fullmatch("[0-9a-f]{32}", run_id) is None
            or type(source_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", source_sha256) is None
            or blender_version not in VERSIONS):
        raise ValueError("invalid_fixed_fixture_identity")
    if FIXTURE.is_symlink() or not FIXTURE.is_file():
        raise ValueError("fixed_fixture_missing")
    if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != source_sha256:
        raise ValueError("fixed_fixture_source_mismatch")
    rows = _observe_source(FIXTURE)
    if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != source_sha256:
        raise ValueError("fixed_fixture_source_changed")
    return {"case_id": CASE_ID, "run_id": run_id, "source_sha256": source_sha256,
            "blender_version": blender_version, "properties": rows}


def fixed_diagnostic_candidates(comparison: dict) -> list[dict]:
    """Actual comparison input: only fixture target/category pairs that exist.

    No arbitrary text, numeric correction, registration or causal claim is returned.
    """
    plan = _fixture_plan(comparison)
    return [{"property": prop, "target": target, "category": category}
            for prop, target, category, _ in PROPERTIES
            if any(row["target"] == target and row["suspected_category"] == category
                   and prop in row["possible_parameter_families"]
                   for row in plan["recommendations"])]
