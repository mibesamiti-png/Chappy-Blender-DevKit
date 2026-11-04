import subprocess
import unittest
from unittest.mock import patch

from cbdk.blender_test import run_smoke


class BlenderRunnerTests(unittest.TestCase):
    @patch('cbdk.blender_test.subprocess.run')
    def test_accepts_only_zero_exit_and_marker(self, runner):
        runner.return_value = subprocess.CompletedProcess([], 0, 'CBDK_BLENDER_SMOKE_PASS {"blender":"4.3"}\n', '')
        result = run_smoke('blender')
        self.assertTrue(result['verified'])
        args = runner.call_args.args[0]
        self.assertIn('--factory-startup', args)
        self.assertIn('--python-exit-code', args)

    @patch('cbdk.blender_test.subprocess.run')
    def test_rejects_marker_without_success_exit(self, runner):
        runner.return_value = subprocess.CompletedProcess([], 7, 'CBDK_BLENDER_SMOKE_PASS {}', '')
        result = run_smoke('blender')
        self.assertFalse(result['verified'])

    @patch('cbdk.blender_test.subprocess.run', side_effect=FileNotFoundError('missing'))
    def test_executable_missing(self, runner):
        result = run_smoke('missing_blender')
        self.assertEqual(result['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
