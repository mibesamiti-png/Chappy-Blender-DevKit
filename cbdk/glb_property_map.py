"""Static, private, non-executing Blender property inventory + GLB plan matching.

Only named Python source files explicitly supplied by the caller are parsed with
ast.parse. Nothing is imported or executed; no snippet, literal value, default,
absolute path or original source is copied into the output report.

An AST declaration is NOT evidence that a class is registered, the property is
available in Blender, or it controls geometry. Even exact names need review.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("reports/latest")
MAX_SOURCES = 16
MAX_SOURCE_BYTES = 1024 * 1024
MAX_PLAN_BYTES = 2 * 1024 * 1024
MAX_RECOMMENDATIONS = 2048
MAX_CANDIDATES_PER_ITEM = 64

PROPERTY_CONSTRUCTORS = frozenset({
    "BoolProperty", "BoolVectorProperty", "IntProperty", "IntVectorProperty",
    "FloatProperty", "FloatVectorProperty", "StringProperty", "EnumProperty",
    "PointerProperty", "CollectionProperty",
})
IDENTIFIER = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{0,127}\Z")


class PropertyMappingError(ValueError):
    pass


def _imported_constructors(tree: ast.Module) -> tuple[set[str], set[str], set[str]]:
    """Collect only visible bpy.props call aliases from module-level imports."""
    names, bpy_aliases, props_aliases = set(), set(), set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "bpy":
                    bpy_aliases.add(item.asname or "bpy")
                elif item.name == "bpy.props":
                    if item.asname:
                        props_aliases.add(item.asname)
                    else:
                        bpy_aliases.add("bpy")
        if isinstance(node, ast.ImportFrom):
            if node.module == "bpy.props" and node.level == 0:
                for item in node.names:
                    if item.name in PROPERTY_CONSTRUCTORS:
                        names.add(item.asname or item.name)
            if node.module == "bpy" and node.level == 0:
                for item in node.names:
                    if item.name == "props":
                        props_aliases.add(item.asname or "props")
    return names, bpy_aliases, props_aliases


def _constructor(expr: ast.AST, imports: tuple[set[str], set[str], set[str]]) -> str | None:
    if not isinstance(expr, ast.Call):
        return None
    func = expr.func
    names, bpy_aliases, props_aliases = imports
    if isinstance(func, ast.Name) and func.id in names:
        # Aliases can be renamed, so keep only a safe generic type label.
        return "imported_bpy_property"
    if isinstance(func, ast.Attribute) and func.attr in PROPERTY_CONSTRUCTORS:
        base = func.value
        if isinstance(base, ast.Name) and base.id in props_aliases:
            return func.attr
        if (isinstance(base, ast.Attribute) and base.attr == "props"
                and isinstance(base.value, ast.Name) and base.value.id in bpy_aliases):
            return func.attr
    return None


def _inventory(source: str | Path, *, file_index: int) -> list[dict]:
    path = Path(source)
    if path.suffix.lower() != ".py" or path.is_symlink() or not path.is_file():
        raise PropertyMappingError("Expected a regular, non-symlinked Python source file")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise PropertyMappingError("Source exceeds local static-analysis size limit")
    try:
        data = path.read_bytes()
        if len(data) > MAX_SOURCE_BYTES:
            raise PropertyMappingError("Source exceeds local static-analysis size limit")
        import io
        import tokenize
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        tree = ast.parse(data.decode(encoding), filename="<private_addon_source>")
    except (SyntaxError, UnicodeError, LookupError, ValueError) as exc:
        raise PropertyMappingError("Python source could not be parsed safely") from exc

    imports = _imported_constructors(tree)
    result = []
    # Only class-level direct definitions; never a local variable or guessed
    # instance attribute, and never a constructor inside an uncalled function.
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            entries = []
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                expr = node.value if node.value is not None else node.annotation
                entries = [(node.target.id, expr)]
            elif isinstance(node, ast.Assign):
                entries = [(t.id, node.value) for t in node.targets if isinstance(t, ast.Name)]
            for prop_name, expression in entries:
                kind = _constructor(expression, imports)
                if kind is None or not IDENTIFIER.fullmatch(prop_name):
                    continue
                result.append({
                    "property": prop_name,
                    "class_name": cls.name,
                    "property_constructor": kind,
                    "source_label": f"source_{file_index}.py",
                    "line": node.lineno,
                    "evidence": "ast_class_property_declaration_only",
                    "registered_in_blender": "not_checked",
                    "controls_geometry": "not_checked",
                })
    return result


def _validate_plan(plan: dict) -> list[dict]:
    if not isinstance(plan, dict) or plan.get("kind") != "cbdk_glb_repair_plan":
        raise PropertyMappingError("Expected CBDK GLB repair plan JSON")
    if plan.get("status") != "review_only" or plan.get("schema_version") != 1:
        raise PropertyMappingError("Only schema-1 review-only plans are supported")
    safety = plan.get("safety")
    flags = ("edits_code", "applies_parameters", "runs_untrusted_addons",
             "auto_approves", "auto_merges", "private_geometry_required")
    if not isinstance(safety, dict) or any(safety.get(k) is not False for k in flags):
        raise PropertyMappingError("Unsafe or modified plan approval flags")
    rows = plan.get("recommendations")
    if (not isinstance(rows, list) or len(rows) > MAX_RECOMMENDATIONS
            or type(plan.get("recommendation_count")) is not int
            or len(rows) != plan["recommendation_count"]):
        raise PropertyMappingError("Invalid plan recommendation count")
    for row in rows:
        if not isinstance(row, dict) or row.get("requires_human_parameter_mapping") is not True:
            raise PropertyMappingError("Unreviewed mapping flag must remain true")
        candidates = row.get("possible_parameter_families")
        if (not isinstance(candidates, list) or len(candidates) > MAX_CANDIDATES_PER_ITEM
                or any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in candidates)):
            raise PropertyMappingError("Invalid candidate parameter identifiers")
        for key in ("target", "suspected_category"):
            if (not isinstance(row.get(key), str) or not row[key]
                    or len(row[key]) > 192 or any(ord(ch) < 32 for ch in row[key])):
                raise PropertyMappingError("Invalid plan target/category")
    return rows


def map_repair_plan_properties(plan: dict, sources: list[str | Path]) -> dict:
    """Correlate declared class properties and family names. No runtime claims."""
    recommendations = _validate_plan(plan)
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCES:
        raise PropertyMappingError("Provide 1..16 explicitly selected Python source files")
    declarations = []
    for index, source in enumerate(sources, 1):
        declarations.extend(_inventory(source, file_index=index))
    # A repeated declaration may be an override or conflict; expose it and
    # require human interpretation rather than silently selecting one.
    indexed: dict[str, list[dict]] = {}
    for prop in declarations:
        indexed.setdefault(prop["property"], []).append(prop)
    mapped = []
    for rec in recommendations:
        found, absent = [], []
        for candidate in dict.fromkeys(rec["possible_parameter_families"]):
            hit = indexed.get(candidate)
            if hit:
                found.append({
                    "candidate_family": candidate,
                    "match": "exact_declaration_name_only",
                    "declarations": hit,
                    "requires_human_review": True,
                })
            else:
                absent.append(candidate)
        mapped.append({
            "target": rec["target"],
            "suspected_category": rec["suspected_category"],
            "exact_name_matches": found,
            "unmatched_parameter_families": absent,
            "has_declared_name_match": bool(found),
            "validated_geometry_effect": False,
        })
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_property_mapping",
        "status": "review_only",
        "source_files_scanned": len(sources),
        "static_property_declarations_found": len(declarations),
        "recommendation_count": len(mapped),
        "recommendations": mapped,
        "unmapped_difference_codes": plan.get("unmapped_difference_codes", []),
        "next_action": "review_exact_declarations_and_actual_blender_registration",
        "limitations": [
            "Exact AST name matches do not prove property registration or geometry effect",
            "Unmatched families may be renamed, derived, dynamically registered or elsewhere",
            "No source snippets, default values or absolute paths are included",
        ],
        "safety": {
            "source_executed": False, "source_modified": False,
            "applies_parameters": False, "auto_approves": False,
            "auto_merges": False, "private_source_committed": False,
        },
    }


def _read_json(path: str | Path) -> dict:
    file = Path(path)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_PLAN_BYTES:
        raise PropertyMappingError("Missing, symlinked or oversized repair plan")
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PropertyMappingError("Duplicate repair plan key")
            result[key] = value
        return result
    try:
        return json.loads(file.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates,
                          parse_constant=lambda s: (_ for _ in ()).throw(
                              PropertyMappingError("Invalid nonfinite JSON constant")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PropertyMappingError("Invalid repair plan JSON") from exc


def write_local_mapping(result: dict, output: str | Path, *, root: Path = ROOT) -> Path:
    """Never write private property identifiers outside ignored reports/latest."""
    if not isinstance(result, dict) or result.get("kind") != "cbdk_glb_property_mapping":
        raise PropertyMappingError("Expected CBDK static property mapping report")
    relative = Path(output)
    if (relative.is_absolute() or relative.suffix != ".json"
            or relative.parts[:2] != REPORT_DIR.parts or len(relative.parts) < 3
            or ".." in relative.parts):
        raise PropertyMappingError("Output must be a .json under reports/latest/")
    root = root.resolve()
    target = root / relative
    if not target.resolve().is_relative_to(root / REPORT_DIR):
        raise PropertyMappingError("Output resolves outside ignored reports/latest/")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Mapping report already exists; choose a new filename")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    return target


def map_properties_from_file(plan_path: str | Path, sources: list[str | Path],
                             output: str | Path = "reports/latest/glb_property_mapping.json",
                             *, root: Path = ROOT) -> dict:
    report = map_repair_plan_properties(_read_json(plan_path), sources)
    write_local_mapping(report, output, root=root)
    return report
