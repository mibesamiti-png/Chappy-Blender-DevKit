"""Fail-closed advisory parser for CBDK GitHub Issue #125.

This file does not fetch GitHub, authorize edits, launch agents or validate CI.
A connected assistant must retrieve the latest issue and official assignment itself.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = 'cbdk-role-dispatch-v1'
MARKER = '<!-- CBDK_ROLE_DISPATCH_V1 -->'
ROLE_MAPS = {'normal': {'B': 'B', 'C': 'C', 'D': 'D'},
             'integration_support': {'B': 'E', 'C': 'G', 'D': 'F'}}
TEAM = frozenset(('B', 'C', 'D'))
VALID_STATES = frozenset(('active', 'pilot_inactive'))


class DispatchError(ValueError):
    """An ambiguous or invalid advisory dispatch must not be applied."""


def parse_issue(body: str) -> dict[str, Any]:
    """Extract exactly one JSON code fence after the known issue marker."""
    if not isinstance(body, str) or body.count(MARKER) != 1:
        raise DispatchError('issue marker absent or duplicated')
    blocks = re.findall(r'```json\s*\n(.*?)\n```', body, flags=re.DOTALL)
    if len(blocks) != 1:
        raise DispatchError('expected exactly one JSON dispatch block')
    try:
        data = json.loads(blocks[0])
    except (ValueError, TypeError) as exc:
        raise DispatchError('invalid JSON block') from exc
    if not isinstance(data, dict):
        raise DispatchError('dispatch must be an object')
    if data.get('schema') != SCHEMA:
        raise DispatchError('unsupported schema')
    rev = data.get('revision')
    if type(rev) is not int or rev < 0:
        raise DispatchError('revision must be nonnegative integer')
    if data.get('state') not in VALID_STATES:
        raise DispatchError('invalid dispatch state')
    phase = data.get('phase')
    if phase not in ROLE_MAPS:
        raise DispatchError('invalid phase')
    if data.get('team_roles') != ROLE_MAPS[phase]:
        raise DispatchError('phase and team roles disagree')
    rnd = data.get('round')
    if not isinstance(rnd, str) or not re.fullmatch(r'R[1-9][0-9]*', rnd):
        raise DispatchError('invalid round')
    if data.get('development_branch') != 'feature/v0.18-shape-diagnostics':
        raise DispatchError('unexpected development branch')
    if data.get('official_assignment') != f'docs/{rnd}_ABCD_START.md':
        raise DispatchError('dispatch and official assignment disagree')
    return data


def advise(body: str | None, team: str, official_round: str, *,
           minimum_revision: int | None = None, exact_head_ci_verified: bool = False) -> dict[str, Any]:
    """Produce an advisory role, never permission for CI bypass, merges or edits.

    The caller is responsible for independently verifying the canonical GitHub
    issue, newest official round, exact-head required CI and actor's PR status.
    Unknown/missing inputs return normal role with blocked new work.
    """
    if team not in TEAM:
        raise DispatchError('team must be one of B, C, D')
    result = {
        'team': team,
        'role': team,
        'phase': 'normal',
        'decision': 'ignore_dispatch',
        'reason': 'dispatch_unavailable',
        'may_start_new_work': False,
        'may_skip_ci': False,
        'may_merge': False,
        'may_modify_a_owned_files': False,
    }
    try:
        data = parse_issue(body or '')
    except DispatchError:
        return result
    if data['state'] != 'active':
        result['reason'] = 'pilot_inactive'
        return result
    if not re.fullmatch(r'R[1-9][0-9]*', official_round or ''):
        result['reason'] = 'unknown_official_round'
        return result
    if data['round'] != official_round:
        result['reason'] = 'stale_or_future_round'
        return result
    if minimum_revision is not None:
        if type(minimum_revision) is not int or minimum_revision < 0:
            raise DispatchError('minimum_revision must be nonnegative integer')
        if data['revision'] < minimum_revision:
            result['reason'] = 'revision_rollback'
            return result
    result['revision'] = data['revision']
    result['phase'] = data['phase']
    if data['phase'] == 'normal':
        result.update(role=team, decision='normal_advisory', reason='official_assignment_still_controls')
        return result
    if not exact_head_ci_verified:
        result.update(decision='support_pending_evidence',
                      reason='exact_head_ci_and_pr_state_not_verified')
        return result
    result.update(role=ROLE_MAPS['integration_support'][team],
                  decision='support_read_only_advisory',
                  reason='subject_to_official_rules_and_a_review')
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--issue-body', type=Path, required=True,
                    help='local UTF-8 copy of Issue #125 body; no network calls')
    ap.add_argument('--team', choices=sorted(TEAM), required=True)
    ap.add_argument('--official-round', required=True)
    ap.add_argument('--minimum-revision', type=int)
    ap.add_argument('--exact-head-ci-verified', action='store_true',
                    help='caller confirms external evidence; NOT checked by this script')
    args = ap.parse_args()
    try:
        body = args.issue_body.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        body = None
    ans = advise(body, args.team, args.official_round,
                 minimum_revision=args.minimum_revision,
                 exact_head_ci_verified=args.exact_head_ci_verified)
    print(json.dumps(ans, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
