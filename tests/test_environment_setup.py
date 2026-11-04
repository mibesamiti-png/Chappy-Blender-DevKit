"""Static regression checks for opt-in test environment scaffolding.

These do not prove Windows/Blender execution; Actions runtime smoke does that.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentSetupTests(unittest.TestCase):
    def test_one_click_runner_does_not_install_anything(self):
        bat = (ROOT / 'run_blender_tests_windows.bat').read_text(encoding='utf-8')
        ps = (ROOT / 'scripts/windows_run_blender_tests.ps1').read_text(encoding='utf-8')
        self.assertIn('windows_run_blender_tests.ps1', bat)
        self.assertIn('verify-parts', ps)
        self.assertIn('evidence-status', ps)
        self.assertIn('Resolve-Blenders', ps)
        self.assertIn('Start-Process -FilePath', ps)
        self.assertIn('RedirectStandardError', ps)
        self.assertIn('UnitOnly', ps)
        self.assertIn('parts_evidence_', ps)
        self.assertNotIn('*> $unitLog', ps)
        self.assertNotIn('Invoke-WebRequest', ps)
        self.assertNotIn('winget install', ps.lower())

    def test_github_workflow_checks_download_checksum_and_runs_blender(self):
        job = (ROOT / '.github/workflows/blender-smoke.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', job)
        self.assertIn("blender-version: ['4.4.3', '4.5.15', '5.2.1']", job)
        self.assertIn('blender-${BLENDER_VERSION}.sha256', job)
        self.assertIn('sha256sum --check --status', job)
        self.assertIn('verify-parts', job)
        self.assertIn('evidence-status', job)
        self.assertIn('upload-artifact@v4', job)
        self.assertIn('contents: read', job)

    def test_windows_ci_reproduces_stderr_handling(self):
        job = (ROOT / '.github/workflows/windows-launcher.yml').read_text(encoding='utf-8')
        self.assertIn('windows-2022', job)
        self.assertIn('powershell.exe -NoProfile', job)
        self.assertIn('-UnitOnly', job)
        self.assertIn("python-version: ['3.11', '3.13']", job)

    def test_local_and_ci_evidence_stays_out_of_git(self):
        ignored = (ROOT / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('reports/latest/', ignored)
        self.assertIn('reports/ci/', ignored)
        self.assertIn('input_sources_private/', ignored)


if __name__ == '__main__':
    unittest.main()
