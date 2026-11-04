"""Read-only static inventory of Blender API usage in scanned Python sources.

Records bpy, bmesh, mathutils and context-sensitive patterns. This is an
inspection tool, not Blender-runtime verification or safe automatic extraction.
"""
from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from pathlib import Path

BLENDER_MODULES = ('bpy', 'bmesh', 'mathutils')


def _attr_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        root = _attr_name(node.value)
        return f'{root}.{node.attr}' if root else None
    return None


def _aliases(nodes: list[ast.stmt]) -> tuple[dict[str, str], set[str]]:
    """Collect unambiguous top-level aliases; flag module binding collisions."""
    from .bundle import _module_bindings
    tree = ast.Module(body=nodes, type_ignores=[])
    bindings = _module_bindings(tree)
    aliases: dict[str, str] = {}
    ambiguous: set[str] = set()
    for item in nodes:
        if isinstance(item, ast.Import):
            for a in item.names:
                root = a.name.split('.')[0]
                alias = a.asname or root
                canonical = a.name if a.asname else root
                if canonical.split('.')[0] in BLENDER_MODULES:
                    aliases[alias] = canonical
        elif isinstance(item, ast.ImportFrom) and item.module:
            if item.module.split('.')[0] in BLENDER_MODULES and item.level == 0:
                for a in item.names:
                    if a.name == '*':
                        ambiguous.add('*')
                    else:
                        aliases[a.asname or a.name] = item.module + '.' + a.name
    for alias in list(aliases):
        if len(bindings.get(alias, [])) != 1:
            ambiguous.add(alias)
            aliases.pop(alias)
    return aliases, ambiguous


def _symbol_usage(node: ast.AST, aliases: dict[str, str], ambiguous: set[str]) -> dict:
    paths: set[str] = set()
    calls: set[str] = set()
    context_paths: set[str] = set()
    runtime_imports: set[str] = set()
    for descendant in ast.walk(node):
        if isinstance(descendant, (ast.Import, ast.ImportFrom)):
            runtime_imports.add(ast.unparse(descendant))
        if isinstance(descendant, ast.Attribute):
            path = _attr_name(descendant)
            if path:
                root, _, rest = path.partition('.')
                if root in aliases:
                    canonical = aliases[root] + ('.' + rest if rest else '')
                    if canonical.startswith(BLENDER_MODULES):
                        paths.add(canonical)
                elif root == 'context':
                    context_paths.add(path)
        elif isinstance(descendant, ast.Name) and descendant.id in aliases:
            paths.add(aliases[descendant.id])
        if isinstance(descendant, ast.Call):
            call = _attr_name(descendant.func)
            if call:
                root, _, rest = call.partition('.')
                if root in aliases:
                    canonical = aliases[root] + ('.' + rest if rest else '')
                    if canonical.startswith(BLENDER_MODULES):
                        calls.add(canonical)
                elif root == 'context':
                    context_paths.add(call)
    operator_calls = sorted(x for x in calls if x.startswith('bpy.ops.'))
    bmesh_ops = sorted(x for x in calls if x.startswith('bmesh.'))
    context_api = sorted(x for x in paths if x.startswith('bpy.context.') or x == 'bpy.context')
    context_sensitive = bool(operator_calls or context_api or context_paths or
                             any(x.startswith('bmesh.from_edit_mesh') or x.startswith('bmesh.update_edit_mesh') for x in bmesh_ops))
    api_used = bool(paths or calls)
    warnings = []
    if ambiguous:
        warnings.append('Ambiguous/rebound Blender module aliases: ' + ', '.join(sorted(ambiguous)))
    if runtime_imports:
        warnings.append('Imports appear inside the symbol; review import side effects')
    if operator_calls:
        warnings.append('bpy.ops calls require Blender context/mode validation')
    if context_sensitive and not operator_calls:
        warnings.append('Blender context/edit mesh access requires runtime validation')
    return {'api_paths': sorted(paths), 'api_calls': sorted(calls), 'operator_calls': operator_calls,
            'bmesh_calls': bmesh_ops, 'context_references': sorted(context_paths | set(context_api)),
            'context_sensitive': context_sensitive, 'uses_blender_api': api_used,
            'requires_blender_runtime_validation': api_used or bool(context_paths),
            'static_warnings': warnings}


def audit_blender_dependencies(catalog: dict, *, max_paths: int = 80) -> dict:
    if not 1 <= max_paths <= 1000:
        raise ValueError('max_paths must be 1..1000')
    by_source = defaultdict(list)
    for symbol in catalog.get('symbols', []):
        by_source[symbol['source']].append(symbol)
    files = []
    uses = []
    for record in catalog.get('files', []):
        if record.get('status') != 'parsed':
            files.append({'source': record['path'], 'status': 'skipped_parse_error'})
            continue
        path = Path(record['path']).resolve()
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError(f'File changed since catalog generation: {record["name"]}')
        tree = ast.parse(raw.decode('utf-8-sig'), filename=str(path))
        aliases, ambiguous = _aliases(tree.body)
        # Use scanner-like symbol identity by line + qualified name.
        by_key = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                by_key[(node.name, node.lineno)] = node
            elif isinstance(node, ast.ClassDef):
                by_key[(node.name, node.lineno)] = node
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        by_key[(f'{node.name}.{child.name}', child.lineno)] = child
        file_total = 0
        file_context = 0
        for sym in by_source.get(record['path'], []):
            node = by_key.get((sym['qualname'], sym['line']))
            if node is None:
                continue
            # Class bodies contain method ASTs. Audit methods separately to avoid
            # counting one bpy call twice (once as class, once as method).
            if isinstance(node, ast.ClassDef):
                node = ast.ClassDef(name=node.name, bases=node.bases, keywords=node.keywords,
                                    body=[x for x in node.body if not isinstance(
                                        x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))],
                                    decorator_list=node.decorator_list)
            usage = _symbol_usage(node, aliases, ambiguous)
            if not usage['uses_blender_api'] and not usage['context_sensitive']:
                continue
            file_total += 1
            file_context += int(usage['context_sensitive'])
            uses.append({'candidate_id': sym['id'], 'file': record['name'],
                         'function': sym['qualname'], 'kind': sym['kind'],
                         'line': sym['line'], **usage})
        files.append({'source': record['path'], 'name': record['name'], 'status': 'audited',
                      'bl_info_version': record.get('bl_info', {}).get('blender'),
                      'blender_symbols': file_total, 'context_sensitive_symbols': file_context,
                      'module_aliases': aliases, 'ambiguous_module_aliases': sorted(ambiguous)})
    uses.sort(key=lambda entry: (entry['file'], entry['line'], entry['function']))
    return {'schema_version': 1, 'scanned_files': len(files),
            'blender_related_symbols': len(uses),
            'context_sensitive_symbols': sum(int(x['context_sensitive']) for x in uses),
            'files': files, 'symbols': uses,
            'verification': 'static_only', 'approved': False,
            'warning': 'Report describes syntactic API references only. Calls through aliases, parameters, or dynamic dispatch may be missed; Blender execution is not performed.'}
