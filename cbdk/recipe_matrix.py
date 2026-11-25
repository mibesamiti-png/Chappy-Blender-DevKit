"""Fail-closed legacy recipe matrix and separate authored-feature coverage.

This inspects only the repository's authored metadata and source files; it
never imports Blender, executes scanned add-ons, builds a release package,
grants licenses, or claims that a Blender runtime test has passed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .addon_builder import ROOT, _trusted_read
from .feature_catalog import (
    TRUSTED_FEATURES, TRUSTED_PART_SOURCES, load_feature_catalog, plan_features,
)
from .modular_builder import validate_modular_recipe

# Intentional, independently maintained expected combinations. Changing a
# recipe or registering a new feature requires updating this audit policy.
EXPECTED_RECIPES = {
    "modular_objects": frozenset({"object_selection"}),
    "modular_edit": frozenset({"edit_selection"}),
    "modular_combined": frozenset({"object_selection", "edit_selection"}),
    "modular_geometry": frozenset({"mesh_bounds", "modifier_summary"}),
    "modular_nudge": frozenset({"vertex_nudge"}),
    "modular_all": frozenset({
        "object_selection", "edit_selection", "mesh_bounds",
        "modifier_summary", "vertex_nudge",
    }),
}
# Explicit independent policy: the six legacy recipe rows remain frozen.
EXPECTED_R18_FEATURES = frozenset({"mesh_bounds", "mesh_center"})
EXPECTED_R18_PARTS = frozenset({"BLCTX-001", "BLGEO-001"})
EXPECTED_AUTHORED_FEATURES = frozenset({
    "object_selection", "edit_selection", "mesh_bounds",
    "modifier_summary", "vertex_nudge", "mesh_center",
})
EXPECTED_PARTS = frozenset({
    "BLCTX-001", "BLCTX-002", "BLGEO-001", "BLMOD-001",
    "BME-001", "BME-002", "BME-003",
})


def r18_center_recipe() -> dict:
    """Fixed synthetic authored example, separate from the six legacy files."""
    return {"schema_version": 2, "template": "modular_preview",
            "package_id": "cbdk_modular_preview",
            "display_name": "CBDK R18 Bounds Center",
            "features": ["mesh_bounds", "mesh_center"],
            "purpose": "local_development_preview"}


CHECKED_BLENDER_VERSIONS = ("4.4.3", "4.5.15", "5.2.1")
MAX_RECIPE_BYTES = 20_000


def audit_recipe_matrix(*, root: Path = ROOT) -> dict:
    """Audit all known recipes and exact helper closure without executing code."""
    project = root.resolve()
    catalog = load_feature_catalog(root=project)
    if set(catalog) != set(TRUSTED_FEATURES) or set(catalog) != EXPECTED_AUTHORED_FEATURES:
        raise ValueError("Trusted feature catalog coverage mismatch")
    if set(TRUSTED_PART_SOURCES) != EXPECTED_PARTS:
        raise ValueError("Trusted helper inventory mismatch")
    legacy = EXPECTED_RECIPES["modular_all"]
    if legacy != EXPECTED_AUTHORED_FEATURES - {"mesh_center"}:
        raise ValueError("Legacy modular_all feature policy drift")

    rows = []
    all_features: set[str] = set()
    all_parts: set[str] = set()
    for name, expected in sorted(EXPECTED_RECIPES.items()):
        path = f"recipes/{name}.json"
        raw = _trusted_read(path, root=project)
        if len(raw) > MAX_RECIPE_BYTES:
            raise ValueError("Recipe exceeds size limit: " + name)
        try:
            recipe = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid trusted recipe: " + name) from exc
        display_name, requested = validate_modular_recipe(recipe)
        if frozenset(requested) != expected:
            raise ValueError("Recipe feature drift detected: " + name)
        plans = [
            plan_features(requested, root=project, target_blender=version)
            for version in CHECKED_BLENDER_VERSIONS
        ]
        plan = plans[0]
        if frozenset(plan["ordered_features"]) != expected:
            raise ValueError("Legacy recipe resolved feature drift: " + name)
        for other in plans[1:]:
            if (other["part_ids"] != plan["part_ids"]
                    or other["ordered_features"] != plan["ordered_features"]):
                raise ValueError("Recipe dependency closure differs between Blender targets")
        if (plan["approved"] is not False or plan["redistribution_cleared"] is not False
                or plan["preview_only"] is not True or plan["runtime_verified"] is not False):
            raise ValueError("Unexpected approval or verification claim in plan")
        # plan_features validates metadata paths but does not check source
        # presence. Inspect trusted sources as bytes; NEVER import them.
        for feature in plan["ordered_features"]:
            _trusted_read(TRUSTED_FEATURES[feature]["source"], root=project)
        for source in plan["part_sources"]:
            _trusted_read(source, root=project)
        rows.append({
            "recipe": name, "display_name": display_name,
            "requested_features": list(requested),
            "resolved_features": list(plan["ordered_features"]),
            "part_ids": list(plan["part_ids"]),
            "target_versions_static_compatible": list(CHECKED_BLENDER_VERSIONS),
        })
        all_features.update(plan["ordered_features"])
        all_parts.update(plan["part_ids"])

    if all_features != legacy:
        raise ValueError("Legacy feature is missing from recipe coverage")
    if all_parts != EXPECTED_PARTS:
        raise ValueError("Registered part is missing from recipe coverage")

    # Independently require the new feature, not just whatever the catalog
    # happens to contain. Keep legacy report counts/rows unchanged.
    _, requested = validate_modular_recipe(r18_center_recipe())
    if frozenset(requested) != EXPECTED_R18_FEATURES:
        raise ValueError("R18 recipe feature drift")
    for version in CHECKED_BLENDER_VERSIONS:
        plan = plan_features(requested, root=project, target_blender=version)
        if (frozenset(plan["ordered_features"]) != EXPECTED_R18_FEATURES
                or frozenset(plan["part_ids"]) != EXPECTED_R18_PARTS):
            raise ValueError("R18 recipe dependency closure drift")
        if (plan["approved"] is not False or plan["redistribution_cleared"] is not False
                or plan["preview_only"] is not True or plan["runtime_verified"] is not False):
            raise ValueError("Unexpected approval or verification claim in R18 plan")
        for feature in plan["ordered_features"]:
            _trusted_read(TRUSTED_FEATURES[feature]["source"], root=project)
        for source in plan["part_sources"]:
            _trusted_read(source, root=project)
    if all_features | EXPECTED_R18_FEATURES != EXPECTED_AUTHORED_FEATURES:
        raise ValueError("Authored feature is missing from combined coverage")
    return {
        "schema_version": 1,
        "kind": "cbdk_recipe_static_matrix",
        "status": "static_checks_passed",
        "recipe_count": len(rows),
        "covered_features": sorted(all_features),
        "covered_parts": sorted(all_parts),
        "all_covered_features": sorted(all_features | EXPECTED_R18_FEATURES),
        "additional_authored_coverage": {
            "recipe": "r18_center_synthetic",
            "requested_features": sorted(EXPECTED_R18_FEATURES),
            "resolved_features": sorted(EXPECTED_R18_FEATURES),
            "part_ids": sorted(EXPECTED_R18_PARTS),
            "target_versions_static_compatible": list(CHECKED_BLENDER_VERSIONS),
            "runtime_verified": False,
        },
        "checked_blender_target_versions": list(CHECKED_BLENDER_VERSIONS),
        "recipes": rows,
        "preview_only": True,
        "approved": False,
        "redistribution_cleared": False,
        "blender_runtime_verified": False,
        "gui_tested": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit six trusted CBDK preview recipes")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_recipe_matrix(root=args.root)
    data = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(data, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding="utf-8")
        print("Static preview recipe matrix saved: " + str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
