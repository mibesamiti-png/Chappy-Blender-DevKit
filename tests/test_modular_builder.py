"""Regression tests for CBDK schema-2 modular Blender preview recipes."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cbdk.__main__ import main
from cbdk.addon_builder import ROOT, build_addon
from cbdk.modular_builder import FEATURES, PACKAGE_ID


class ModularBuilderTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        sources = [
            'catalog/authored_parts.json', 'catalog/addon_features.json',
            'catalog/ui_layouts.json', 'parts/blender/context.py',
            'parts/blender/edit_mesh.py', 'parts/blender/measure.py',
            'parts/blender/modifiers.py', 'parts/blender/edit_transform.py',
            'parts/blender/edit_audit.py',
            'templates/modular_preview/__init__.py',
            'templates/modular_preview/features/object_selection.py',
            'templates/modular_preview/features/edit_selection.py',
            'templates/modular_preview/features/mesh_bounds.py',
            'templates/modular_preview/features/modifier_summary.py',
            'templates/modular_preview/features/vertex_nudge.py',
        ]
        for path in sources:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        self.recipe = self.root / 'recipe.json'
        self.output = self.root / 'preview.zip'
        self.data = {
            'schema_version': 2, 'template': 'modular_preview',
            'package_id': PACKAGE_ID, 'display_name': 'CBDK Modular Preview',
            'features': ['object_selection', 'edit_selection'],
            'purpose': 'local_development_preview',
        }
        self.save_recipe()

    def save_recipe(self):
        self.recipe.write_text(json.dumps(self.data, ensure_ascii=False), encoding='utf-8')

    def build(self, *, opt_in=True):
        return build_addon(self.recipe, self.output, preview_unapproved=opt_in, root=self.root)

    def test_combined_dependency_closure(self):
        result = self.build()
        self.assertEqual(result['features'], ['edit_selection', 'object_selection'])
        self.assertEqual(result['part_ids'], ['BLCTX-001', 'BLCTX-002', 'BME-001'])
        with ZipFile(self.output) as archive:
            names = set(archive.namelist())
            self.assertEqual(names, {f'{PACKAGE_ID}/{p}' for p in (
                '__init__.py', 'README.txt', 'CBDK_BUILD_INFO.json',
                'helpers/__init__.py', 'helpers/context.py', 'helpers/edit_mesh.py',
                'features/__init__.py', 'features/object_selection.py',
                'features/edit_selection.py',
            )})
            provenance = json.loads(archive.read(f'{PACKAGE_ID}/CBDK_BUILD_INFO.json'))
            self.assertEqual(provenance['part_ids'], result['part_ids'])
            self.assertFalse(provenance['approved'])
            self.assertFalse(provenance['redistribution_cleared'])
            self.assertFalse(provenance['blender_runtime_verified_for_this_build'])

    def test_object_only_omits_edit_dependency(self):
        self.data['features'] = ['object_selection']
        self.save_recipe()
        report = self.build()
        self.assertEqual(report['part_ids'], ['BLCTX-001', 'BLCTX-002'])
        with ZipFile(self.output) as z:
            files = z.namelist()
            self.assertFalse(any(x.endswith('/helpers/edit_mesh.py') for x in files))
            self.assertFalse(any(x.endswith('/features/edit_selection.py') for x in files))

    def test_edit_only_omits_object_feature(self):
        self.data['features'] = ['edit_selection']
        self.save_recipe()
        report = self.build()
        self.assertEqual(report['part_ids'], ['BLCTX-001', 'BME-001'])
        with ZipFile(self.output) as z:
            self.assertIn(f'{PACKAGE_ID}/helpers/edit_mesh.py', z.namelist())
            self.assertNotIn(f'{PACKAGE_ID}/features/object_selection.py', z.namelist())

    def test_geometry_only_selects_exact_two_new_helpers(self):
        self.data['features'] = ['mesh_bounds', 'modifier_summary']
        self.save_recipe()
        report = self.build()
        self.assertEqual(report['part_ids'], ['BLCTX-001', 'BLGEO-001', 'BLMOD-001'])
        with ZipFile(self.output) as z:
            names = z.namelist()
            self.assertIn(f'{PACKAGE_ID}/helpers/measure.py', names)
            self.assertIn(f'{PACKAGE_ID}/helpers/modifiers.py', names)
            self.assertNotIn(f'{PACKAGE_ID}/helpers/edit_mesh.py', names)
            self.assertNotIn(f'{PACKAGE_ID}/features/object_selection.py', names)

    def test_all_tools_recipe_includes_five_parts(self):
        self.data['features'] = ['object_selection', 'edit_selection',
                                 'mesh_bounds', 'modifier_summary', 'vertex_nudge']
        self.save_recipe()
        result = self.build()
        self.assertEqual(result['part_ids'], [
            'BLCTX-001', 'BLCTX-002', 'BLGEO-001', 'BLMOD-001', 'BME-001', 'BME-002', 'BME-003'
        ])
        with ZipFile(self.output) as z:
            self.assertIn(f'{PACKAGE_ID}/helpers/measure.py', z.namelist())
            self.assertIn(f'{PACKAGE_ID}/helpers/modifiers.py', z.namelist())
            self.assertEqual(len(json.loads(z.read(f'{PACKAGE_ID}/CBDK_BUILD_INFO.json'))['features']), 5)

    def test_ui_sections_are_safe_and_subset_only(self):
        import ast
        self.build()
        with ZipFile(self.output) as archive:
            source = archive.read(f'{PACKAGE_ID}/__init__.py').decode('utf-8')
            manifest = json.loads(archive.read(f'{PACKAGE_ID}/CBDK_BUILD_INFO.json'))
        tree = ast.parse(source)
        section_assignments = [node.value for node in tree.body
                               if isinstance(node, ast.Assign)
                               and any(isinstance(t, ast.Name) and t.id == '_UI_SECTIONS'
                                       for t in node.targets)]
        self.assertEqual(len(section_assignments), 1)
        layout = ast.literal_eval(section_assignments[0])
        self.assertEqual(layout, (
            ('Inspection', (('object_selection', 'Selected Meshes'),)),
            ('Edit Mode', (('edit_selection', 'Selection Counts'),)),
        ))
        self.assertEqual(manifest['ui_section_titles'], ['Inspection', 'Edit Mode'])
        self.assertNotIn('__CBDK_UI_SECTIONS__', source)
        self.assertEqual(manifest['ui_options']['section_styles'][0]['visible_in'], 'always')

    def test_invalid_declared_bounds_stop_before_zip_creation(self):
        path = self.root / 'catalog/ui_layouts.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['sections'][1]['controls'][1]['parameters'] = {
            'offset': {'default': [0, 0, 2], 'min': -1, 'max': 1}}
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'outside declared'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_template_marker_text_in_labels_is_an_inert_literal(self):
        import ast
        self.data['display_name'] = 'CBDK __CBDK_FEATURE_IDS__'
        self.save_recipe()
        path = self.root / 'catalog/ui_layouts.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['sections'][0]['controls'][0]['label'] = '__CBDK_UI_OPTIONS__'
        path.write_text(json.dumps(data), encoding='utf-8')
        self.build()
        with ZipFile(self.output) as archive:
            tree = ast.parse(archive.read(f'{PACKAGE_ID}/__init__.py'))
        literals = {node.targets[0].id: node.value for node in tree.body
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
        self.assertEqual(ast.literal_eval(literals['bl_info'])['name'], self.data['display_name'])
        self.assertEqual(ast.literal_eval(literals['_UI_SECTIONS'])[0][1][0][1], '__CBDK_UI_OPTIONS__')

    def test_generated_panel_has_guarded_operator_arguments(self):
        self.data['features'] = ['vertex_nudge']
        self.save_recipe()
        self.build()
        with ZipFile(self.output) as archive:
            source = archive.read(f'{PACKAGE_ID}/__init__.py').decode('utf-8')
        import ast
        tree = ast.parse(source)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertIn('_EDIT_MODE_FEATURES', names)
        self.assertIn('cbdk_modular_nudge_offset', source)
        self.assertIn('button_row.enabled', source)
        self.assertIn('button.offset', source)

    def test_feature_order_does_not_affect_zip(self):
        self.build()
        first = self.output.read_bytes()
        self.data['features'].reverse()
        self.save_recipe()
        other = self.root / 'second.zip'
        build_addon(self.recipe, other, preview_unapproved=True, root=self.root)
        self.assertEqual(first, other.read_bytes())

    def test_recipe_title_is_python_literal_and_not_code(self):
        self.data['display_name'] = 'CBDK "Quote"; __import__("os").system("echo danger")'
        self.save_recipe()
        self.build()
        with ZipFile(self.output) as z:
            source = z.read(f'{PACKAGE_ID}/__init__.py').decode('utf-8')
        # Entire label appears within a Python string literal and compiles safely.
        import ast
        tree = ast.parse(source)
        metadata = tree.body[1].value  # bl_info assignment follows module docstring
        self.assertEqual(ast.literal_eval(metadata)['name'], self.data['display_name'])

    def test_opt_in_required(self):
        with self.assertRaisesRegex(ValueError, 'preview-unapproved'):
            self.build(opt_in=False)
        self.assertFalse(self.output.exists())

    def test_invalid_features_are_rejected(self):
        for features in ([], ['not_registered'], ['object_selection'] * 2,
                         ['object_selection', '../../private.py'],
                         ['object_selection', {}], ['object_selection', 'edit_selection', 'object_selection']):
            with self.subTest(features=features):
                self.data['features'] = features
                self.save_recipe()
                with self.assertRaises(ValueError):
                    self.build()
        self.assertFalse(self.output.exists())

    def test_unknown_recipe_fields_rejected(self):
        self.data['execute_source'] = 'input_sources_private/anything.py'
        self.save_recipe()
        with self.assertRaises(ValueError):
            self.build()

    def test_wrong_template_and_package_rejected(self):
        for key, value in [('template','../../outside'), ('package_id','unexpected'),
                           ('purpose','general_release')]:
            with self.subTest(key=key):
                changed = dict(self.data, **{key:value})
                self.recipe.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.build()

    def test_name_controls_rejected(self):
        for label in ('x', 'x\nexec("bad")', '\x00bad', 'x' * 73, 9):
            with self.subTest(label=label):
                self.data['display_name'] = label
                self.save_recipe()
                with self.assertRaises(ValueError):
                    self.build()

    def test_unexpected_catalog_source_rejected(self):
        path = self.root / 'catalog/authored_parts.json'
        data = json.loads(path.read_text())
        data['parts'][0]['source'] = 'input_sources_private/foo.py'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse(self.output.exists())

    def test_missing_template_is_rejected(self):
        (self.root / 'templates/modular_preview/features/edit_selection.py').unlink()
        with self.assertRaises(ValueError):
            self.build()

    def test_missing_part_is_rejected(self):
        path = self.root / 'catalog/authored_parts.json'
        data = json.loads(path.read_text())
        data['parts'] = [p for p in data['parts'] if p['part_id'] != 'BLCTX-002']
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.build()

    def test_output_is_not_overwritten(self):
        self.output.write_bytes(b'preserve')
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(self.output.read_bytes(), b'preserve')

    def test_symlink_to_external_code_refused(self):
        path = self.root / 'templates/modular_preview/features/edit_selection.py'
        original = self.root / 'original.py'
        path.rename(original)
        try:
            path.symlink_to(original)
        except OSError:
            self.skipTest('Symlink unavailable on this OS')
        with self.assertRaises(ValueError):
            self.build()

    def test_cli_three_recipe_examples(self):
        for recipe_name in ('modular_objects', 'modular_edit', 'modular_combined', 'modular_geometry', 'modular_nudge', 'modular_all'):
            with self.subTest(recipe_name=recipe_name):
                output = self.root / f'{recipe_name}.zip'
                rc = main(['build-addon', '--recipe', str(ROOT / f'recipes/{recipe_name}.json'),
                           '--preview-unapproved', '--output', str(output)])
                self.assertEqual(rc, 0)
                self.assertTrue(output.is_file())

    def test_legacy_v1_recipe_still_supported(self):
        output = self.root / 'legacy.zip'
        rc = main(['build-addon', '--recipe', str(ROOT / 'recipes/mesh_inspector.json'),
                   '--preview-unapproved', '--output', str(output)])
        self.assertEqual(rc, 0)
        with ZipFile(output) as z:
            self.assertIn('cbdk_mesh_inspector_preview/__init__.py', z.namelist())
            self.assertNotIn('cbdk_modular_preview/__init__.py', z.namelist())


if __name__ == '__main__':
    unittest.main()
