"""Regression guards for PR CI resource usage and handoff integrity."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
FILES = ('test.yml', 'blender-smoke.yml', 'windows-launcher.yml',
         'package-windows-kit.yml', 'skill-package.yml', 'durable-handoff.yml')

class WorkflowEfficiencyTests(unittest.TestCase):
    def test_pr_runs_cancel_superseded_workflows(self):
        for name in FILES:
            with self.subTest(name=name):
                text = (WORKFLOWS / name).read_text(encoding='utf-8')
                self.assertIn("group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}", text)
                self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", text)

    def test_python_workflow_avoids_duplicate_branch_pushes(self):
        content = (WORKFLOWS / 'test.yml').read_text(encoding='utf-8')
        self.assertIn('  pull_request:\n', content)
        self.assertIn('  push:\n    branches: [main]', content)
        self.assertNotIn('on: [push, pull_request]', content)

    def test_handoff_does_not_run_duplicate_unittest_on_pr(self):
        content = (WORKFLOWS / 'durable-handoff.yml').read_text(encoding='utf-8')
        self.assertIn("- name: Run Python regression tests\n        if: github.event_name != 'pull_request'", content)
        self.assertIn("- name: Save actual Python CI observation\n        if: github.event_name != 'pull_request'", content)
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/main'", content)

    def test_blender_matrix_remains_full(self):
        content = (WORKFLOWS / 'blender-smoke.yml').read_text(encoding='utf-8')
        self.assertIn("['4.4.3', '4.5.15', '5.2.1']", content)
        self.assertIn('scripts/blender_audit_scaling_smoke.py', content)

if __name__ == "__main__":
    unittest.main()
