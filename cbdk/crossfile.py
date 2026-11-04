"""Conservative multi-file AST dependency graph and review-only extraction.

Only explicit relative ``from .module import helper`` imports are followed. No
module is imported or executed. No generated code is approved automatically.
This is not a sandbox, an equivalence proof, or a license clearance tool.
"""
from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

from .bundle import (
    ALLOWED_BUILTINS, MAX_AST_NODES, MAX_DEPTH, MAX_FUNCTIONS,
    _function_globals, _index_constants, _module_bindings, _parse_source,
    _validate_function,
)

MAX_FILES = 12


def _under(child: Path, directory: Path) -> bool:
    return child == directory or directory in child.parents


def _catalog_sources(catalog: dict) -> dict[Path, dict]:
    result: dict[Path, dict] = {}
    for item in catalog.get('files', []):
        path = Path(item['path']).resolve()
        if path in result:
            raise ValueError(f'Duplicate catalog entry for path {path}')
        result[path] = item
    return result


def _source_imports(tree: ast.Module, path: Path, sources_root: Path) -> dict[str, Path]:
    """Return explicit relative imports only, retaining unresolved as blockers later."""
    result = {}
    for stmt in tree.body:
        if not isinstance(stmt, ast.ImportFrom) or stmt.level < 1 or not stmt.module:
            continue
        directory = path.parent
        for _ in range(stmt.level - 1):
            directory = directory.parent
        if stmt.module:
            directory = directory.joinpath(*stmt.module.split('.'))
        target = directory.with_suffix('.py').resolve()
        # An explicit source file is required; package __init__ execution is not inferred.
        for item in stmt.names:
            if item.name == '*' or item.asname is not None:
                continue
            if not _under(target, sources_root):
                continue
            result[item.name] = target
    return result


def _find_root(catalog: dict, candidate_id: str, path: Path, file_records: dict[Path, dict]) -> str:
    syms = [s for s in catalog.get('symbols', []) if s.get('id') == candidate_id]
    if len(syms) != 1:
        raise ValueError('Missing or ambiguous root candidate ID')
    symbol = syms[0]
    if symbol.get('kind') != 'function' or '.' in symbol.get('qualname', ''):
        raise ValueError('Root must be a top-level synchronous function')
    record = file_records.get(path)
    if record is None or record['path'] != symbol.get('source'):
        raise ValueError('Root source path does not match the catalog entry')
    if path.name != symbol.get('source_name'):
        raise ValueError('Root source name does not match catalog')
    if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Root source has changed; rescan first')
    return symbol['qualname']


