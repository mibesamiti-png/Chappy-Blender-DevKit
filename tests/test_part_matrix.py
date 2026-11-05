"""Review-only runtime matrix regression tests. No Blender process required."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.evidence import PART_CASES, SCRIPT_PATH, verify_authored_parts
from cbdk.part_matrix import (
    MAX_EVIDENCE_BYTES, evidence_paths, render_matrix_markdown,
    summarize_parts, write_matrix,
)


class PartMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for source in {SCRIPT_PATH, *(src for src, _ in PART_CASES.values())}:
            f = self.root / source
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('trusted-test-fixture', encoding='utf-8')
        self.catalog = {'schema_version': 1, 'parts': [
            {'part_id': key, 'name': key, 'source': src, 'status': 'unit_tested',
             'approved': False, 'license_review': 'pending'}
            for key, (src, _checks) in PART_CASES.items()
        ]}

    def save_report(self, name, version='4.4.3'):
        payload = {'schema_version': 1, 'suite': 'parts', 'blender': version,
                   'part_checks': {key: list(checks) for key, (_, checks) in PART_CASES.items()}}
        with patch('cbdk.evidence.run_smoke', return_value={
            'status': 'passed', 'verified': True, 'message': json.dumps(payload),
        }):
            report = verify_authored_parts('blender', root=self.root)
        path = self.root / name
        path.write_text(json.dumps(report), encoding='utf-8')
        return path

    def test_three_version_matrix_and_unapproved(self):
        paths = [self.save_report(f'parts_evidence_{v}.json', version=v)
                 for v in ('5.2.1', '2.92.0', '4.4.3')]
        result = summarize_parts(self.catalog, paths, root=self.root)
        self.assertEqual(result['valid_evidence_count'], 3)
        self.assertEqual(result['invalid_evidence_count'], 0)
        for part in result['parts']:
            self.assertEqual(part['runtime_versions'], ['2.92.0', '4.4.3', '5.2.1'])
            self.assertEqual(part['verification'], 'blender_smoke_passed')
            self.assertFalse(part['approved_by_evidence'])
            self.assertEqual(part['authenticity'], 'not_verified')
        self.assertFalse(result['approved_by_evidence'])

    def test_changed_source_invalidates_evidence_not_catalog(self):
        evidence = self.save_report('parts_evidence.json')
        (self.root / 'parts/blender/context.py').write_text('new source')
        result = summarize_parts(self.catalog, [evidence], root=self.root)
        self.assertEqual(result['valid_evidence_count'], 0)
        self.assertEqual(result['invalid_evidence_count'], 1)
        self.assertEqual(result['parts'][0]['verification'], 'not_recorded')
        self.assertEqual(self.catalog['parts'][0]['status'], 'unit_tested')

    def test_fail_closed_on_modified_result_and_unknown_part(self):
        path = self.save_report('parts_evidence.json')
        data = json.loads(path.read_text())
        data['parts']['UNKNOWN-999'] = data['parts']['BME-001']
        path.write_text(json.dumps(data))
        report = summarize_parts(self.catalog, [path], root=self.root)
        self.assertEqual(report['valid_evidence_count'], 0)
        self.assertEqual(report['invalid_evidence_count'], 1)

    def test_catalog_source_mismatch_refuses_pass(self):
        path = self.save_report('parts_evidence.json')
        self.catalog['parts'][0]['source'] = 'parts/blender/not_same.py'
        report = summarize_parts(self.catalog, [path], root=self.root)
        self.assertEqual(report['valid_evidence_count'], 0)
        self.assertEqual(report['invalid_evidence_count'], 1)

    def test_missing_evidence_is_unverified(self):
        result = summarize_parts(self.catalog, [], root=self.root)
        self.assertFalse(result['has_runtime_evidence'])
        self.assertEqual(result['valid_evidence_count'], 0)
        self.assertTrue(all(x['verification'] == 'not_recorded' for x in result['parts']))

    def test_malformed_json_is_rejected_without_crashing(self):
        path = self.root / 'parts_evidence_bad.json'
        path.write_text('{not json')
        result = summarize_parts(self.catalog, [path], root=self.root)
        self.assertEqual(result['invalid_evidence_count'], 1)
        self.assertEqual(result['valid_evidence_count'], 0)

    def test_exceeds_size_limit_is_rejected(self):
        path = self.root / 'parts_evidence_large.json'
        with path.open('wb') as out:
            out.truncate(MAX_EVIDENCE_BYTES + 1)
        report = summarize_parts(self.catalog, [path], root=self.root)
        self.assertIn('size limit', report['rejected_evidence'][0]['reason'])

    def test_symlink_is_rejected_when_supported(self):
        p = self.save_report('parts_evidence_good.json')
        link = self.root / 'parts_evidence_link.json'
        try:
            link.symlink_to(p)
        except OSError:
            self.skipTest('Creating symlinks is not permitted here')
        report = summarize_parts(self.catalog, [link], root=self.root)
        self.assertEqual(report['invalid_evidence_count'], 1)

    def test_duplicate_evidence_file_only_counts_once(self):
        path = self.save_report('parts_evidence.json')
        report = summarize_parts(self.catalog, [path, path], root=self.root)
        self.assertEqual(report['valid_evidence_count'], 1)

    def test_duplicate_part_id_is_rejected(self):
        self.catalog['parts'].append(dict(self.catalog['parts'][0]))
        with self.assertRaises(ValueError):
            summarize_parts(self.catalog, [], root=self.root)

    def test_discovery_only_matches_parts_evidence(self):
        self.save_report('parts_evidence_Blender_4_4_3.json')
        (self.root / 'registry.json').write_text('{}')
        paths = evidence_paths(self.root)
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].name.startswith('parts_evidence'))

    def test_write_json_and_markdown(self):
        report = summarize_parts(self.catalog, [self.save_report('parts_evidence.json')], root=self.root)
        out = self.root / 'reports' / 'parts_matrix.json'
        write_matrix(out, report)
        self.assertEqual(json.loads(out.read_text())['valid_evidence_count'], 1)
        self.assertIn('4.4.3', render_matrix_markdown(report))

    def test_cli_no_evidence_returns_error_with_file(self):
        catalog = self.root / 'catalog.json'
        catalog.write_text(json.dumps(self.catalog))
        output = self.root / 'status.json'
        self.assertEqual(main(['part-matrix', '--catalog', str(catalog), '--evidence-dir', str(self.root),
                               '--output', str(output)]), 1)
        self.assertFalse(json.loads(output.read_text())['has_runtime_evidence'])

    def test_cli_real_repo_mock_evidence_success(self):
        root = Path(__file__).resolve().parents[1]
        payload = {'schema_version': 1, 'suite': 'parts', 'blender': '4.4.3',
                   'part_checks': {key: list(checks) for key, (_, checks) in PART_CASES.items()}}
        with patch('cbdk.evidence.run_smoke', return_value={
            'status': 'passed', 'verified': True, 'message': json.dumps(payload),
        }):
            report = verify_authored_parts('blender', root=root)
        path = self.root / 'parts_evidence.json'
        path.write_text(json.dumps(report))
        output = self.root / 'matrix.json'
        self.assertEqual(main(['part-matrix', '--catalog', str(root / 'catalog/authored_parts.json'),
                               '--evidence', str(path), '--output', str(output)]), 0)
        self.assertEqual(json.loads(output.read_text())['valid_evidence_count'], 1)


if __name__ == '__main__':
    unittest.main()
