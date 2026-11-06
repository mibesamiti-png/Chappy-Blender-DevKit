"""Fail-closed static matrix for CBDK's six trusted modular preview recipes.

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
CHECKED_BLENDER_VERSIONS = ("4.4.3", "4.5.15", "5.2.1")
MAX_RECIPE_BYTES = 20_000


def audit_recipe_matrix(*, root: Path = ROOT) -> dict:
    """Audit all known recipes and exact helper closure without executing code."""
    project = root.resolve()
    catalog = load_feature_catalog(root=project)
    if set(catalog) != set(TRUSTED_FEATURES):
        raise ValueError("Trusted feature catalog coverage mismatch")
    if EXPECTED_RECIPES["modular_all"] != set(TRUSTED_FEATURES):
        raise ValueError("modular_all policy no longer covers every trusted feature")

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

    if all_features != set(TRUSTED_FEATURES):
        raise ValueError("Registered feature is missing from recipe coverage")
    if all_parts != set(TRUSTED_PART_SOURCES):
        raise ValueError("Registered part is missing from recipe coverage")
    return {
        "schema_version": 1,
        "kind": "cbdk_recipe_static_matrix",
        "status": "static_checks_passed",
        "recipe_count": len(rows),
        "covered_features": sorted(all_features),
        "covered_parts": sorted(all_parts),
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
