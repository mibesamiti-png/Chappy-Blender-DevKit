import tempfile
import threading
import subprocess
import sys
import unittest
from handoff import Store, Interrupted


class HandoffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name + '/state.db')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_write_and_checkpoint(self):
        self.assertEqual(self.store.write('A', 1, 0, 'new'), 'applied')
        self.assertEqual(self.store.current()['revision'], 1)
        self.assertEqual(self.store.recover(), 'valid')

    def test_old_writer_after_handoff(self):
        self.assertEqual(self.store.handoff('A', 1, 0, 'B'), 'applied')
        self.assertEqual(self.store.write('A', 1, 0, 'old'), 'rejected')

    def test_reused_writer_identity_rejects_old_epoch(self):
        self.store.handoff('A', 1, 0, 'B')
        self.store.handoff('B', 2, 0, 'A')
        self.assertEqual(self.store.write('A', 1, 0, 'stale'), 'rejected')
        self.assertEqual(self.store.write('A', 3, 0, 'current'), 'applied')

    def test_revision_check(self):
        self.store.write('A', 1, 0, 'one')
        self.assertEqual(self.store.write('A', 1, 0, 'stale'), 'rejected')

    def test_interrupted_write_rolls_back(self):
        with self.assertRaises(Interrupted):
            self.store.write('A', 1, 0, 'broken', 'before_checkpoint')
        self.assertEqual(self.store.current()['payload'], 'seed')
        self.assertEqual(self.store.recover(), 'valid')

    def test_interrupted_handoff_rolls_back(self):
        with self.assertRaises(Interrupted):
            self.store.handoff('A', 1, 0, 'B', 'before_checkpoint')
        self.assertEqual(self.store.current()['writer'], 'A')
        self.assertEqual(self.store.recover(), 'valid')

    def test_human_edit_respected(self):
        self.store.handoff('A', 1, 0, 'H')
        self.store.write('H', 2, 0, 'human')
        self.assertEqual(self.store.write('A', 1, 0, 'robot'), 'rejected')
        self.assertEqual(self.store.current()['payload'], 'human')

    def test_invalid_checkpoint_detection(self):
        self.store.corrupt_checkpoint()
        self.assertEqual(self.store.recover(), 'invalid')

    def test_cannot_transfer_to_same_owner(self):
        self.assertEqual(self.store.handoff('A', 1, 0, 'A'), 'rejected')

    def test_wrong_token_cannot_transfer(self):
        self.assertEqual(self.store.handoff('A', 2, 0, 'B'), 'rejected')

    def test_wrong_revision_cannot_transfer(self):
        self.store.write('A', 1, 0, 'changed')
        self.assertEqual(self.store.handoff('A', 1, 0, 'B'), 'rejected')

    def test_concurrent_writers_exactly_one_commits(self):
        barrier = threading.Barrier(3)
        outcomes = []
        errors = []
        path = self.tmp.name + '/state.db'
        def worker(payload):
            other = Store.open_existing(path)
            try:
                barrier.wait(timeout=5)
                outcomes.append(other.write('A', 1, 0, payload))
            except BaseException as err:
                errors.append(str(err))
            finally:
                other.close()
        t1 = threading.Thread(target=worker, args=('one',))
        t2 = threading.Thread(target=worker, args=('two',))
        t1.start(); t2.start()
        barrier.wait(timeout=5)
        t1.join(timeout=5); t2.join(timeout=5)
        self.assertEqual(errors, [])
        self.assertEqual(sorted(outcomes), ['applied', 'rejected'])
        self.assertEqual(self.store.current()['revision'], 1)
        self.assertEqual(self.store.recover(), 'valid')

    def test_abrupt_child_process_exit_rolls_back(self):
        script = ("import sqlite3,os,sys; "
                  "c=sqlite3.connect(sys.argv[1],isolation_level=None); "
                  "c.execute('BEGIN IMMEDIATE'); "
                  'c.execute("UPDATE live SET payload=\'uncommitted\' WHERE target=\'synthetic-object\'"); '
                  "os._exit(23)")
        result = subprocess.run([sys.executable, '-c', script, self.tmp.name+'/state.db'],
                                timeout=5, check=False)
        self.assertEqual(result.returncode, 23)
        self.assertEqual(self.store.current()['payload'], 'seed')
        self.assertEqual(self.store.recover(), 'valid')

    def test_rollback_followed_by_retry(self):
        with self.assertRaises(Interrupted):
            self.store.write('A', 1, 0, 'broken', 'before_checkpoint')
        self.assertEqual(self.store.write('A', 1, 0, 'safe'), 'applied')
        self.assertEqual(self.store.recover(), 'valid')


if __name__ == '__main__':
    unittest.main()