def inspect_crossfile(catalog: dict, candidate_id: str, source: str | Path,
                      *, sources_root: str | Path, max_functions: int = MAX_FUNCTIONS,
                      max_files: int = MAX_FILES) -> dict:
    """Build a cross-file pure function DAG, rejecting non-relative external refs."""
    if not 1 <= max_functions <= MAX_FUNCTIONS:
        raise ValueError(f'max_functions must be 1..{MAX_FUNCTIONS}')
    if not 1 <= max_files <= MAX_FILES:
        raise ValueError(f'max_files must be 1..{MAX_FILES}')
    path = Path(source).resolve()
    root_dir = Path(sources_root).resolve()
    if not root_dir.is_dir() or not _under(path, root_dir):
        raise ValueError('Source must reside below existing sources root')
    records = _catalog_sources(catalog)
    root_name = _find_root(catalog, candidate_id, path, records)
    file_data: dict[Path, tuple] = {}
    blockers: list[str] = []
    visiting: list[tuple[Path, str]] = []
    visited: set[tuple[Path, str]] = set()
    ordered: list[tuple[Path, str]] = []
    edges: list[dict] = []
    chosen_constants: dict[str, tuple[Path, object]] = {}
    chosen_functions: dict[str, Path] = {}
    uses_math = False

    def load(current: Path):
        if current in file_data:
            return file_data[current]
        if len(file_data) >= max_files:
            raise ValueError('Cross-file source count limit exceeded')
        if not _under(current, root_dir):
            raise ValueError('Imported source escapes allowed root')
        record = records.get(current)
        if record is None:
            raise ValueError('Imported module was not in the scanned catalog')
        raw = current.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record.get('sha256'):
            raise ValueError('Imported source changed; rescan before extracting')
        tree, bindings, functions, counts, constants = _parse_source(str(current), record['sha256'])
        imports = _source_imports(tree, current, root_dir)
        payload = tree, bindings, functions, counts, constants, imports, record
        file_data[current] = payload
        return payload

    def visit(current: Path, name: str, depth: int) -> None:
        nonlocal uses_math
        key = current, name
        if key in visiting:
            blockers.append('Dependency cycle: ' + ' -> '.join(f'{x.name}:{n}' for x, n in [*visiting, key]))
            return
        if key in visited:
            return
        if depth > MAX_DEPTH or len(visiting) + len(visited) >= max_functions:
            blockers.append('Dependency depth/count limit reached')
            return
        try:
            _, bindings, functions, counts, constants, imports, record = load(current)
        except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
            blockers.append(f'{current.name}: {exc}')
            return
        if name not in functions or counts[name] != 1 or bindings.get(name) != ['FunctionDef']:
            blockers.append(f'{current.name}: ambiguous or missing helper {name}')
            return
        if name in ALLOWED_BUILTINS or name == 'math':
            blockers.append(f'{current.name}: helper name shadows a reserved name: {name}')
            return
        other = chosen_functions.get(name)
        if other is not None and other != current:
            blockers.append(f'Flattened helper name collision: {name} in {other.name} and {current.name}')
            return
        if name in chosen_constants:
            blockers.append(f'Name collision between constant and helper: {name}')
            return
        chosen_functions[name] = current
        visiting.append(key)
        node = functions[name]
        if sum(1 for _ in ast.walk(node)) > MAX_AST_NODES:
            blockers.append(f'{current.name}:{name}: function exceeds AST size cap')
            visiting.pop()
            visited.add(key)
            ordered.append(key)
            return
        globals_found = set(_function_globals(record['sha256'], name, node))
        valid_func_names = set(functions) | {n for n in imports if bindings.get(n) == ['ImportFrom']}
        blockers.extend(f'{current.name}:{name}: {reason}' for reason in
                        _validate_function(node, globals_found, valid_func_names, bindings))
        for ref in sorted(globals_found):
            if ref in functions:
                edges.append({'from': f'{current.name}:{name}', 'to': f'{current.name}:{ref}'})
                visit(current, ref, depth + 1)
            elif ref in imports and bindings.get(ref) == ['ImportFrom']:
                target = imports[ref]
                if not _under(target, root_dir):
                    blockers.append(f'{name}: import escapes source root')
                else:
                    edges.append({'from': f'{current.name}:{name}', 'to': f'{target.name}:{ref}'})
                    visit(target, ref, depth + 1)
            elif ref == 'math':
                if bindings.get('math') == ['Import:math']:
                    uses_math = True
                else:
                    blockers.append(f'{current.name}:{name}: math import missing or shadowed')
            elif ref in constants:
                if ref in ALLOWED_BUILTINS:
                    blockers.append(f'{current.name}:{name}: builtin {ref} shadowed by constant')
                elif ref in chosen_functions:
                    blockers.append(f'{current.name}:{name}: constant {ref} collides with function')
                elif ref in chosen_constants and chosen_constants[ref][0] != current:
                    blockers.append(f'Constant name collision: {ref} in multiple modules')
                else:
                    chosen_constants[ref] = (current, constants[ref][1])
            elif ref in ALLOWED_BUILTINS:
                if ref in bindings:
                    blockers.append(f'{current.name}:{name}: builtin {ref} shadowed')
            else:
                blockers.append(f'{current.name}:{name}: unresolved or disallowed global {ref}')
        visiting.pop()
        visited.add(key)
        ordered.append(key)

    visit(path, root_name, 0)
    if set(chosen_functions) & set(chosen_constants):
        blockers.append('Function/constant name collision in flattened bundle')
    all_names = set(chosen_functions) | set(chosen_constants)
    if 'math' in all_names:
        blockers.append('math name collision in flattened bundle')
    symbols = {(Path(s['source']).resolve(), s['qualname']): s for s in catalog.get('symbols', [])
               if s.get('kind') == 'function'}
    manifest = {
        'schema_version': 1, 'root_candidate_id': candidate_id,
        'sources_root': str(root_dir), 'root': {'file': str(path.relative_to(root_dir)), 'name': root_name},
        'files': [{'path': str(p.relative_to(root_dir)), 'sha256': file_data[p][-1]['sha256']}
                  for p in sorted(file_data)],
        'functions': [{'file': str(p.relative_to(root_dir)), 'name': name,
                       'candidate_id': symbols.get((p, name), {}).get('id'),
                       'line': file_data[p][2][name].lineno} for p, name in ordered],
        'dependencies': edges,
        'constants': [{'file': str(p.relative_to(root_dir)), 'name': name, 'value': value}
                      for name, (p, value) in sorted(chosen_constants.items())],
        'uses_math': uses_math,
        'eligible_for_review_extraction': not blockers,
        'blockers': sorted(set(blockers)), 'verification': 'static_only', 'approved': False,
        'warning': 'Review candidate only; no source imported/executed, behavior proven, Blender tested, or license cleared.',
    }
    return manifest


