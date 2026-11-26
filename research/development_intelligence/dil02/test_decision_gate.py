import unittest
from decision_gate import decide


def option(id, effort=2, complexity=1, fits_goal=True, gates_passed=True):
    return dict(id=id, effort=effort, complexity=complexity,
                fits_goal=fits_goal, gates_passed=gates_passed, quality=10)


def case(**updates):
    row = dict(goal_revision='2', accepted_revision=None, checks_passed=False,
               evidence_fresh=True, mode='continue', hint=None, budget=10,
               options=[option('small'), option('large', 7, 8)])
    row.update(updates)
    return row


class DecisionGateTest(unittest.TestCase):
    def test_minimum_sufficient(self):
        self.assertEqual(decide(case())['option'], 'small')

    def test_idea_not_binding(self):
        self.assertEqual(decide(case(mode='idea', hint='large'))['option'], 'small')

    def test_adoption_binding(self):
        self.assertEqual(decide(case(mode='adopt', hint='large'))['option'], 'large')

    def test_adoption_cannot_bypass_budget(self):
        self.assertEqual(decide(case(mode='adopt', hint='large', budget=3))['action'], 'escalate')

    def test_stop_after_accepted(self):
        self.assertEqual(decide(case(accepted_revision='2', checks_passed=True))['action'], 'stop')

    def test_stale_acceptance_requires_verify(self):
        self.assertEqual(decide(case(accepted_revision='2', checks_passed=True,
                                     evidence_fresh=False))['action'], 'verify')

    def test_goal_revision_changes_scope(self):
        self.assertEqual(decide(case(accepted_revision='1', checks_passed=True))['action'], 'choose')

    def test_required_gate(self):
        self.assertEqual(decide(case(options=[option('risky', 1, 1, gates_passed=False),
                                              option('safe', 3)]))['option'], 'safe')

    def test_no_eligible_option(self):
        self.assertEqual(decide(case(budget=0))['action'], 'escalate')

    def test_malformed_flag(self):
        with self.assertRaises(ValueError):
            decide(case(checks_passed=1))

    def test_duplicate_candidate(self):
        with self.assertRaises(ValueError):
            decide(case(options=[option('same'), option('same')]))

    def test_does_not_mutate(self):
        c = case()
        before = repr(c)
        decide(c)
        self.assertEqual(repr(c), before)


if __name__ == '__main__':
    unittest.main()
