"""DIL-03 cooperative synthetic checkpoint + ownership protocol (offline).

Not a process lock, authentication service, Blender integration, or recovery daemon.
"""
import hashlib
import json
import sqlite3

TARGET = 'synthetic-object'


class Interrupted(Exception):
    """Injected failure in the simulation, *not* a physical crash."""


def digest(s):
    raw = json.dumps(s, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class Store:
    """Transactional guarded store; all cooperative writes pass these methods."""

    def __init__(self, path):
        self.db = sqlite3.connect(str(path), isolation_level=None, timeout=2)
        self.db.execute('PRAGMA busy_timeout=2000')
        self.db.execute('CREATE TABLE live(target TEXT PRIMARY KEY, writer TEXT NOT NULL, epoch INTEGER NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE checkpoint(target TEXT PRIMARY KEY, writer TEXT NOT NULL, epoch INTEGER NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL)')
        self.db.execute('INSERT INTO live VALUES(?,?,?,?,?)', (TARGET, 'A', 1, 0, 'seed'))
        self._save_checkpoint({'writer': 'A', 'epoch': 1, 'revision': 0, 'payload': 'seed'})

    @classmethod
    def open_existing(cls, path):
        obj = cls.__new__(cls)
        obj.db = sqlite3.connect(str(path), isolation_level=None, timeout=2)
        obj.db.execute('PRAGMA busy_timeout=2000')
        return obj

    def _save_checkpoint(self, s):
        self.db.execute('INSERT OR REPLACE INTO checkpoint VALUES(?,?,?,?,?,?)',
                        (TARGET, s['writer'], s['epoch'], s['revision'], s['payload'], digest(s)))

    def current(self):
        row = self.db.execute('SELECT writer,epoch,revision,payload FROM live WHERE target=?', (TARGET,)).fetchone()
        return dict(zip(('writer','epoch','revision','payload'), row))

    def _transition(self, action, actor, epoch, revision, value, failpoint):
        if failpoint not in (None, 'before_checkpoint'):
            raise ValueError('unknown failpoint')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            state = self.current()
            if (state['writer'], state['epoch'], state['revision']) != (actor, epoch, revision):
                self.db.execute('ROLLBACK')
                return 'rejected'
            after = dict(state)
            if action == 'write':
                after['payload'] = value
                after['revision'] += 1
            elif action == 'handoff':
                if value == state['writer'] or not value:
                    self.db.execute('ROLLBACK')
                    return 'rejected'
                after['writer'] = value
                after['epoch'] += 1
            else:
                raise ValueError('unknown action')
            self.db.execute('UPDATE live SET writer=?,epoch=?,revision=?,payload=? WHERE target=?',
                            (after['writer'],after['epoch'],after['revision'],after['payload'],TARGET))
            if failpoint == 'before_checkpoint':
                raise Interrupted('injected between state and checkpoint')
            self._save_checkpoint(after)
            self.db.execute('COMMIT')
            return 'applied'
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise

    def write(self, actor, epoch, revision, payload, failpoint=None):
        return self._transition('write', actor, epoch, revision, payload, failpoint)

    def handoff(self, actor, epoch, revision, next_writer, failpoint=None):
        return self._transition('handoff', actor, epoch, revision, next_writer, failpoint)

    def corrupt_checkpoint(self):
        self.db.execute('UPDATE checkpoint SET payload=? WHERE target=?', ('corrupted', TARGET))
        return 'applied'

    def recover(self):
        row = self.db.execute('SELECT writer,epoch,revision,payload,hash FROM checkpoint WHERE target=?', (TARGET,)).fetchone()
        if row is None:
            return 'invalid'
        s = dict(zip(('writer','epoch','revision','payload'), row[:4]))
        if row[4] != digest(s) or s != self.current():
            return 'invalid'
        return 'valid'

    def close(self):
        self.db.close()


class ReferenceStore:
    """Two deliberately simple reference baselines, not CBDK production code."""

    def __init__(self, revision_cas=False):
        self.revision_cas = revision_cas
        self.state = {'writer':'A','epoch':1,'revision':0,'payload':'seed'}
        self.checkpoint = dict(self.state)

    def current(self):
        return dict(self.state)

    def _transition(self, action, actor, epoch, revision, value, failpoint):
        if actor != self.state['writer']:
            return 'rejected'
        if self.revision_cas and revision != self.state['revision']:
            return 'rejected'
        if action == 'handoff' and (not value or value == self.state['writer']):
            return 'rejected'
        after = dict(self.state)
        if action == 'write':
            after['payload'] = value
            after['revision'] += 1
        else:
            after['writer'] = value
            after['epoch'] += 1
        self.state = after
        if failpoint == 'before_checkpoint':
            raise Interrupted('injected after non-atomic state change')
        self.checkpoint = dict(after)
        return 'applied'

    def write(self, actor, epoch, revision, payload, failpoint=None):
        return self._transition('write', actor, epoch, revision, payload, failpoint)

    def handoff(self, actor, epoch, revision, next_writer, failpoint=None):
        return self._transition('handoff', actor, epoch, revision, next_writer, failpoint)

    def corrupt_checkpoint(self):
        self.checkpoint['payload'] = 'corrupted'
        return 'applied'

    def recover(self):
        # A naive reader reports checkpoint availability; no hash/target validation.
        return 'valid' if self.checkpoint else 'invalid'

    def close(self):
        pass


def simulate(store, scenario):
    statuses = []
    for event in scenario['events']:
        try:
            op = event['op']
            if op == 'write':
                result = store.write(event['actor'], event['epoch'], event['revision'], event['payload'], event.get('failpoint'))
            elif op == 'handoff':
                result = store.handoff(event['actor'], event['epoch'], event['revision'], event['next_writer'], event.get('failpoint'))
            elif op == 'corrupt_checkpoint':
                result = store.corrupt_checkpoint()
            else:
                raise ValueError('invalid event')
        except Interrupted:
            result = 'interrupted'
        statuses.append(result)
    return {'statuses': statuses, 'state': store.current(), 'recovery': store.recover()}