def extract_crossfile(catalog: dict, candidate_id: str, source: str | Path,
                      output: str | Path, *, sources_root: str | Path,
                      max_functions: int = MAX_FUNCTIONS, max_files: int = MAX_FILES) -> dict:
    """Flatten trusted-shape DAG to new .py + JSON. Refuses all overwrites."""
    manifest = inspect_crossfile(catalog, candidate_id, source, sources_root=sources_root,
                                 max_functions=max_functions, max_files=max_files)
    if not manifest['eligible_for_review_extraction']:
        raise ValueError('Cross-file extraction blocked: ' + '; '.join(manifest['blockers']))
    directory = Path(sources_root).resolve()
    target = Path(output).resolve()
    meta = target.with_suffix('.json')
    protected = {directory.joinpath(entry['path']).resolve() for entry in manifest['files']}
    if target.suffix != '.py' or target in protected or target == Path(source).resolve():
        raise ValueError('Output must be a new .py file, separate from any source')
    if target.exists() or meta.exists():
        raise FileExistsError('Output or manifest already exists; refusing overwrite')
    # Recheck every source just before generating output.
    records = _catalog_sources(catalog)
    for file in manifest['files']:
        source_file = (directory / file['path']).resolve()
        if hashlib.sha256(source_file.read_bytes()).hexdigest() != file['sha256']:
            raise ValueError('Source changed since inspection; abort extraction')
        if records[source_file]['sha256'] != file['sha256']:
            raise ValueError('Catalog differs from source in manifest')
    sections = ['"""CBDK v0.5 UNAPPROVED cross-file review candidate; rights/runtime tests required."""', '']
    if manifest['uses_math']:
        sections += ['import math', '']
    for constant in manifest['constants']:
        p = (directory / constant['file']).resolve()
        _, _, _, _, constants = _parse_source(str(p), records[p]['sha256'])
        sections.extend([ast.unparse(constants[constant['name']][0]), ''])
    for item in manifest['functions']:
        p = (directory / item['file']).resolve()
        _, _, functions, _, _ = _parse_source(str(p), records[p]['sha256'])
        sections.extend([ast.unparse(functions[item['name']]), ''])
    generated = '\n'.join(sections).rstrip() + '\n'
    ast.parse(generated)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as out:
        out.write(generated)
    try:
        with meta.open('x', encoding='utf-8') as out:
            json.dump(manifest, out, ensure_ascii=False, indent=2)
            out.write('\n')
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return manifest
