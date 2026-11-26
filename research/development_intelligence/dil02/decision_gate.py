"""DIL-02: deterministic, read-only *proposal* gate, not an AI or executor."""

MODES = {'idea', 'adopt', 'continue'}


def admissible(option, budget):
    """Require declared goal fit, all non-negotiable gates, and remaining budget."""
    return (option['fits_goal'] is True and option['gates_passed'] is True
            and option['effort'] <= budget)


def decide(case):
    """Return a recommendation, never authorize/perform edits or approvals."""
    if type(case.get('budget')) is not int or case['budget'] < 0:
        raise ValueError('invalid budget')
    if case['mode'] not in MODES:
        raise ValueError('invalid mode')
    if not isinstance(case['goal_revision'], str) or not case['goal_revision']:
        raise ValueError('invalid goal revision')
    if type(case['checks_passed']) is not bool or type(case['evidence_fresh']) is not bool:
        raise ValueError('invalid verification flags')
    ids = set()
    for option in case['options']:
        if (not isinstance(option['id'], str) or not option['id'] or
                option['id'] in ids or
                type(option['effort']) is not int or option['effort'] < 0 or
                type(option['complexity']) is not int or option['complexity'] < 0 or
                type(option['fits_goal']) is not bool or
                type(option['gates_passed']) is not bool):
            raise ValueError('invalid option')
        ids.add(option['id'])
    if (case['accepted_revision'] == case['goal_revision'] and
            case['checks_passed']):
        return {'action': 'stop' if case['evidence_fresh'] else 'verify',
                'option': None, 'reason': 'accepted' if case['evidence_fresh'] else 'stale_evidence'}
    valid = [o for o in case['options'] if admissible(o, case['budget'])]
    if case['mode'] == 'adopt':
        chosen = next((o for o in valid if o['id'] == case['hint']), None)
        if chosen is None:
            return {'action': 'escalate', 'option': None, 'reason': 'explicit_choice_blocked'}
        return {'action': 'choose', 'option': chosen['id'], 'reason': 'explicit_choice'}
    if not valid:
        return {'action': 'escalate', 'option': None, 'reason': 'no_admissible_plan'}
    chosen = min(valid, key=lambda o: (o['effort'], o['complexity'], o['id']))
    return {'action': 'choose', 'option': chosen['id'], 'reason': 'minimum_sufficient'}


def idea_first(case):
    """Toy comparator: latest hint dominates; no evidence/constraint enforcement."""
    if case['accepted_revision'] == case['goal_revision'] and case['checks_passed'] and case['evidence_fresh']:
        return {'action': 'stop', 'option': None}
    if case['hint'] and any(o['id'] == case['hint'] for o in case['options']):
        return {'action': 'choose', 'option': case['hint']}
    if not case['options']:
        return {'action': 'escalate', 'option': None}
    return {'action': 'choose', 'option': min(case['options'], key=lambda o: o['effort'])['id']}


def quality_max(case):
    """Toy comparator: maximizes claimed quality even after goal acceptance."""
    if not case['options']:
        return {'action': 'escalate', 'option': None}
    return {'action': 'choose', 'option': max(case['options'], key=lambda o: o['quality'])['id']}
