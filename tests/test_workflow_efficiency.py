"""Regression guards for PR CI resource usage and handoff integrity."""
import re
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
        # Match exactly three version/digest pairs in the actual matrix block.
        matrix = content.split('      matrix:\n', 1)[1].split('    timeout-minutes:', 1)[0]
        rows = re.findall(r"(?m)^          - blender-version: '([^']+)'\n            archive-sha256: '([0-9a-f]{64})'$", matrix)
        self.assertEqual(matrix.count("- blender-version:"), 3)
        self.assertEqual(rows, [
            ('4.4.3', '8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946'),
            ('4.5.15', '0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773e'),
            ('5.2.1', 'a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9'),
        ])
        self.assertIn('scripts/blender_audit_scaling_smoke.py', content)

if __name__ == "__main__":
    unittest.main()
