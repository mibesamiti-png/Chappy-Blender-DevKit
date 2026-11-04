"""Human-review contracts inferred from Blender API audit evidence.

These are diagnostic metadata only, never code execution or semantic validation.
"""
from __future__ import annotations

import json
from pathlib import Path


def make_blender_contracts(audit: dict) -> dict:
    """Convert v0.5 audit evidence into explicit, review-only test requirements."""
    if audit.get('schema_version') != 1 or not isinstance(audit.get('symbols'), list):
        raise ValueError('Expected a v0.5 Blender audit JSON object')
    contracts = []
    for symbol in audit['symbols']:
        paths = tuple(symbol.get('api_paths') or [])
        calls = tuple(symbol.get('api_calls') or [])
        references = tuple(symbol.get('context_references') or [])
        operators = tuple(symbol.get('operator_calls') or [])
        edit_mesh = any(s.startswith(('bmesh.from_edit_mesh', 'bmesh.update_edit_mesh'))
                        for s in (*paths, *calls))
        uses_ops = bool(operators)
        direct_context = bool(references) or any(p.startswith('bpy.context') for p in paths)
        risks = []
        if edit_mesh:
            risks.append('Edit Mesh API: requires an appropriate edit mesh and valid Blender context')
        if uses_ops:
            risks.append('bpy.ops: operator poll/context/mode requirements must be checked in Blender')
        if direct_context:
            risks.append('Context-sensitive access: requires explicit scene/selection/mode fixtures')
        if any(x.startswith('mathutils') for x in (*paths, *calls)):
            risks.append('mathutils: Blender version/runtime availability must be checked')
        # Mode is *not* inferred for arbitrary bpy.ops: API names alone are insufficient.
        mode_hints = ['EDIT_MESH'] if edit_mesh else []
        tests = ['import_or_registration_in_supported_blender', 'normal_input',
                 'missing_or_invalid_context', 'source_preservation', 'undo_or_cleanup_if_mutating']
        if edit_mesh:
            tests.extend(['edit_mode_active_mesh', 'multi_object_edit_mode'])
        if uses_ops:
            tests.extend(['operator_poll', 'context_override_if_required'])
        contracts.append({
            'candidate_id': symbol['candidate_id'], 'source_name': symbol['file'],
            'qualname': symbol['function'], 'kind': symbol['kind'], 'line': symbol['line'],
            'api_paths': list(paths), 'api_calls': list(calls),
            'context_references': list(references),
            'mode_hints_not_guarantees': mode_hints,
            'requires_operator_poll': uses_ops,
            'requires_runtime_verification': True,
            'risks': risks or ['Blender API usage: manual review required'],
            'suggested_tests': tests,
            'status': 'review_required', 'verification': 'static_only',
            'approved': False,
        })
    return {
        'schema_version': 1, 'contracts_count': len(contracts),
        'edit_mesh_candidates': sum(bool(x['mode_hints_not_guarantees']) for x in contracts),
        'operator_candidates': sum(x['requires_operator_poll'] for x in contracts),
        'contracts': contracts, 'verification': 'static_only', 'approved': False,
        'warning': 'Contracts are inferred from syntax only; mode hints are not validated preconditions.',
    }


def write_contracts(path: str | Path, report: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
