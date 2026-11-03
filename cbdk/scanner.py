"""Static-only source analysis: never import or execute the inspected addons."""
from __future__ import annotations

import ast
import hashlib
import os
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", "build", "dist"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_python_files(paths: Iterable[str | Path]) -> list[Path]:
    found: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix.lower() == ".py":
            found.add(path.resolve())
        elif path.is_dir():
            for candidate in path.rglob("*.py"):
                if not any(part in EXCLUDE_DIRS for part in candidate.parts):
                    found.add(candidate.resolve())
    return sorted(found)


def _call_name(expr: ast.AST) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        root = _call_name(expr.value)
        return f"{root}.{expr.attr}" if root else expr.attr
    return ""


def _defined_symbols(tree: ast.AST) -> list[tuple[str, ast.AST, str]]:
    """Collect module functions, classes and methods; keep nested defs out of catalog."""
    symbols: list[tuple[str, ast.AST, str]] = []
    for n in getattr(tree, "body", []):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append((n.name, n, "function"))
        elif isinstance(n, ast.ClassDef):
            symbols.append((n.name, n, "class"))
            for child in n.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append((f"{n.name}.{child.name}", child, "method"))
    return symbols


def _signature(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        try:
            prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
            return prefix + node.name + "(" + ast.unparse(node.args) + ")" + (
                " -> " + ast.unparse(node.returns) if node.returns is not None else ""
            )
        except (AttributeError, ValueError, TypeError):
            return f"def {node.name}(...)"
    return f"class {getattr(node, 'name', 'Unknown')}"


class _Canonicalizer(ast.NodeTransformer):
    def __init__(self, *, relaxed: bool):
        self.relaxed = relaxed

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node = self.generic_visit(node)
        node.name = "_FUNCTION_"
        self._strip_docstring(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node = self.generic_visit(node)
        node.name = "_FUNCTION_"
        self._strip_docstring(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node = self.generic_visit(node)
        node.name = "_CLASS_"
        self._strip_docstring(node)
        return node

    @staticmethod
    def _strip_docstring(node: ast.AST) -> None:
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:]

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if self.relaxed:
            node.id = "_NAME_"
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        if self.relaxed:
            node.arg = "_ARG_"
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if self.relaxed:
            node.value = ("_STRING_" if isinstance(node.value, str) else
                          "_NUMBER_" if isinstance(node.value, (int, float, complex)) and not isinstance(node.value, bool)
                          else node.value)
        return node


def _fingerprint(node: ast.AST, *, relaxed: bool) -> str:
    # Parse copy to avoid mutating the original AST or corrupting later analysis.
    clone = ast.parse(ast.unparse(node)).body[0]
    normal = _Canonicalizer(relaxed=relaxed).visit(clone)
    return sha256(ast.dump(normal, include_attributes=False).encode("utf-8"))


def _category(symbol: str, calls: list[str]) -> str:
    hay = (symbol + " " + " ".join(calls)).lower()
    for cat, words in [
        ("ui", ("panel", "layout", "draw", "menu", "uilist")),
        ("io", ("export", "import", "save", "load", "file", "path", "json", "stl")),
        ("mesh", ("bmesh", "mesh", "face", "edge", "vert", "topology")),
        ("geometry", ("vector", "normal", "transform", "rotate", "matrix", "project", "basis")),
        ("object", ("object", "collection", "selection", "select")),
        ("modifier", ("modifier", "boolean", "bevel", "subsurf")),
        ("material", ("material", "shader", "node")),
        ("settings", ("property", "preset", "register", "unregister", "settings")),
    ]:
        if any(x in hay for x in words):
            return cat
    return "misc"


def _bl_info(tree: ast.Module) -> dict:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "bl_info" for t in node.targets):
            try:
                info = ast.literal_eval(node.value)
                if isinstance(info, dict):
                    return {k: list(v) if isinstance(v, tuple) else v for k, v in info.items() if isinstance(k, str) and isinstance(v, (str, int, float, bool, tuple, list))}
            except (ValueError, SyntaxError, TypeError, MemoryError):
                pass
    return {}


def scan(paths: Iterable[str | Path]) -> dict:
    files = []
    symbols = []
    for path in iter_python_files(paths):
        raw = path.read_bytes()
        display_path = os.path.relpath(path, Path.cwd())
        file_record = {"path": display_path, "name": path.name, "sha256": sha256(raw), "bytes": len(raw), "status": "parsed", "bl_info": {}}
        files.append(file_record)
        try:
            content = raw.decode("utf-8-sig")
            tree = ast.parse(content, filename=str(path))
        except (UnicodeError, SyntaxError, ValueError) as exc:
            file_record["status"] = "parse_error"
            file_record["error"] = str(exc)
            continue
        file_record["bl_info"] = _bl_info(tree)
        imports = sorted({alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names} |
                         {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)})
        file_record["imports"] = imports
        for name, node, kind in _defined_symbols(tree):
            calls = sorted({_call_name(n.func) for n in ast.walk(node) if isinstance(n, ast.Call) and _call_name(n.func)})
            type_hist = dict(sorted(Counter(type(n).__name__ for n in ast.walk(node)).items()))
            n_nodes = sum(type_hist.values())
            symbol_id = "CND-" + sha256((file_record["sha256"] + ":" + name + ":" + kind).encode())[:14].upper()
            symbols.append({
                "id": symbol_id, "source": display_path, "source_name": path.name,
                "qualname": name, "kind": kind, "signature": _signature(node),
                "line": getattr(node, "lineno", None), "end_line": getattr(node, "end_lineno", None),
                "doc": (ast.get_docstring(node) or "")[:600], "calls": calls,
                "category": _category(name, calls), "node_count": n_nodes,
                "type_hist": type_hist, "exact_ast_sha256": _fingerprint(node, relaxed=False),
                "shape_sha256": _fingerprint(node, relaxed=True),
                "status": "candidate", "verification": "static_parse_only",
                "license": "unverified", "dependencies": [],
            })
    return {"schema_version": 1, "files": files, "symbols": symbols,
            "notice": "Candidates only; not guaranteed portable, licensed, or Blender-runtime tested."}
