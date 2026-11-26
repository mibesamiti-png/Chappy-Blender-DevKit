import json
import unittest
from pathlib import Path
ROOT=Path(__file__).parent

class TestSourceProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=json.loads((ROOT/'results'/'first-source-probe.json').read_text(encoding='utf8'))
        cls.matrix=json.loads((ROOT/'observed_matrix.json').read_text(encoding='utf8'))
        cls.cases=json.loads((ROOT/'cases.json').read_text(encoding='utf8'))

    def test_distinct_exact_source_docs(self):
        rows=self.matrix['entries']
        self.assertEqual(len(rows),12)
        self.assertEqual(len({r['id'] for r in rows}),12)
        self.assertTrue(all(r['blob_ok'] and r['anchors_ok'] for r in rows))

    def test_declared_questions_not_modified(self):
        self.assertEqual(len(self.cases),15)
        self.assertEqual(sum(bool(c['topics']) for c in self.cases),9)
        self.assertEqual(sum(len(c['gold_ids']) for c in self.cases),16)

    def test_historical_negative_separate(self):
        old=[r['id'] for r in self.matrix['entries'] if not r['current']]
        self.assertEqual(old,['r15'])
        self.assertEqual(self.result['observed']['hybrid_proxy']['historical_returns'],0)

    def test_result_is_stated_as_proxy(self):
        self.assertIn('probe',self.result['record_type'])
        self.assertFalse(self.result['product_adoption'])
        self.assertFalse(self.result['can_skip_ci'])
        self.assertFalse(self.result['can_authorize_merge'])

    def test_real_misses_are_not_success(self):
        hy=self.result['observed']['hybrid_proxy']
        self.assertEqual((hy['required_found'],hy['required_total']), (11,16))
        self.assertEqual(self.result['result'],'transfer_failed_not_ready')
        self.assertFalse(self.result['strong_gate_met'])
        missed=[x['question'] for x in hy['details'] if x['missing']]
        self.assertEqual(missed,['Q02','Q03','Q05','Q08','Q14'])

    def test_no_rejected_automatic_gate(self):
        for name, d in self.result['observed'].items():
            for row in d['details']:
                self.assertIn(row['status'], ('evidence_candidate_only','needs_authoritative_source'))

    def test_bytes_are_not_tokens(self):
        ratio=self.result['hybrid_vs_full_byte_ratio']
        self.assertAlmostEqual(ratio,447232/3956580)
        self.assertTrue(any('tokens' in l for l in self.result['limits']))

if __name__ == '__main__':unittest.main()
