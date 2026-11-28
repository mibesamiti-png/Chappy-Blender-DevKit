"""Local standalone tests: python -m unittest discover -s tests -p test_role_dispatch.py -v"""
import importlib.util
import json
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'role_dispatch.py'
spec = importlib.util.spec_from_file_location('role_dispatch', MODULE)
dispatch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatch)


def issue(**overrides):
    data = dict(schema='cbdk-role-dispatch-v1', revision=1, state='active',
                round='R16', phase='normal',
                development_branch='feature/v0.18-shape-diagnostics',
                official_assignment='docs/R16_ABCD_START.md',
                team_roles={'B': 'B', 'C': 'C', 'D': 'D'})
    data.update(overrides)
    return '<!-- CBDK_ROLE_DISPATCH_V1 -->\n```json\n' + json.dumps(data) + '\n```\n'


class RoleDispatchTests(unittest.TestCase):
    def test_all_normal_roles(self):
        for team in 'BCD':
            with self.subTest(team=team):
                r=dispatch.advise(issue(),team,'R16')
                self.assertEqual(r['role'],team)
                self.assertEqual(r['decision'],'normal_advisory')
                self.assertFalse(r['may_start_new_work'])

    def test_all_support_roles_after_external_confirmation(self):
        for team,role in zip('BCD','EGF'):
            with self.subTest(team=team):
                doc=issue(phase='integration_support',team_roles={'B':'E','C':'G','D':'F'})
                r=dispatch.advise(doc,team,'R16',exact_head_ci_verified=True)
                self.assertEqual(r['role'],role)
                self.assertEqual(r['decision'],'support_read_only_advisory')
                self.assertFalse(r['may_start_new_work'])
                self.assertFalse(r['may_skip_ci'])
                self.assertFalse(r['may_merge'])

    def test_support_without_external_ci_stays_normal(self):
        doc=issue(phase='integration_support',team_roles={'B':'E','C':'G','D':'F'})
        r=dispatch.advise(doc,'B','R16')
        self.assertEqual(r['role'],'B')
        self.assertEqual(r['decision'],'support_pending_evidence')

    def test_stale_round_stays_normal(self):
        self.assertEqual(dispatch.advise(issue(), 'B', 'R17')['reason'],'stale_or_future_round')

    def test_revision_rollback_stays_normal(self):
        self.assertEqual(dispatch.advise(issue(revision=2),'C','R16',minimum_revision=3)['reason'],'revision_rollback')

    def test_inactive_stays_normal(self):
        self.assertEqual(dispatch.advise(issue(state='pilot_inactive'),'D','R16')['reason'],'pilot_inactive')

    def test_unavailable_stays_normal(self):
        self.assertEqual(dispatch.advise(None,'B','R16')['reason'],'dispatch_unavailable')

    def test_invalid_json_stays_normal(self):
        self.assertEqual(dispatch.advise('<!-- CBDK_ROLE_DISPATCH_V1 -->\n```json\n{\n```','B','R16')['role'],'B')

    def test_multiple_dispatch_blocks_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue()+'\n```json\n{}\n```')

    def test_duplicate_marker_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue()+ '<!-- CBDK_ROLE_DISPATCH_V1 -->')

    def test_phase_mismatch_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue(phase='integration_support'))

    def test_wrong_assignment_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue(official_assignment='docs/R15_ABCD_START.md'))

    def test_wrong_branch_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue(development_branch='main'))

    def test_unknown_schema_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue(schema='v99'))

    def test_boolean_revision_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.parse_issue(issue(revision=True))

    def test_invalid_team_rejected(self):
        with self.assertRaises(dispatch.DispatchError):
            dispatch.advise(issue(),'A','R16')

    def test_no_claim_of_authority_under_any_route(self):
        for doc in [issue(),issue(state='pilot_inactive'),issue(phase='integration_support',team_roles={'B':'E','C':'G','D':'F'})]:
            for team in 'BCD':
                r=dispatch.advise(doc,team,'R16',exact_head_ci_verified=True)
                for key in ('may_start_new_work','may_skip_ci','may_merge','may_modify_a_owned_files'):
                    self.assertFalse(r[key])

    def test_parse_existing_issue_schema(self):
        doc=issue(state='pilot_inactive', revision=0)
        d=dispatch.parse_issue(doc)
        self.assertEqual(d['round'],'R16')
        self.assertEqual(d['revision'],0)


if __name__ == '__main__':
    unittest.main()
