"""Bounded AST checks on already allowlisted preview assets; never import them.

This catches packaging/registration drift, not arbitrary Python behavior or
licensing. Dynamic imports and runtime Blender registration still need CI.
"""
from __future__ import annotations

import ast
import posixpath
import re
import json
import argparse
import tempfile
from pathlib import Path


def validate_registration_assets(assets: dict[str, bytes], features: tuple[str, ...]) -> dict:
    trees = {}
    for path, data in assets.items():
        if path.endswith(".py"):
            if len(data) > 500_000:
                raise ValueError("Preview Python asset exceeds audit limit: " + path)
            try:
                trees[path] = ast.parse(data, filename=path)
            except (SyntaxError, ValueError) as exc:
                raise ValueError("Invalid preview Python asset: " + path) from exc

    imports = 0
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            # A relative import starts at the containing package, then climbs.
            package = path.split("/")[:-1]
            if node.level > len(package) + 1:
                raise ValueError("Relative import escapes preview package: " + path)
            base = package[:len(package) - node.level + 1]
            if node.module:
                base += node.module.split(".")
                targets = ["/".join(base)]
            else:
                targets = ["/".join(base + [alias.name]) for alias in node.names]
            for target in targets:
                if (target + ".py" not in trees and
                        posixpath.join(target, "__init__.py") not in trees):
                    raise ValueError("Unpackaged relative dependency: " + path + " -> " + target)
                if node.module:
                    dependency = trees.get(target + ".py", trees.get(target + "/__init__.py"))
                    names = set()
                    for statement in dependency.body:
                        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            names.add(statement.name)
                        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                            names.update(a.asname or a.name.split(".")[0] for a in statement.names)
                        elif isinstance(statement, ast.Assign):
                            names.update(n.id for t in statement.targets for n in ast.walk(t)
                                         if isinstance(n, ast.Name))
                        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                            names.add(statement.target.id)
                    if any(alias.name not in names for alias in node.names):
                        raise ValueError("Unresolved static helper export: " + path + " -> " + target)
                imports += 1

    identifiers = set()
    classes = set()
    for feature in features:
        path = "features/" + feature + ".py"
        if path not in trees:
            raise ValueError("Missing feature module: " + feature)
        body = trees[path].body
        bindings = [node.value for node in body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "OPERATOR_CLASS"
                            for t in node.targets)]
        if len(bindings) != 1 or not isinstance(bindings[0], ast.Name):
            raise ValueError("Feature needs one explicit OPERATOR_CLASS: " + feature)
        definitions = [node for node in body if isinstance(node, ast.ClassDef)
                       and node.name == bindings[0].id]
        if len(definitions) != 1:
            raise ValueError("Unresolved operator class: " + feature)
        cls = definitions[0]
        ids = [node.value for node in cls.body if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "bl_idname" for t in node.targets)]
        if (len(ids) != 1 or not isinstance(ids[0], ast.Constant)
                or not isinstance(ids[0].value, str)
                or not ids[0].value.startswith("cbdk.")):
            raise ValueError("Operator needs an explicit CBDK bl_idname: " + feature)
        if ids[0].value in identifiers or cls.name in classes:
            raise ValueError("Duplicate operator registration: " + feature)
        identifiers.add(ids[0].value)
        classes.add(cls.name)
    return {"relative_imports_checked": imports,
            "operator_ids": sorted(identifiers), "runtime_verified": False}


def audit_registration(*, root: Path) -> dict:
    """Cross-check the independent runtime/CI inventory and six real builds."""
    from .addon_builder import _trusted_read
    from .feature_catalog import TRUSTED_FEATURES
    from .recipe_matrix import EXPECTED_RECIPES, audit_recipe_matrix
    from .modular_builder import build_modular

    root = root.resolve()
    matrix = audit_recipe_matrix(root=root)
    smoke = ast.parse(_trusted_read("scripts/blender_modular_addon_smoke.py", root=root))
    known = [n.value for n in smoke.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "KNOWN" for t in n.targets)]
    if len(known) != 1:
        raise ValueError("Runtime feature inventory must be explicit")
    try:
        inventory = ast.literal_eval(known[0])
    except (ValueError, TypeError) as exc:
        raise ValueError("Runtime feature inventory must be literal") from exc
    if not isinstance(inventory, set) or inventory != set(TRUSTED_FEATURES):
        raise ValueError("Runtime feature inventory disagrees with trusted catalog")
    workflow = _trusted_read(".github/workflows/blender-smoke.yml", root=root).decode("utf-8")
    loops = re.findall(r"^\s*for recipe in ([a-z0-9_ ]+); do\s*$", workflow, re.MULTILINE)
    if (len(loops) != 1 or len(loops[0].split()) != len(EXPECTED_RECIPES)
            or set(loops[0].split()) != set(EXPECTED_RECIPES)):
        raise ValueError("Blender CI recipe inventory disagrees with static matrix")
    with tempfile.TemporaryDirectory(prefix="cbdk-registration-audit-") as directory:
        for name in sorted(EXPECTED_RECIPES):
            recipe = json.loads(_trusted_read("recipes/" + name + ".json", root=root))
            build_modular(recipe, Path(directory) / (name + ".zip"),
                          preview_unapproved=True, root=root)
    return {"schema_version": 1, "kind": "cbdk_registration_static_audit",
            "status": "static_checks_passed", "recipe_count": matrix["recipe_count"],
            "features": matrix["covered_features"], "preview_only": True,
            "approved": False, "runtime_verified": False,
            "redistribution_cleared": False}


def main(argv=None):
    from .addon_builder import ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    print(json.dumps(audit_registration(root=args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
