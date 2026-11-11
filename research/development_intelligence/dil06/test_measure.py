"""Focused negative controls; not a real-world productivity trial."""
import copy
import json
from pathlib import Path
import unittest

from measure import analyze_round, analyze_snapshot, check_team, utc

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / 'observed.json').read_text(encoding='utf-8'))

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.r13 = copy.deepcopy(DATA['rounds'][0])
        self.r14 = copy.deepcopy(DATA['rounds'][1])

    def test_r13_observed_gap(self):
        self.assertEqual(analyze_round(self.r13)['ci_to_integration_pr_publication_gap_seconds'], 504)

    def test_r14_observed_gap(self):
        self.assertEqual(analyze_round(self.r14)['ci_to_integration_pr_publication_gap_seconds'], 236816)

    def test_r15_pending(self):
        self.assertEqual(analyze_round(DATA['rounds'][2])['report_kind'], 'insufficient_evidence')

    def test_teams_require_five_families(self):
        self.r14['teams'][0]['workflows'].pop()
        self.assertIn('B:required_workflow_family_missing', analyze_round(self.r14)['blockers'])

    def test_run_wrong_sha_blocks(self):
        self.r14['teams'][0]['workflows'][0]['head_sha'] = 'a'*40
        self.assertIsNone(analyze_round(self.r14)['ci_to_integration_pr_publication_gap_seconds'])

    def test_job_wrong_sha_blocks(self):
        self.r14['teams'][0]['workflows'][0]['jobs'][0]['head_sha'] = 'a'*40
        self.assertIn('B:required_job_sha_mismatch', analyze_round(self.r14)['blockers'])

    def test_missing_required_matrix_job_blocks(self):
        f=self.r13['teams'][0]['workflows'][0]
        f['jobs'] = f['jobs'][1:]
        f['job_total'] -= 1
        self.assertIsNone(analyze_round(self.r13)['ci_to_integration_pr_publication_gap_seconds'])

    def test_unrelated_skipped_job_is_ok(self):
        self.assertEqual(analyze_round(self.r14)['report_kind'], 'observed_publication_interval')
        self.assertTrue(any(j['conclusion']=='skipped' for j in self.r14['teams'][0]['workflows'][-1]['jobs']))

    def test_stale_team_head_blocks(self):
        self.r14['teams'][0]['head_sha'] = 'a'*40
        self.assertIsNone(analyze_round(self.r14)['last_required_ci_job_completed_at'])

    def test_incomplete_jobs_listing_blocks(self):
        self.r13['teams'][0]['workflows'][0]['job_total'] += 1
        self.assertIn('B:job_listing_incomplete', analyze_round(self.r13)['blockers'])

    def test_no_human_efficiency_claim(self):
        for r in analyze_snapshot(DATA)['rounds']:
            self.assertTrue(all(v is None for v in r['unobservable'].values()))
            self.assertFalse(r['is_proof_of_speedup'])
            self.assertFalse(r['can_authorize_merge'])
            self.assertFalse(r['can_skip_ci'])

    def test_integration_before_green_blocks(self):
        self.r13['integration_pr']['created_at']='2026-11-08T01:50:00Z'
        self.assertIn('integration_pr_created_before_complete_ci', analyze_round(self.r13)['blockers'])

    def test_duplicate_family_blocks(self):
        self.r13['teams'][0]['workflows'].append(copy.deepcopy(self.r13['teams'][0]['workflows'][0]))
        self.assertIn('B:duplicate_workflow_family', analyze_round(self.r13)['blockers'])

    def test_timestamps_are_utc_and_valid(self):
        for bad in ['2026-11-08T02:35:37', '2026-11-08T02:35:37+09:00', 'tomorrow', None]:
            with self.assertRaises(ValueError):
                utc(bad)

    def test_source_is_not_mutated(self):
        x=copy.deepcopy(self.r14)
        analyze_round(x)
        self.assertEqual(self.r14,x)

if __name__ == '__main__':
    unittest.main()
