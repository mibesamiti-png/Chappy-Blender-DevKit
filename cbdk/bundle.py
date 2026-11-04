"""Conservative same-file AST dependency bundling; never execute inspected code."""
from __future__ import annotations

import ast
import hashlib
import json
import math
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from .isolation import ALLOWED_BUILTINS, ALLOWED_MATH, DISALLOWED_NODES, _globals_in

MAX_FUNCTIONS = 64
MAX_DEPTH = 24
MAX_AST_NODES = 5000


def _module_bindings(tree: ast.Module) -> dict[str, list[str]]:
    bindings: dict[str, list[str]] = defaultdict(list)

    def visit_stmt(node: ast.stmt) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings[node.name].append(type(node).__name__)
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                bindings[alias.asname or alias.name.split('.')[0]].append('Import:' + alias.name)
            return
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bindings[alias.asname or alias.name].append('ImportFrom')
            return
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        bindings[sub.id].append('Assignment')
            return
        if isinstance(node, ast.Expr):
            for sub in ast.walk(node):
                if isinstance(sub, ast.NamedExpr):
                    for name in ast.walk(sub.target):
                        if isinstance(name, ast.Name) and isinstance(name.ctx, ast.Store):
                            bindings[name.id].append('NamedExpr')
        if isinstance(node, (ast.For, ast.AsyncFor)):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    bindings[sub.id].append('LoopBinding')
        for field in ('body', 'orelse', 'finalbody'):
            for child in getattr(node, field, []):
                if isinstance(child, ast.stmt):
                    visit_stmt(child)
        for handler in getattr(node, 'handlers', []):
            if isinstance(handler, ast.ExceptHandler):
                if handler.name:
                    bindings[handler.name].append('ExceptBinding')
                for child in handler.body:
                    visit_stmt(child)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars:
                    for sub in ast.walk(item.optional_vars):
                        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                            bindings[sub.id].append('WithBinding')

    for stmt in tree.body:
        visit_stmt(stmt)
    return dict(bindings)


def _immutable_literal(node: ast.AST):
    try:
        value = ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None, False
    if type(value) in (type(None), bool, int, float, str):
        if type(value) is float and not math.isfinite(value):
            return None, False
        if type(value) is str and len(value) > 512:
            return None, False
        if type(value) is int and value.bit_length() > 256:
            return None, False
        return value, True
    return None, False


def _index_constants(tree: ast.Module, bindings: dict[str, list[str]]) -> dict[str, tuple[ast.Assign, object]]:
    constants = {}
    for node in tree.body:
        target = None
        # Never copy annotated assignments; their annotation can execute code.
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
        if target is None or len(bindings.get(target, [])) != 1:
            continue
        value, is_literal = _immutable_literal(node.value)
        if is_literal:
            constants[target] = (node, value)
    return constants


