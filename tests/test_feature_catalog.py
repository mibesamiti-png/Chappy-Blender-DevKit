"""Safety/compatibility tests for CBDK's static, allowlisted feature registry."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.addon_builder import ROOT, build_addon
from cbdk.feature_catalog import (
    load_feature_catalog, parse_version, plan_features, validate_feature_catalog,
)


class TrustedFeatureCatalogTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in ('catalog/addon_features.json', 'catalog/authored_parts.json'):
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dest)
        self.source = self.root / 'catalog/addon_features.json'
        self.doc = json.loads(self.source.read_text(encoding='utf-8'))

    def save(self):
        self.source.write_text(json.dumps(self.doc, ensure_ascii=False), encoding='utf-8')

    def feature(self, feature_id):
        return next(item for item in self.doc['features'] if item['id'] == feature_id)

    def test_current_allowlist_has_five_known_features(self):
        catalog = load_feature_catalog(root=self.root)
        self.assertEqual(set(catalog), {'edit_selection', 'object_selection', 'mesh_bounds', 'modifier_summary', 'vertex_nudge'})
        self.assertTrue(all(x['min_blender'] == '4.4.0' for x in catalog.values()))

    def test_object_only_plans_exact_two_parts(self):
        plan = plan_features(['object_selection'], root=self.root)
        self.assertEqual(plan['ordered_features'], ['object_selection'])
        self.assertEqual(plan['part_ids'], ['BLCTX-001', 'BLCTX-002'])
        self.assertEqual(plan['part_sources'], ['parts/blender/context.py'])
        self.assertIsNone(plan['compatible_with_target'])
        self.assertFalse(plan['approved'])

    def test_combined_merges_shared_dependencies(self):
        plan = plan_features(['object_selection', 'edit_selection'], root=self.root)
        self.assertEqual(plan['part_ids'], ['BLCTX-001', 'BLCTX-002', 'BME-001'])
        self.assertEqual(plan['ordered_features'], ['edit_selection', 'object_selection'])
        self.assertEqual(len(plan['part_sources']), 2)

    def test_compatible_blender_4_4_and_5_2(self):
        for ver in ('4.4.3', '4.5.15', '5.2.1'):
            self.assertTrue(plan_features(['edit_selection'], root=self.root,
                                          target_blender=ver)['compatible_with_target'])

    def test_incompatible_older_blender_fails(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            plan_features(['object_selection'], root=self.root, target_blender='2.92.0')

    def test_invalid_version_strings_fail_closed(self):
        for value in ('5', '5.2', '5.2.1-beta', '5.2.01', 'x.y.z', '5.2.1\nmalicious', 5, ''):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_version(value)

    def test_dependency_is_added_transitively(self):
        # Simulates metadata adding a dependency, still limited to known features.
        self.feature('object_selection')['requires_features'] = ['edit_selection']
        self.save()
        plan = plan_features(['object_selection'], root=self.root)
        self.assertEqual(plan['ordered_features'], ['edit_selection', 'object_selection'])
        self.assertEqual(plan['dependency_features_added'], ['edit_selection'])
        self.assertEqual(plan['part_ids'], ['BLCTX-001', 'BLCTX-002', 'BME-001'])

    def test_cycle_is_rejected_even_if_selection_is_one_feature(self):
        self.feature('edit_selection')['requires_features'] = ['object_selection']
        self.feature('object_selection')['requires_features'] = ['edit_selection']
        self.save()
        with self.assertRaisesRegex(ValueError, 'Cycle'):
            plan_features(['object_selection'], root=self.root)

    def test_missing_feature_or_unknown_id_is_rejected(self):
        self.doc['features'].pop()
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)
        self.doc['features'].append({'id': 'untrusted'})
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)

    def test_duplicate_id_rejected(self):
        self.doc['features'][1] = copy.deepcopy(self.doc['features'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_feature_catalog(self.doc)

    def test_catalog_cannot_redirect_to_private_python(self):
        self.doc['features'][0]['source'] = 'input_sources_private/my_addon.py'
        self.save()
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            load_feature_catalog(root=self.root)

    def test_catalog_cannot_change_required_part_ids(self):
        self.doc['features'][0]['required_parts'] = ['BLCTX-001', 'UNKNOWN-999']
        self.save()
        with self.assertRaisesRegex(ValueError, 'dependencies'):
            load_feature_catalog(root=self.root)

    def test_unknown_dependency_rejected(self):
        self.doc['features'][0]['requires_features'] = ['external_code']
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)

    def test_repeated_or_self_dependency_rejected(self):
        self.doc['features'][0]['requires_features'] = ['object_selection', 'object_selection']
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)
        self.doc['features'][0]['requires_features'] = ['edit_selection']
        with self.assertRaisesRegex(ValueError, 'Cycle'):
            validate_feature_catalog(self.doc)

    def test_version_range_conflict_and_invalid_ranges_rejected(self):
        self.doc['features'][0]['max_blender'] = '4.4.5'
        self.feature('object_selection')['min_blender'] = '4.5.0'
        self.save()
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            plan_features(['object_selection', 'edit_selection'], root=self.root)
        self.doc['features'][0]['min_blender'] = '4.7.0'
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)

    def test_part_source_substitution_is_rejected(self):
        catalog_path = self.root / 'catalog/authored_parts.json'
        cat = json.loads(catalog_path.read_text(encoding='utf-8'))
        cat['parts'][0]['source'] = 'input_sources_private/sneaky.py'
        catalog_path.write_text(json.dumps(cat))
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            plan_features(['object_selection'], root=self.root)

    def test_requested_unknown_or_duplicate_rejected(self):
        for requested in ([], ['object_selection', 'object_selection'],
                          ['untrusted'], ['object_selection', {}], 'object_selection'):
            with self.subTest(requested=requested):
                with self.assertRaises(ValueError):
                    plan_features(requested, root=self.root)

    def test_extra_keys_in_catalog_rejected(self):
        self.doc['python_import'] = 'os'
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)
        self.doc.pop('python_import')
        self.doc['features'][0]['exec'] = 'print("bad")'
        with self.assertRaises(ValueError):
            validate_feature_catalog(self.doc)

    def test_cli_feature_list_and_addon_plan(self):
        with tempfile.TemporaryDirectory() as out:
            features = Path(out) / 'feature-list.json'
            planned = Path(out) / 'addon-plan.json'
            self.assertEqual(main(['feature-list', '--output', str(features)]), 0)
            self.assertEqual(main(['addon-plan',
                                   '--recipe', str(ROOT / 'recipes/modular_combined.json'),
                                   '--target-blender', '4.4.3',
                                   '--output', str(planned)]), 0)
            f = json.loads(features.read_text(encoding='utf-8'))
            p = json.loads(planned.read_text(encoding='utf-8'))
            self.assertFalse(f['approved'])
            self.assertEqual(len(f['features']), 5)
            self.assertEqual(p['part_ids'], ['BLCTX-001', 'BLCTX-002', 'BME-001'])
            self.assertEqual(p['target_blender'], '4.4.3')

    def test_cli_incompatible_target_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as out:
            filename = Path(out) / 'no-plan.json'
            with self.assertRaises(SystemExit) as err:
                main(['addon-plan',
                      '--recipe', str(ROOT / 'recipes/modular_combined.json'),
                      '--target-blender', '3.6.0', '--output', str(filename)])
            self.assertEqual(err.exception.code, 2)
            self.assertFalse(filename.exists())

    def test_modular_build_records_target_and_detects_incompatible(self):
        with tempfile.TemporaryDirectory() as out:
            output = Path(out) / 'good.zip'
            result = build_addon(ROOT / 'recipes/modular_combined.json', output,
                                 preview_unapproved=True, target_blender='4.4.3')
            self.assertEqual(result['target_blender'], '4.4.3')
            self.assertTrue(output.is_file())
            bad = Path(out) / 'bad.zip'
            with self.assertRaisesRegex(ValueError, 'outside'):
                build_addon(ROOT / 'recipes/modular_combined.json', bad,
                            preview_unapproved=True, target_blender='3.6.0')
            self.assertFalse(bad.exists())

    def test_legacy_build_target_compatibility(self):
        with tempfile.TemporaryDirectory() as out:
            target = Path(out) / 'legacy.zip'
            with self.assertRaisesRegex(ValueError, '4.4.0'):
                build_addon(ROOT / 'recipes/mesh_inspector.json', target,
                            preview_unapproved=True, target_blender='3.6.0')
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
