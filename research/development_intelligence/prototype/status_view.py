"""DIL-01: read-only observation classifier, NOT a lock or liveness guarantee.

The caller must supply trusted expected identity and observation time. No IO,
network, process probes, scheduling, ownership transfer or automatic execution.
"""
import re

STATES = {'running', 'pause_requested', 'paused', 'awaiting_confirmation',
          'failed', 'completed', 'stopped'}
IDENTITY = ('work_id', 'target_id', 'attempt_id', 'revision')
TOKEN = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
FIELDS = set(IDENTITY) | {'status', 'updated_at', 'heartbeat_at',
                          'heartbeat_attempt', 'verified_steps', 'total_steps'}


def _integer(x):
    return type(x) is int and 0 <= x <= 10**12


def observe(record, expected, now, *, snapshot_ttl=300, heartbeat_ttl=30):
    """All times are integer seconds in one caller-controlled clock domain.

    Valid recent evidence means 'recently observed', not 'still running now'.
    Raw input strings never appear in diagnostics. verified_steps are declared
    counts: this prototype does not validate referenced artifacts.
    """
    def result(state, reason, age=None, counts=None):
        return dict(state=state, reason=reason, age_seconds=age,
                    recently_observed=state == 'running_observed',
                    step_counts=counts, edit_authorized=False, eta=None)

    if (not _integer(now) or type(snapshot_ttl) is not int or
            type(heartbeat_ttl) is not int or
            not 1 <= heartbeat_ttl <= snapshot_ttl <= 3600):
        raise ValueError('invalid clock policy')
    if not isinstance(record, dict) or not isinstance(expected, dict):
        return result('invalid', 'schema')
    if set(record) != FIELDS or set(expected) != set(IDENTITY):
        return result('invalid', 'schema')
    for key in IDENTITY:
        if any(type(v) is not str or not TOKEN.fullmatch(v)
               for v in (record[key], expected[key])):
            return result('invalid', 'identity_type')
    if any(record[k] != expected[k] for k in IDENTITY):
        return result('conflict', 'identity_changed')
    if type(record['status']) is not str or record['status'] not in STATES:
        return result('invalid', 'status')
    if not _integer(record['updated_at']):
        return result('invalid', 'timestamp')
    if not all(_integer(record[k]) for k in ('verified_steps', 'total_steps')):
        return result('invalid', 'counts')
    done, total = record['verified_steps'], record['total_steps']
    if done > total or total > 10000:
        return result('invalid', 'counts')
    if record['status'] == 'completed' and (not total or done != total):
        return result('invalid', 'incomplete_completion')
    age = now - record['updated_at']
    if age < 0:
        return result('unknown', 'clock_ahead')
    if age > snapshot_ttl:
        return result('stale', 'snapshot_expired', age)
    # heartbeat timestamp/identity are optional as a pair, but malformed fields
    # are never quietly ignored, even for terminal records.
    hb, attempt = record['heartbeat_at'], record['heartbeat_attempt']
    if hb is not None or attempt is not None:
        if not _integer(hb) or type(attempt) is not str or not TOKEN.fullmatch(attempt):
            return result('invalid', 'heartbeat_schema', age)
        if hb > record['updated_at']:
            return result('unknown', 'heartbeat_ahead', age)
    counts = dict(declared_verified=done, total=total)
    if record['status'] != 'running':
        return result('reported_' + record['status'], 'record_only', age, counts)
    if hb is None:
        return result('unknown', 'heartbeat_missing', age, counts)
    if attempt != expected['attempt_id']:
        return result('unknown', 'heartbeat_wrong_attempt', age, counts)
    if now - hb > heartbeat_ttl:
        return result('unknown', 'heartbeat_expired', age, counts)
    return result('running_observed', 'recent_heartbeat', age, counts)
