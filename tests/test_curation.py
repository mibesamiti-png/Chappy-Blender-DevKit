import json
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.curation import (build_review_queue, decide, empty_registry, read_registry,
                           register_candidate, render_review_markdown, write_registry)
from cbdk.dedup import duplicates
from cbdk.scanner import scan


class CurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, code in [('one.py', 'def center(x):\n    return x + 1\n'),
                           ('two.py', 'def middle(x):\n    return x+1\n'),
                           ('three.py', 'def offset(y):\n    return y + 2\n')]:
            (self.root / name).write_text(code, encoding='utf-8')
        self.catalog = scan([self.root])
        self.dup = duplicates(self.catalog)
        self.candidates = {p['qualname']: p['id'] for p in self.catalog['symbols']}

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, *, candidate='center', part_id='GEO-001', **kwargs):
        return register_candidate(self.catalog, self.registry, candidate_id=self.candidates[candidate],
                                  part_id=part_id, name='Center', purpose='Calculate center',
                                  origin='self_owned', license_id='LicenseRef-Proprietary',
                                  license_evidence='owner review', reviewer='owner', **kwargs)

    def test_queue_is_deterministic_and_non_executing(self):
        q1 = build_review_queue(self.catalog, self.dup)
        q2 = build_review_queue(self.catalog, self.dup)
        self.assertEqual(q1, q2)
        self.assertGreater(q1['finding_count'], 0)
        self.assertTrue(all(x['decision'] == 'unreviewed' for x in q1['findings']))
        self.assertIn('center', render_review_markdown(q1))

    def test_register_and_decide_with_fixed_id(self):
        self.registry = empty_registry()
        entry = self.add()
        self.assertEqual(entry['status'], 'proposed')
        self.assertEqual(entry['verification'], 'static_parse_only')
        updated = decide(self.registry, part_id='GEO-001', decision='selected', reviewer='owner', reason='reviewed')
        self.assertEqual(updated['status'], 'selected')
        self.assertEqual(len(updated['history']), 2)
        self.assertNotIn('approved', [x['status'] for x in self.registry['parts']])

    def test_same_ast_requires_variant(self):
        self.registry = empty_registry()
        self.add()
        with self.assertRaisesRegex(ValueError, 'Same AST'):
            self.add(candidate='middle', part_id='GEO-002')
        variant = self.add(candidate='middle', part_id='GEO-002', variant_of='GEO-001')
        self.assertEqual(variant['variant_of'], 'GEO-001')

    def test_rejects_unknown_license_and_duplicate_id(self):
        self.registry = empty_registry()
        self.add()
        with self.assertRaisesRegex(ValueError, 'Stable part ID'):
            self.add(candidate='offset')
        with self.assertRaisesRegex(ValueError, 'Invalid stable ID'):
            self.add(candidate='offset', part_id='oops')
        with self.assertRaisesRegex(ValueError, 'license'):
            register_candidate(self.catalog, self.registry, candidate_id=self.candidates['offset'],
                               part_id='GEO-003', name='Offset', purpose='Offset', origin='self_owned',
                               license_id='unverified', license_evidence='unknown', reviewer='owner')

    def test_rejects_missing_candidates_and_bad_decisions(self):
        self.registry = empty_registry()
        with self.assertRaisesRegex(ValueError, 'Candidate not present'):
            register_candidate(self.catalog, self.registry, candidate_id='CND-NOTFOUND',
                               part_id='GEO-001', name='Name', purpose='Purpose', origin='self_owned',
                               license_id='LicenseRef-Proprietary', license_evidence='owner', reviewer='owner')
        with self.assertRaisesRegex(ValueError, 'Decision'):
            self.add()
            decide(self.registry, part_id='GEO-001', decision='approved', reviewer='owner', reason='bad')

    def test_persistence_is_atomic_and_schema_guarded(self):
        self.registry = empty_registry()
        self.add()
        path = self.root / 'local' / 'registry.json'
        write_registry(path, self.registry)
        self.assertEqual(read_registry(path)['parts'][0]['part_id'], 'GEO-001')
        path.write_text('{"schema_version": 3, "parts": []}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            read_registry(path)

    def test_cli_triage_register_decide(self):
        data = self.root / 'data'
        data.mkdir()
        (data / 'catalog.json').write_text(json.dumps(self.catalog), encoding='utf-8')
        (data / 'duplicates.json').write_text(json.dumps(self.dup), encoding='utf-8')
        queue = data / 'review_queue.json'
        reg = data / 'registry.json'
        self.assertEqual(main(['triage', '--catalog', str(data/'catalog.json'), '--duplicates', str(data/'duplicates.json'), '--output', str(queue)]), 0)
        self.assertTrue(queue.with_suffix('.md').exists())
        self.assertEqual(main(['register', '--catalog', str(data/'catalog.json'), '--registry', str(reg),
                               '--candidate', self.candidates['center'], '--part-id', 'GEO-001',
                               '--name', 'Center', '--purpose', 'Center calc', '--origin', 'self_owned',
                               '--license-id', 'LicenseRef-Proprietary', '--license-evidence', 'owner',
                               '--reviewer', 'owner']), 0)
        self.assertEqual(main(['decide', '--registry', str(reg), '--part-id', 'GEO-001',
                               '--decision', 'hold', '--reviewer', 'owner', '--reason', 'Needs Blender tests']), 0)
        self.assertEqual(main(['parts', '--registry', str(reg)]), 0)
        self.assertEqual(read_registry(reg)['parts'][0]['status'], 'hold')


if __name__ == '__main__':
    unittest.main()
