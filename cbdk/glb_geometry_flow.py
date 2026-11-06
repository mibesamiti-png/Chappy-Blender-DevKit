"""Conservative AST-only property-to-geometry *syntactic* evidence.

Only straight-line statements inside explicitly selected class methods are
considered. A direct self.property expression or a local alias can reach a
small allowlist of Blender geometry APIs. This NEVER proves runtime behavior,
actual receiver identity, registration, a valid mesh, or a causal effect.
No addon source is imported, executed, modified or copied into the report.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .glb_property_usage import _source_ast

MAX_EVENTS_PER_FILE = 4096
MAX_EXAMPLES = 12
PRIMITIVES = frozenset({
    "primitive_cube_add", "primitive_uv_sphere_add", "primitive_ico_sphere_add",
    "primitive_cylinder_add", "primitive_cone_add", "primitive_torus_add",
    "primitive_plane_add", "primitive_circle_add", "primitive_grid_add",
})
BMESH_OPERATIONS = frozenset({
    "create_cube", "create_uvsphere", "create_icosphere", "create_cone",
    "create_circle", "create_grid", "bevel", "subdivide_edges",
    "extrude_face_region", "extrude_edge_only", "inset_individual",
    "bisect_plane", "delete", "translate", "scale", "rotate",
})
TRANSFORM_FIELDS = frozenset({"dimensions", "scale", "location"})
# These are common modifier attributes but any Python object can define them.
# Report only a candidate assignment to such an attribute, never an
# authenticated Blender modifier or a proven effect. This allows reviewers to
# inspect bevel/solidify/boolean code without executing private addons.
MODIFIER_FIELDS = frozenset({
    "width", "segments", "profile", "thickness", "offset", "levels",
    "render_levels", "operation", "solver", "object", "use_self",
    "use_even_offset", "use_clamp_overlap",
})


def _chain(expr: ast.AST) -> tuple[str, ...]:
    names = []
    while isinstance(expr, ast.Attribute):
        names.append(expr.attr)
        expr = expr.value
    if not isinstance(expr, ast.Name):
        return ()
    names.append(expr.id)
    return tuple(reversed(names))


def _imports(tree: ast.Module) -> dict[str, str]:
    aliases = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name in {"bpy", "bmesh"}:
                    aliases[item.asname or item.name] = item.name
    return aliases


def _operation(expr: ast.Call, imports: dict[str, str]) -> tuple[str, str] | None:
    names = _chain(expr.func)
    if len(names) < 3:
        return None
    root = imports.get(names[0])
    if root == "bpy" and len(names) == 4 and names[1:3] == ("ops", "mesh"):
        if names[-1] in PRIMITIVES:
            return "mesh_primitive", "bpy.ops.mesh." + names[-1]
    if root == "bmesh" and len(names) == 3 and names[1] == "ops":
        if names[-1] in BMESH_OPERATIONS:
            return "bmesh_geometry_operation", "bmesh.ops." + names[-1]
    return None


def _dependencies(expr: ast.AST, declared: set[str],
                  locals_: dict[str, set[str]]) -> dict[str, str]:
    """Return syntactic contributing properties and strongest observed form."""
    found: dict[str, str] = {}
    for node in ast.walk(expr):
        if (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self" and node.attr in declared):
            found[node.attr] = "direct_self_attribute"
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            for prop in locals_.get(node.id, ()):
                found.setdefault(prop, "straight_line_local_alias")
    return found


def _calls(expr: ast.AST):
    # Do not descend into lambda / comprehension whose body is a later scope.
    stack = [expr]
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp,
                             ast.DictComp, ast.GeneratorExp)):
            continue
        if isinstance(node, ast.Call):
            yield node
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _trace_method(cls: str, node: ast.FunctionDef | ast.AsyncFunctionDef,
                  declared: set[str], source_label: str,
                  imports: dict[str, str]) -> tuple[list[dict], int]:
    locals_: dict[str, set[str]] = {}
    hits: list[dict] = []
    skipped = 0

    def add(prop: str, category: str, api: str, line: int, mode: str):
        hits.append({
            "property": prop, "source_label": source_label,
            "class_name": cls[:128] if len(cls) <= 128 else "identifier_omitted",
            "function_name": node.name[:128] if len(node.name) <= 128 else "identifier_omitted",
            "line": line, "geometry_operation_category": category,
            "recognized_api": api, "syntactic_path": mode,
            "receiver_binding_verified": False,
            "geometry_effect_verified": False,
        })
        if len(hits) > MAX_EVENTS_PER_FILE:
            raise ValueError("Too many possible geometry flow events")

    for statement in node.body:
        # No interprocedural, loop, branch or exception dataflow is claimed.
        if isinstance(statement, (ast.If, ast.For, ast.AsyncFor, ast.While,
                                  ast.Try, ast.With, ast.AsyncWith, ast.Match,
                                  ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            skipped += 1
            locals_.clear()  # Values may be overwritten along unobserved paths.
            continue
        expression = None
        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            expression = statement.value
        elif isinstance(statement, (ast.Expr, ast.Return)):
            expression = statement.value
        if expression is None:
            if isinstance(statement, ast.Delete):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        locals_.pop(target.id, None)
            continue

        # Find recognized Blender geometry API calls and trace only properties
        # actually present in their argument expressions, not same-function
        # co-occurrence alone.
        for call in _calls(expression):
            operation = _operation(call, imports)
            if operation is None:
                continue
            deps = {}
            for arg in (*call.args, *(kw.value for kw in call.keywords)):
                for key, mode in _dependencies(arg, declared, locals_).items():
                    deps[key] = mode if mode == "direct_self_attribute" else deps.get(key, mode)
            for prop, mode in sorted(deps.items()):
                add(prop, *operation, call.lineno, mode)

        # Explicit object transforms are a potential geometry path only when
        # their assigned expression is itself property-dependent.
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            deps = _dependencies(expression, declared, locals_)
            for target in targets:
                if not isinstance(target, ast.Attribute):
                    continue
                if target.attr in TRANSFORM_FIELDS:
                    category, api = "object_transform_assignment", "object." + target.attr
                elif target.attr in MODIFIER_FIELDS:
                    category, api = "possible_modifier_setting_assignment", "modifier." + target.attr
                else:
                    continue
                for prop, mode in sorted(deps.items()):
                    add(prop, category, api, statement.lineno, mode)

            # Invalidate old aliases on reassignment; only simple local names
            # are tracked, never attributes, indexing, destructuring or scopes.
            for target in targets:
                if isinstance(target, ast.Name):
                    if deps:
                        locals_[target.id] = set(deps)
                    else:
                        locals_.pop(target.id, None)
        elif isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name):
            deps = _dependencies(expression, declared, locals_)
            aliases = set(deps) | locals_.get(statement.target.id, set())
            if aliases:
                locals_[statement.target.id] = aliases
            else:
                locals_.pop(statement.target.id, None)
    return hits, skipped


def trace_geometry_paths(sources: list[str | Path],
                         declared_by_scope: dict[tuple[str, str], set[str]]) -> dict[str, dict]:
    """Return bounded AST evidence keyed by property; no runtime claims."""
    merged: dict[str, list[dict]] = {}
    skipped = 0
    for index, source in enumerate(sources, 1):
        tree = _source_ast(source)
        imports = _imports(tree)
        label = f"source_{index}.py"
        file_hits = 0
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            props = declared_by_scope.get((label, cls.name), set())
            if not props:
                continue
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                hits, ignored = _trace_method(cls.name, fn, props, label, imports)
                skipped += ignored
                file_hits += len(hits)
                if file_hits > MAX_EVENTS_PER_FILE:
                    raise ValueError("Too many geometry flow events in source")
                for item in hits:
                    merged.setdefault(item["property"], []).append(item)
    result = {}
    for prop in sorted({p for group in declared_by_scope.values() for p in group}):
        items = sorted(merged.get(prop, []),
                       key=lambda x: (x["source_label"], x["class_name"],
                                      x["line"], x["geometry_operation_category"],
                                      x["recognized_api"]))
        categories = {}
        for row in items:
            name = row["geometry_operation_category"]
            categories[name] = categories.get(name, 0) + 1
        result[prop] = {
            "possible_path_count": len(items),
            "operation_counts": dict(sorted(categories.items())),
            "examples": items[:MAX_EXAMPLES],
            "examples_truncated": len(items) > MAX_EXAMPLES,
            "limited_to_straight_line_method_statements": True,
            "receiver_binding_verified": False,
            "geometry_effect_verified": False,
        }
    return result
