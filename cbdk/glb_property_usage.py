"""Conservative AST-only *possible* property attribute reference evidence.

Reports only source-identifier/scope/line metadata from explicitly chosen private
Python files. An attribute's text matching a Blender property declaration never
proves receiver identity, runtime registration or geometry effects. Nothing runs.
"""
from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

MAX_FILES = 16
MAX_FILE_BYTES = 1024 * 1024
MAX_REFERENCES_PER_FILE = 4096
MAX_EXAMPLES_PER_PROPERTY = 16
MAX_SCOPE_NAME_LENGTH = 128


class PropertyUsageError(ValueError):
    pass


def _source_ast(source: str | Path) -> ast.Module:
    path = Path(source)
    if path.suffix.lower() != ".py" or path.is_symlink() or not path.is_file():
        raise PropertyUsageError("Expected an explicitly selected regular Python file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise PropertyUsageError("Source exceeds static trace size limit")
    try:
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise PropertyUsageError("Source exceeds static trace size limit")
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        return ast.parse(data.decode(encoding), filename="<private_source>")
    except (UnicodeError, LookupError, SyntaxError, ValueError) as exc:
        raise PropertyUsageError("Unable to statically parse selected Python file") from exc


def _name(value: str) -> str:
    # Never expose a path, a string literal, source line, or unbounded identifier.
    return value if len(value) <= MAX_SCOPE_NAME_LENGTH else "identifier_omitted"


def _receiver_kind(value: ast.AST) -> str:
    if isinstance(value, ast.Name):
        return "self" if value.id == "self" else "unverified_variable"
    if (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name)
            and value.value.id == "context"
            and value.attr in ("scene", "object", "window_manager", "tool_settings")):
        return "context_attribute"
    return "unverified_expression"


class _UsageVisitor(ast.NodeVisitor):
    def __init__(self, names: set[str], index: int):
        self.names = names
        self.label = f"source_{index}.py"
        self.cls: str | None = None
        self.functions: list[str] = []
        self.augmented: ast.AST | None = None
        self.results: dict[str, list[dict]] = {}
        self.total = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Nested classes remain unverified: the class label is a syntactic scope.
        old = self.cls
        self.cls = _name(node.name)
        self.generic_visit(node)
        self.cls = old

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions.append(_name(node.name))
        self.generic_visit(node)
        self.functions.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # A lambda's scope cannot be named reliably; do not claim function provenance.
        self.functions.append("<lambda>")
        self.generic_visit(node)
        self.functions.pop()

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        old = self.augmented
        self.augmented = node.target
        self.visit(node.target)
        self.augmented = old
        self.visit(node.value)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in self.names and self.functions:
            self.total += 1
            if self.total > MAX_REFERENCES_PER_FILE:
                raise PropertyUsageError("Too many attribute references for bounded trace")
            if node is self.augmented:
                kind = "read_write"
            elif isinstance(node.ctx, ast.Store):
                kind = "write"
            elif isinstance(node.ctx, ast.Del):
                kind = "delete"
            else:
                kind = "read"
            self.results.setdefault(node.attr, []).append({
                "source_label": self.label,
                "class_name": self.cls,
                "function_name": ".".join(self.functions),
                "line": node.lineno,
                "access": kind,
                "receiver_kind": _receiver_kind(node.value),
                "association_with_declared_property": "not_verified",
                "geometry_effect": "not_verified",
            })
        self.generic_visit(node)


def trace_property_references(sources: list[str | Path],
                              property_names: set[str]) -> dict[str, dict]:
    """Bounded, name-only static evidence; no imports, exec, AST evaluation or writes."""
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_FILES:
        raise PropertyUsageError("Expected 1..16 explicitly selected source files")
    if not isinstance(property_names, set) or any(
            not isinstance(name, str) or not name.isidentifier()
            for name in property_names):
        raise PropertyUsageError("Expected property identifier set")
    merged: dict[str, list[dict]] = {name: [] for name in property_names}
    for index, source in enumerate(sources, 1):
        visitor = _UsageVisitor(property_names, index)
        visitor.visit(_source_ast(source))
        for name, items in visitor.results.items():
            merged[name].extend(items)
    result = {}
    for name in sorted(merged):
        items = sorted(merged[name], key=lambda x: (
            x["source_label"], x["line"], x["class_name"] or "",
            x["function_name"], x["access"]))
        counts = {kind: sum(x["access"] == kind for x in items)
                  for kind in ("read", "write", "delete", "read_write")}
        # Aggregate all observations before limiting display examples: counts
        # must not depend on the 16-example UI cap. This only identifies
        # syntactic 'self' access in a named class, never actual binding.
        self_scopes: dict[tuple[str, str], dict] = {}
        for site in items:
            if site["receiver_kind"] != "self" or not site["class_name"]:
                continue
            key = (site["source_label"], site["class_name"])
            scope = self_scopes.get(key)
            if scope is None:
                scope = {
                    "source_label": key[0], "class_name": key[1],
                    "possible_reference_count": 0,
                    "access_counts": {kind: 0 for kind in counts},
                    "actual_property_binding_verified": False,
                }
                self_scopes[key] = scope
            scope["possible_reference_count"] += 1
            scope["access_counts"][site["access"]] += 1
        result[name] = {
            "possible_reference_count": len(items),
            "access_counts": counts,
            "examples": items[:MAX_EXAMPLES_PER_PROPERTY],
            "examples_truncated": len(items) > MAX_EXAMPLES_PER_PROPERTY,
            "syntactic_self_scopes": [self_scopes[key] for key in sorted(self_scopes)],
            "receiver_binding_verified": False,
            "runtime_effect_verified": False,
        }
    return result
