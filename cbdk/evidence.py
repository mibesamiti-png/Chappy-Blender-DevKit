"""Blender runtime smoke evidence for CBDK-authored parts.

This is a local execution record, not a cryptographic attestation, safety proof,
license clearance or automatic approval for reuse. Does not execute unknown code.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .blender_test import run_smoke
from .curation import _write_json_atomic

# Check IDs correspond to explicit assertions in the trusted Blender script.
PART_CASES: dict[str, tuple[str, tuple[str, ...]]] = {
    'BLCTX-001': ('parts/blender/context.py', ('active_mesh_object', 'wrong_mode_rejected')),
    'BLCTX-002': ('parts/blender/context.py', ('selection_excludes_non_mesh', 'selection_snapshot_tuple')),
    'BME-001': ('parts/blender/edit_mesh.py', ('object_mode_rejected', 'triangle_edit_selection')),
}
SCRIPT_PATH = 'scripts/blender_parts_smoke.py'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parts_payload(payload: object) -> dict:
    """Require every specified case before counting a suite as passing."""
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or payload.get('suite') != 'parts':
        raise ValueError('Unexpected parts-suite schema/version')
    if not isinstance(payload.get('blender'), str) or not payload['blender'].strip():
        raise ValueError('Blender version missing')
    checks = payload.get('part_checks')
    if not isinstance(checks, dict) or set(checks) != set(PART_CASES):
        raise ValueError('Parts suite must report exactly all expected part IDs')
    for part_id, (_, required) in PART_CASES.items():
        actual = checks[part_id]
        if not isinstance(actual, list) or len(actual) != len(set(actual)) or set(actual) != set(required):
            raise ValueError(f'Incomplete, duplicate or unexpected check for {part_id}')
        if any(not isinstance(x, str) for x in actual):
            raise ValueError(f'Invalid check labels for {part_id}')
    return payload


def verify_authored_parts(blender: str, *, timeout: int = 90, root: Path | None = None) -> dict:
    """Run trusted local suite and return provenance-bound per-part evidence.

    Failure reports contain no verified parts. No user-supplied success marker is
    accepted separately; only the trusted subprocess' output is inspected.
    """
    project = (root or Path(__file__).resolve().parent.parent).resolve()
    script = project / SCRIPT_PATH
    sources = sorted({path for path, _ in PART_CASES.values()})
    manifest = {}
    for relative_path in [SCRIPT_PATH, *sources]:
        path = (project / relative_path).resolve()
        if not path.is_file() or not path.is_relative_to(project):
            raise ValueError(f'Trusted file not found inside project: {relative_path}')
        manifest[relative_path] = _sha256(path)
    run = run_smoke(blender, timeout=timeout, suite='parts')
    report: dict = {
        'schema_version': 1, 'kind': 'local_blender_parts_smoke',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'suite': 'parts', 'run_status': run['status'],
        'source_hashes_sha256': manifest,
        'parts': {}, 'approved': False,
        'warning': ('Smoke results are environment-specific. Not a signed attestation, '
                    'proof of equivalence, clearance for redistribution, or approval.'),
    }
    if run.get('verified'):
        try:
            payload = validate_parts_payload(json.loads(run['message']))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            report['run_status'] = 'failed'
            report['error'] = f'Unexpected Blender output: {exc}'
        else:
            report['blender_version'] = payload['blender']
            for part_id, (source_file, cases) in PART_CASES.items():
                report['parts'][part_id] = {
                    'status': 'blender_smoke_passed',
                    'checks': list(cases),
                    'source': source_file,
                    'source_sha256': manifest[source_file],
                    'verification': 'runtime_smoke_only',
                    'approved': False,
                }
    else:
        report['error'] = run.get('reason') or run.get('message', 'Blender smoke failed')
    return report


def save_evidence(output: str | Path, evidence: dict) -> None:
    _write_json_atomic(output, evidence)


def check_evidence_freshness(evidence: dict, *, root: Path | None = None) -> dict:
    """Check hashes, not authenticity; stale or unverifiable evidence is refused."""
    project = (root or Path(__file__).resolve().parent.parent).resolve()
    paths = evidence.get('source_hashes_sha256')
    errors = []
    if evidence.get('schema_version') != 1 or evidence.get('kind') != 'local_blender_parts_smoke':
        errors.append('Unsupported evidence schema')
    if not isinstance(paths, dict) or set(paths) != {SCRIPT_PATH, *(p for p, _ in PART_CASES.values())}:
        errors.append('Missing or unknown provenance paths')
    else:
        for relative, expected in paths.items():
            current = (project / relative).resolve()
            if not current.is_relative_to(project) or not current.is_file() or _sha256(current) != expected:
                errors.append(f'Code changed or missing: {relative}')
    if evidence.get('run_status') != 'passed':
        errors.append('Smoke suite has not passed')
    parts = evidence.get('parts')
    if not isinstance(parts, dict) or set(parts) != set(PART_CASES):
        errors.append('Missing part-level test results')
    else:
        for id, (source, expected) in PART_CASES.items():
            part = parts[id]
            if not isinstance(part, dict):
                errors.append('Invalid part result: ' + id)
                continue
            if (part.get('source') != source or part.get('checks') != list(expected) or
                    part.get('status') != 'blender_smoke_passed' or part.get('approved') is not False or
                    part.get('source_sha256') != (paths or {}).get(source)):
                errors.append('Invalid part result: ' + id)
    if evidence.get('approved') is not False:
        errors.append('Evidence may not declare approval')
    return {'fresh': not errors, 'errors': errors,
            'note': 'Fresh hashes do not prove authenticity; verify origin of evidence separately.'}
