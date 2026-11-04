"""Conservative AST-based extraction of dependency-light top-level functions.

Never imports or runs inspected source files. Output is a *review candidate*, not
an approved/verified component. Only small, pure-expression shapes are eligible.
"""
from __future__ import annotations

import ast
import hashlib
import json
import symtable
from pathlib import Path

ALLOWED_BUILTINS = frozenset({
    'abs', 'all', 'any', 'bool', 'divmod', 'enumerate', 'filter', 'float',
    'int', 'len', 'list', 'map', 'max', 'min', 'pow', 'range', 'reversed',
    'round', 'set', 'sorted', 'str', 'sum', 'tuple', 'zip',
})
ALLOWED_MATH = frozenset({
    'acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'degrees', 'e',
    'exp', 'fabs', 'floor', 'fmod', 'hypot', 'isfinite', 'log',
    'pi', 'radians', 'sin', 'sqrt', 'tan', 'tau',
})
DISALLOWED_NODES = (
    ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom, ast.Lambda,
    ast.Global, ast.Nonlocal, ast.Import, ast.ImportFrom, ast.With,
    ast.AsyncWith, ast.Try, ast.Raise, ast.Delete, ast.While, ast.NamedExpr,
    ast.ClassDef, ast.FunctionDef, ast.Assert,
)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _globals_in(node: ast.FunctionDef) -> set[str]:
    table = symtable.symtable(ast.unparse(node), '<candidate>', 'exec')
    result: set[str] = set()

    def gather(scope):
        for symbol in scope.get_symbols():
            if symbol.is_global() and symbol.is_referenced():
                result.add(symbol.get_name())
        for child in scope.get_children():
            gather(child)

    gather(table.get_children()[0])
    return result


def _find_candidate(catalog: dict, candidate_id: str, source: Path):
    symbols = [s for s in catalog.get('symbols', []) if s.get('id') == candidate_id]
    if len(symbols) != 1:
        raise ValueError('Candidate ID missing or ambiguous in the catalog')
    symbol = symbols[0]
    if symbol.get('kind') != 'function' or '.' in symbol.get('qualname', ''):
        raise ValueError('Only top-level functions can be inspected for isolated extraction')
    records = [f for f in catalog.get('files', []) if f.get('path') == symbol['source']]
    if len(records) != 1:
        raise ValueError('Source record missing or ambiguous')
    record = records[0]
    raw = source.read_bytes()
    if _digest(raw) != record.get('sha256') or source.name != symbol.get('source_name'):
        raise ValueError('Source hash/name mismatch: rescan before extracting')
    tree = ast.parse(raw.decode('utf-8-sig'), filename=str(source))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == symbol['qualname'] and n.lineno == symbol['line']]
    if len(functions) != 1:
        raise ValueError('Function definition moved or changed: rescan first')
    return symbol, record, functions[0]


def inspect_candidate(catalog: dict, candidate_id: str, source: str | Path) -> dict:
    """Report evidence for manual review; never invokes the inspected code."""
    path = Path(source)
    symbol, record, node = _find_candidate(catalog, candidate_id, path)
    reasons = []
    if node.decorator_list:
        reasons.append('Decorators may depend on context or execute at import time')
    if node.args.defaults or any(x is not None for x in node.args.kw_defaults):
        defaults = list(node.args.defaults) + [x for x in node.args.kw_defaults if x is not None]
        if any(not isinstance(x, ast.Constant) or not isinstance(x.value, (str, int, float, bool, type(None))) for x in defaults):
            reasons.append('Non-literal default argument')
    allowed_annotations = {'int', 'float', 'str', 'bool', 'None'}
    annotations = [a.annotation for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs if a.annotation]
    if node.args.vararg and node.args.vararg.annotation:
        annotations.append(node.args.vararg.annotation)
    if node.args.kwarg and node.args.kwarg.annotation:
        annotations.append(node.args.kwarg.annotation)
    if node.returns:
        annotations.append(node.returns)
    for a in annotations:
        if not isinstance(a, ast.Name) or a.id not in allowed_annotations:
            reasons.append('Complex annotation refers to external types')
            break

    arg_names = {a.arg for a in (node.args.posonlyargs + node.args.args + node.args.kwonlyargs)}
    if node.args.vararg:
        arg_names.add(node.args.vararg.arg)
    if node.args.kwarg:
        arg_names.add(node.args.kwarg.arg)
    if 'math' in arg_names or any(isinstance(n, ast.Name) and n.id == 'math' and isinstance(n.ctx, ast.Store)
                                  for n in ast.walk(node)):
        reasons.append('math module name shadowed by a local variable')
    dependencies = sorted(_globals_in(node) - ALLOWED_BUILTINS - {'math'})
    if dependencies:
        reasons.append('Unresolved globals: ' + ', '.join(dependencies))

    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, DISALLOWED_NODES):
            reasons.append('Unsupported AST node: ' + type(child).__name__)
        if isinstance(child, ast.Attribute):
            if not (isinstance(child.value, ast.Name) and child.value.id == 'math' and child.attr in ALLOWED_MATH):
                reasons.append('Attribute access requires manual review')
        if isinstance(child, ast.Call):
            target = child.func
            okay = (isinstance(target, ast.Name) and target.id in ALLOWED_BUILTINS) or (
                isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                and target.value.id == 'math' and target.attr in ALLOWED_MATH
            )
            if not okay:
                reasons.append('Call outside allowlist')
        if isinstance(child, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if not all(isinstance(t, ast.Name) for t in targets):
                reasons.append('Nonlocal/collection assignment may mutate external state')
        if isinstance(child, ast.For) and not isinstance(child.target, ast.Name):
            reasons.append('Complex loop target')
    reasons = sorted(set(reasons))
    globals_found = sorted(_globals_in(node))
    return {
        'schema_version': 1, 'candidate_id': candidate_id,
        'qualname': symbol['qualname'], 'source_name': path.name,
        'source_sha256': record['sha256'], 'line': node.lineno,
        'global_references': globals_found, 'uses_math': 'math' in globals_found,
        'eligible_for_review_extraction': not reasons, 'blockers': reasons,
        'verification': 'static_only', 'approved': False,
        'warning': 'No execution, semantic equivalence check, license approval, or Blender validation has occurred.',
    }


def extract_candidate(catalog: dict, candidate_id: str, source: str | Path,
                      output: str | Path) -> dict:
    """Write one AST-unparsed function and provenance manifest; refuse overwrite."""
    report = inspect_candidate(catalog, candidate_id, source)
    if not report['eligible_for_review_extraction']:
        raise ValueError('; '.join(report['blockers']))
    path = Path(source)
    _, _, node = _find_candidate(catalog, candidate_id, path)
    target = Path(output)
    manifest = target.with_suffix('.json')
    if target.suffix != '.py' or target.resolve() == path.resolve():
        raise ValueError('Output must be a new .py file, distinct from source')
    if target.exists() or manifest.exists():
        raise FileExistsError('Output or provenance manifest already exists; refusing overwrite')
    generated = ('"""CBDK review candidate: NOT validated or approved.\n'
                 'Original implementation must be rights-reviewed before redistribution.\n"""\n'
                 + ('import math\n\n' if report['uses_math'] else '\n')
                 + ast.unparse(node) + '\n')
    ast.parse(generated)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as handle:
        handle.write(generated)
    try:
        with manifest.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write('\n')
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return report