def _validate_function(node: ast.FunctionDef, globals_found: set[str], function_names: set[str],
                       bindings: dict[str, list[str]]) -> list[str]:
    blockers = []
    if node.decorator_list:
        blockers.append('Decorated function: decorator runs when function is defined')
    for default in [*node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)]:
        _, good = _immutable_literal(default)
        if not good:
            blockers.append('Dynamic or mutable default argument')
    annotations = [a.annotation for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs if a.annotation]
    if node.args.vararg and node.args.vararg.annotation:
        annotations.append(node.args.vararg.annotation)
    if node.args.kwarg and node.args.kwarg.annotation:
        annotations.append(node.args.kwarg.annotation)
    if node.returns:
        annotations.append(node.returns)
    for anno in annotations:
        if not (isinstance(anno, ast.Name) and anno.id in {'int', 'str', 'bool', 'float'}) and not (
            isinstance(anno, ast.Constant) and anno.value is None
        ):
            blockers.append('Annotation requiring runtime evaluation')
            break
        if isinstance(anno, ast.Name) and anno.id in bindings:
            blockers.append('Annotation type is shadowed in original module')
    args = {a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
    if node.args.vararg:
        args.add(node.args.vararg.arg)
    if node.args.kwarg:
        args.add(node.args.kwarg.arg)
    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, DISALLOWED_NODES) or isinstance(child, (ast.AsyncFor, ast.AsyncWith, ast.Match)):
            blockers.append('Unsupported syntax: ' + type(child).__name__)
        if isinstance(child, ast.Attribute):
            if not (isinstance(child.value, ast.Name) and child.value.id == 'math' and child.attr in ALLOWED_MATH):
                blockers.append('Object attribute access requires manual review')
        if isinstance(child, ast.Call):
            target = child.func
            if isinstance(target, ast.Name):
                valid = target.id in globals_found and (target.id in ALLOWED_BUILTINS or target.id in function_names)
            else:
                valid = (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                         and target.value.id == 'math' and target.attr in ALLOWED_MATH
                         and 'math' in globals_found)
            if not valid:
                blockers.append('Call to dynamic or disallowed callable')
        if isinstance(child, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if not all(isinstance(target, ast.Name) for target in targets):
                blockers.append('Mutation through attribute, subscript or destructuring')
        if isinstance(child, (ast.For, ast.AsyncFor)) and not isinstance(child.target, ast.Name):
            blockers.append('Complex loop assignment')
        if isinstance(child, ast.Name) and child.id == 'math' and isinstance(child.ctx, ast.Store):
            blockers.append('Local math binding shadows imported module')
    if 'math' in args:
        blockers.append('math parameter shadows module')
    if sum(1 for _ in ast.walk(node)) > MAX_AST_NODES:
        blockers.append('Function exceeds AST size cap')
    return sorted(set(blockers))


@lru_cache(maxsize=16)
def _parse_source(path_string: str, expected_sha: str):
    source = Path(path_string)
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('Source hash mismatch: rescan before extracting')
    tree = ast.parse(raw.decode('utf-8-sig'), filename=str(source))
    bindings = _module_bindings(tree)
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    counts = Counter(n.name for n in defs)
    functions = {n.name: n for n in defs if counts[n.name] == 1}
    constants = _index_constants(tree, bindings)
    return tree, bindings, functions, counts, constants


@lru_cache(maxsize=2048)
def _function_globals(source_sha: str, name: str, node: ast.FunctionDef) -> frozenset[str]:
    if sum(1 for _ in ast.walk(node)) > MAX_AST_NODES:
        return frozenset()
    return frozenset(_globals_in(node))


def _resolve_catalog_candidate(catalog: dict, candidate_id: str, path: Path):
    matches = [s for s in catalog.get('symbols', []) if s.get('id') == candidate_id]
    if len(matches) != 1:
        raise ValueError('Candidate ID missing or ambiguous in catalog')
    symbol = matches[0]
    if symbol.get('kind') != 'function' or '.' in symbol.get('qualname', ''):
        raise ValueError('Only top-level functions can be bundled')
    records = [f for f in catalog.get('files', []) if f.get('path') == symbol.get('source')]
    if len(records) != 1:
        raise ValueError('Source record missing or ambiguous in catalog')
    record = records[0]
    if path.name != symbol.get('source_name') or hashlib.sha256(path.read_bytes()).hexdigest() != record.get('sha256'):
        raise ValueError('Source hash/name mismatch: rescan before extracting')
    return symbol, record


def inspect_bundle(catalog: dict, candidate_id: str, source: str | Path,
                   *, max_functions: int = MAX_FUNCTIONS) -> dict:
    """Analyze dependency DAG; never load or execute inspected source."""
    if not 1 <= max_functions <= MAX_FUNCTIONS:
        raise ValueError(f'max_functions must be 1..{MAX_FUNCTIONS}')
    path = Path(source)
    root_symbol, record = _resolve_catalog_candidate(catalog, candidate_id, path)
    tree, bindings, functions, counts, constants = _parse_source(str(path.resolve()), record['sha256'])
    root = root_symbol['qualname']
    if counts[root] != 1:
        raise ValueError('Duplicate top-level function name: root is ambiguous')
    if functions[root].lineno != root_symbol['line']:
        raise ValueError('Function moved or changed: rescan')
    if root not in functions:
        raise ValueError('Root is not a unique top-level function')
    symbols = {s['qualname']: s for s in catalog['symbols']
               if s.get('kind') == 'function' and s.get('source') == root_symbol['source']}

    visiting: list[str] = []
    visited: set[str] = set()
    ordered: list[str] = []
    edges: list[dict] = []
    needed_constants: set[str] = set()
    needs_math = False
    blockers: list[str] = []

    def visit(name: str, depth: int) -> None:
        nonlocal needs_math
        if name in visiting:
            blockers.append('Cyclic dependency: ' + ' -> '.join([*visiting, name]))
            return
        if name in visited:
            return
        if depth > MAX_DEPTH or len(visited) + len(visiting) >= max_functions:
            blockers.append('Function/dependency limit reached')
            return
        if name not in functions:
            blockers.append('Missing or overwritten top-level helper: ' + name)
            return
        if bindings.get(name) != ['FunctionDef']:
            blockers.append('Ambiguous/shadowed function binding: ' + name)
            return
        visiting.append(name)
        node = functions[name]
        if sum(1 for _ in ast.walk(node)) > MAX_AST_NODES:
            blockers.append(f'{name}: function exceeds AST size cap')
            visiting.pop()
            visited.add(name)
            ordered.append(name)
            return
        global_refs = set(_function_globals(record['sha256'], name, node))
        blockers.extend(f'{name}: {b}' for b in _validate_function(node, global_refs, set(functions), bindings))
        for reference in sorted(global_refs):
            if reference in functions:
                edges.append({'from': name, 'to': reference})
                visit(reference, depth + 1)
            elif reference == 'math':
                if bindings.get('math') == ['Import:math']:
                    needs_math = True
                else:
                    blockers.append(f'{name}: math is not an unshadowed import math')
            elif reference in constants:
                if reference in ALLOWED_BUILTINS:
                    blockers.append(f'{name}: builtin {reference} shadowed by module constant')
                else:
                    needed_constants.add(reference)
            elif reference in ALLOWED_BUILTINS:
                if reference in bindings:
                    blockers.append(f'{name}: builtin {reference} shadowed in source')
            else:
                blockers.append(f'{name}: unresolved global {reference}')
        visiting.pop()
        visited.add(name)
        ordered.append(name)

    visit(root, 0)
    return {
        'schema_version': 1, 'root_candidate_id': candidate_id, 'root_function': root,
        'source_name': path.name, 'source_sha256': record['sha256'],
        'functions': [{'name': name, 'candidate_id': symbols[name]['id'],
                       'line': functions[name].lineno} for name in ordered if name in symbols],
        'dependencies': edges,
        'constants': [{'name': name, 'value': constants[name][1]} for name in sorted(needed_constants)],
        'uses_math': needs_math,
        'eligible_for_review_extraction': not blockers,
        'blockers': sorted(set(blockers)),
        'verification': 'static_only', 'approved': False,
        'warning': 'AST inspection does not prove safety, behavioral equivalence, Blender compatibility, or rights to distribute.',
    }


def extract_bundle(catalog: dict, candidate_id: str, source: str | Path, output: str | Path,
                   *, max_functions: int = MAX_FUNCTIONS) -> dict:
    """Write a review-only bundle and provenance JSON, refusing to overwrite."""
    manifest = inspect_bundle(catalog, candidate_id, source, max_functions=max_functions)
    if not manifest['eligible_for_review_extraction']:
        raise ValueError('Bundle blocked: ' + '; '.join(manifest['blockers']))
    source_path = Path(source)
    target = Path(output)
    provenance = target.with_suffix('.json')
    if target.suffix != '.py' or target.resolve() == source_path.resolve():
        raise ValueError('Output must be a new .py file, different from source')
    if target.exists() or provenance.exists():
        raise FileExistsError('Output or manifest exists; refusing to overwrite')
    tree, bindings, defs, _, constants = _parse_source(str(source_path.resolve()), manifest['source_sha256'])
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != manifest['source_sha256']:
        raise ValueError('Source hash mismatch after inspection: refusing extraction')
    sections = ['"""CBDK v0.4 review-only function bundle. NOT approved for redistribution."""', '']
    if manifest['uses_math']:
        sections += ['import math', '']
    for entry in manifest['constants']:
        sections += [ast.unparse(constants[entry['name']][0]), '']
    for entry in manifest['functions']:
        sections += [ast.unparse(defs[entry['name']]), '']
    generated = '
'.join(sections).rstrip() + '
'
    ast.parse(generated)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(generated)
    try:
        with provenance.open('x', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write('
')
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return manifest
