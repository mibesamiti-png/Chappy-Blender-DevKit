import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.evidence import (
    PART_CASES, SCRIPT_PATH, check_evidence_freshness, save_evidence,
    validate_parts_payload, verify_authored_parts,
)


def good_payload():
    return {
        'schema_version': 1, 'suite': 'parts', 'blender': '4.5.0',
        'part_checks': {key: list(cases) for key, (_, cases) in PART_CASES.items()},
    }


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in {SCRIPT_PATH, *(src for src, _ in PART_CASES.values())}:
            f = self.root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('trusted-fake-fixture', encoding='utf-8')

    def run_report(self, *, verified=True, message=None):
        return {
            'status': 'passed' if verified else 'failed',
            'verified': verified,
            'message': message if message is not None else json.dumps(good_payload()),
        }

    def test_complete_payload(self):
        self.assertEqual(validate_parts_payload(good_payload())['blender'], '4.5.0')

    def test_rejects_missing_or_extra_part_id(self):
        bad = good_payload()
        del bad['part_checks']['BLCTX-002']
        with self.assertRaises(ValueError):
            validate_parts_payload(bad)
        bad = good_payload()
        bad['part_checks']['OTHER-003'] = []
        with self.assertRaises(ValueError):
            validate_parts_payload(bad)

    def test_rejects_partial_duplicate_and_fake_case(self):
        for checks in (['active_mesh_object'],
                       ['active_mesh_object', 'wrong_mode_rejected', 'wrong_mode_rejected'],
                       ['active_mesh_object', 'bogus']):
            bad = good_payload()
            bad['part_checks']['BLCTX-001'] = checks
            with self.assertRaises(ValueError):
                validate_parts_payload(bad)

    def test_rejects_wrong_schema_and_missing_version(self):
        for change in ({'schema_version': 2}, {'suite': 'basic'}, {'blender': ''}):
            bad = good_payload()
            bad.update(change)
            with self.assertRaises(ValueError):
                validate_parts_payload(bad)

    @patch('cbdk.evidence.run_smoke')
    def test_run_records_per_part_smoke_not_approval(self, runner):
        runner.return_value = self.run_report()
        report = verify_authored_parts('blender', root=self.root)
        self.assertEqual(report['run_status'], 'passed')
        self.assertEqual(set(report['parts']), set(PART_CASES))
        self.assertEqual(report['blender_version'], '4.5.0')
        self.assertIs(report['approved'], False)
        self.assertTrue(all(part['status'] == 'blender_smoke_passed' and
                            part['approved'] is False for part in report['parts'].values()))
        runner.assert_called_once_with('blender', timeout=90, suite='parts')
        self.assertTrue(check_evidence_freshness(report, root=self.root)['fresh'])

    @patch('cbdk.evidence.run_smoke')
    def test_stale_code_invalidates_report(self, runner):
        runner.return_value = self.run_report()
        report = verify_authored_parts('blender', root=self.root)
        (self.root / 'parts/blender/edit_mesh.py').write_text('changed code')
        result = check_evidence_freshness(report, root=self.root)
        self.assertFalse(result['fresh'])
        self.assertTrue(any('Code changed' in msg for msg in result['errors']))

    @patch('cbdk.evidence.run_smoke')
    def test_failed_subprocess_never_creates_passed_parts(self, runner):
        runner.return_value = self.run_report(verified=False)
        report = verify_authored_parts('blender', root=self.root)
        self.assertEqual(report['run_status'], 'failed')
        self.assertFalse(report['parts'])
        self.assertFalse(check_evidence_freshness(report, root=self.root)['fresh'])

    @patch('cbdk.evidence.run_smoke')
    def test_invalid_marker_never_creates_passed_parts(self, runner):
        runner.return_value = self.run_report(message='garbage output')
        report = verify_authored_parts('blender', root=self.root)
        self.assertEqual(report['run_status'], 'failed')
        self.assertFalse(report['parts'])

    @patch('cbdk.evidence.run_smoke')
    def test_incomplete_case_never_creates_passed_parts(self, runner):
        partial = good_payload()
        partial['part_checks']['BME-001'].pop()
        runner.return_value = self.run_report(message=json.dumps(partial))
        report = verify_authored_parts('blender', root=self.root)
        self.assertEqual(report['run_status'], 'failed')
        self.assertFalse(report['parts'])

    @patch('cbdk.evidence.run_smoke')
    def test_record_is_atomic_and_not_approved(self, runner):
        runner.return_value = self.run_report()
        report = verify_authored_parts('blender', root=self.root)
        out = self.root / 'reports/latest/parts_evidence.json'
        save_evidence(out, report)
        saved = json.loads(out.read_text())
        self.assertEqual(saved['source_hashes_sha256'], report['source_hashes_sha256'])
        self.assertFalse(saved['approved'])

    @patch('cbdk.evidence.run_smoke')
    def test_cli_with_failed_suite_returns_error(self, runner):
        runner.return_value = self.run_report(verified=False)
        target = self.root / 'failed.json'
        # CLI uses real project hashes by default.
        self.assertEqual(main(['verify-parts', '--blender', 'missing_blender', '--output', str(target)]), 1)
        self.assertEqual(json.loads(target.read_text())['run_status'], 'failed')
        self.assertEqual(main(['evidence-status', '--evidence', str(target)]), 1)

    @patch('cbdk.evidence.run_smoke')
    def test_cli_success_and_local_freshness(self, runner):
        runner.return_value = self.run_report()
        target = self.root / 'passed.json'
        self.assertEqual(main(['verify-parts', '--blender', 'blender', '--output', str(target)]), 0)
        self.assertEqual(main(['evidence-status', '--evidence', str(target)]), 0)


if __name__ == '__main__':
    unittest.main()
