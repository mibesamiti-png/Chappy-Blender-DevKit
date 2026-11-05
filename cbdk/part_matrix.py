"""Summarize local Blender smoke evidence without changing component approval.

Evidence is local/untrusted JSON. Its source hashes are checked against the
current project, but neither hash equality nor green smoke tests authenticate
remote provenance or grant a license/approval for redistribution.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from .curation import _write_json_atomic
from .evidence import PART_CASES, check_evidence_freshness

MAX_EVIDENCE_FILES = 128
MAX_EVIDENCE_BYTES = 2_000_000
VERSION_RE = re.compile(r"(?:Blender\s+)?(\d+)\.(\d+)\.(\d+)(?:\b|$)")


def _version(raw: object) -> str:
    if not isinstance(raw, str) or len(raw) > 100:
        raise ValueError('invalid Blender version string')
    match = VERSION_RE.search(raw)
    if not match:
        raise ValueError('Blender version must include major.minor.patch')
    return '.'.join(str(int(x)) for x in match.groups())


def evidence_paths(directory: str | Path | None, explicit: Iterable[str | Path] = ()) -> list[Path]:
    """Collect named evidence JSON only (not arbitrary local catalog JSON)."""
    paths = [Path(p) for p in explicit]
    if directory is not None:
        folder = Path(directory)
        if not folder.is_dir():
            raise ValueError(f'Evidence directory not found: {folder}')
        paths.extend(folder.glob('parts_evidence*.json'))
    unique = {str(path.resolve()): path for path in paths}
    if len(unique) > MAX_EVIDENCE_FILES:
        raise ValueError('Too many evidence files')
    return [unique[name] for name in sorted(unique)]


def summarize_parts(catalog: dict, paths: Iterable[str | Path], *, root: Path | None = None) -> dict:
    """Produce a non-authoritative, read-only runtime matrix from local reports."""
    if catalog.get('schema_version') != 1 or not isinstance(catalog.get('parts'), list):
        raise ValueError('Expected authored-parts schema 1')
    catalog_parts = {}
    for entry in catalog['parts']:
        if not isinstance(entry, dict):
            raise ValueError('Invalid authored part')
        part_id, source = entry.get('part_id'), entry.get('source')
        if not isinstance(part_id, str) or part_id in catalog_parts or not isinstance(source, str):
            raise ValueError('Missing or repeated authored part ID/source')
        catalog_parts[part_id] = entry

    records = {part_id: {'part_id': part_id, 'name': part.get('name'),
                          'source': part['source'], 'catalog_status': part.get('status'),
                          'catalog_approved': part.get('approved') is True,
                          'license_review': part.get('license_review'),
                          'runtime_versions': [], 'verification': 'not_recorded',
                          'approved_by_evidence': False, 'authenticity': 'not_verified'}
               for part_id, part in sorted(catalog_parts.items())}
    good: list[dict] = []
    rejected: list[dict] = []
    given = list(paths)
    if len(given) > MAX_EVIDENCE_FILES:
        raise ValueError('Too many evidence files')
    seen: set[str] = set()
    for raw_path in given:
        path = Path(raw_path)
        label = path.name
        if str(path.resolve()) in seen:
            continue
        seen.add(str(path.resolve()))
        try:
            if path.suffix.lower() != '.json' or path.is_symlink() or not path.is_file():
                raise ValueError('Expected a regular non-symlink JSON evidence file')
            if path.stat().st_size > MAX_EVIDENCE_BYTES:
                raise ValueError('Evidence JSON exceeds size limit')
            payload = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(payload, dict):
                raise ValueError('Evidence is not a JSON object')
            freshness = check_evidence_freshness(payload, root=root)
            if not freshness['fresh']:
                raise ValueError('; '.join(freshness['errors']))
            version = _version(payload.get('blender_version'))
            part_report = payload['parts']
            for part_id, info in part_report.items():
                if part_id not in catalog_parts:
                    raise ValueError('Unknown part ID in evidence')
                if info.get('source') != catalog_parts[part_id]['source']:
                    raise ValueError('Catalog source mismatch for ' + part_id)
                if part_id not in PART_CASES:
                    raise ValueError('No trusted smoke contract for ' + part_id)
            good.append({'file': label, 'blender_version': version,
                         'timestamp_utc_untrusted': payload.get('timestamp_utc')})
            for part_id in part_report:
                if version not in records[part_id]['runtime_versions']:
                    records[part_id]['runtime_versions'].append(version)
        except (OSError, ValueError, UnicodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
            rejected.append({'file': label, 'reason': str(exc)[:400]})

    for entry in records.values():
        entry['runtime_versions'].sort(key=lambda x: tuple(int(p) for p in x.split('.')))
        if entry['runtime_versions']:
            entry['verification'] = 'blender_smoke_passed'

    return {'schema_version': 1, 'kind': 'derived_local_part_matrix',
            'parts': list(records.values()), 'valid_evidence_count': len(good),
            'invalid_evidence_count': len(rejected), 'valid_evidence': good,
            'rejected_evidence': rejected,
            'has_runtime_evidence': bool(good),
            'approved_by_evidence': False,
            'warning': ('For local review only. JSON may be forged. Fresh hashes do not authenticate '
                        'the executor; smoke results do not grant approval, licensing or broad compatibility.')}


def write_matrix(output: str | Path, matrix: dict) -> None:
    _write_json_atomic(output, matrix)


def render_matrix_markdown(matrix: dict) -> str:
    rows = ['# CBDK Blender runtime matrix', '',
            'This is untrusted local smoke evidence, not an approval or license clearance.', '',
            '| Part | Smoke-verified Blender versions | Catalog approval |', '|---|---|---|']
    for entry in matrix['parts']:
        versions = ', '.join(entry['runtime_versions']) if entry['runtime_versions'] else 'Not recorded'
        rows.append(f"| {entry['part_id']} | {versions} | {'yes' if entry['catalog_approved'] else 'no'} |")
    rows.extend(['', f"Valid reports: {matrix['valid_evidence_count']}; "
                     f"rejected: {matrix['invalid_evidence_count']}."])
    for failure in matrix['rejected_evidence']:
        rows.append(f"- Rejected {failure['file']}: {failure['reason']}")
    return '\n'.join(rows) + '\n'
