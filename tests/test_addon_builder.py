"""Safety tests for the private-only, recipe-driven Blender add-on builder."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.addon_builder import PACKAGE_ID, PART_IDS, ROOT, build_addon


class AddonBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        paths = (
            'catalog/authored_parts.json', 'templates/mesh_inspector/__init__.py',
            'parts/blender/context.py', 'parts/blender/edit_mesh.py',
        )
        for path in paths:
            source = ROOT / path
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        self.recipe = self.root / 'recipe.json'
        self.base_recipe = {
            'schema_version': 1, 'template': 'mesh_inspector',
            'package_id': PACKAGE_ID, 'part_ids': sorted(PART_IDS),
            'purpose': 'local_development_preview',
        }
        self.recipe.write_text(json.dumps(self.base_recipe), encoding='utf-8')
        self.output = self.root / 'dist' / 'mesh_inspector.zip'

    def build(self, **kwargs):
        return build_addon(self.recipe, self.output, root=self.root, **kwargs)

    def test_refuse_unapproved_by_default(self):
        with self.assertRaisesRegex(ValueError, 'preview-unapproved'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_generates_valid_blender_addon_package(self):
        report = self.build(preview_unapproved=True)
        self.assertEqual(report['part_ids'], sorted(PART_IDS))
        self.assertIs(report['preview_only'], True)
        with ZipFile(self.output) as archive:
            names = set(archive.namelist())
            expected = {
                f'{PACKAGE_ID}/__init__.py', f'{PACKAGE_ID}/helpers/__init__.py',
                f'{PACKAGE_ID}/helpers/context.py', f'{PACKAGE_ID}/helpers/edit_mesh.py',
                f'{PACKAGE_ID}/CBDK_BUILD_INFO.json', f'{PACKAGE_ID}/README.txt',
            }
            self.assertEqual(names, expected)
            provenance = json.loads(archive.read(f'{PACKAGE_ID}/CBDK_BUILD_INFO.json'))
            self.assertFalse(provenance['redistribution_cleared'])
            self.assertFalse(provenance['approved'])
            self.assertFalse(provenance['blender_runtime_verified_for_this_build'])
            self.assertEqual(len(provenance['parts']), 3)
            template = archive.read(f'{PACKAGE_ID}/__init__.py').decode()
            self.assertIn('def register():', template)
            self.assertIn('def unregister():', template)
            self.assertIn('VIEW3D_PT_cbdk_mesh_inspector', template)

    def test_repeat_build_is_byte_identical(self):
        self.build(preview_unapproved=True)
        first = self.output.read_bytes()
        alternate = self.root / 'alternate.zip'
        build_addon(self.recipe, alternate, preview_unapproved=True, root=self.root)
        self.assertEqual(first, alternate.read_bytes())

    def test_refuse_overwrite(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_bytes(b'keep-original')
        with self.assertRaises(FileExistsError):
            self.build(preview_unapproved=True)
        self.assertEqual(self.output.read_bytes(), b'keep-original')

    def test_refuse_extra_or_unknown_part_id(self):
        self.base_recipe['part_ids'].append('UNTRUSTED-999')
        self.recipe.write_text(json.dumps(self.base_recipe))
        with self.assertRaises(ValueError):
            self.build(preview_unapproved=True)

    def test_refuse_duplicate_or_wrong_type_part_id(self):
        for ids in ([sorted(PART_IDS)[0]] * 3, ['BLCTX-001', {}, 'BME-001']):
            with self.subTest(ids=ids):
                self.base_recipe['part_ids'] = ids
                self.recipe.write_text(json.dumps(self.base_recipe))
                with self.assertRaises(ValueError):
                    self.build(preview_unapproved=True)
        self.assertFalse(self.output.exists())

    def test_refuse_extra_recipe_metadata(self):
        self.base_recipe['python_script'] = '../../user_source.py'
        self.recipe.write_text(json.dumps(self.base_recipe))
        with self.assertRaises(ValueError):
            self.build(preview_unapproved=True)

    def test_refuse_catalog_source_substitution(self):
        path = self.root / 'catalog/authored_parts.json'
        cat = json.loads(path.read_text())
        cat['parts'][0]['source'] = 'input_sources_private/private.py'
        path.write_text(json.dumps(cat))
        with self.assertRaises(ValueError):
            self.build(preview_unapproved=True)
        self.assertFalse(self.output.exists())

    def test_refuse_catalog_duplicate_ids(self):
        path = self.root / 'catalog/authored_parts.json'
        cat = json.loads(path.read_text())
        cat['parts'].append(cat['parts'][0])
        path.write_text(json.dumps(cat))
        with self.assertRaises(ValueError):
            self.build(preview_unapproved=True)

    def test_refuse_symlinked_authored_source(self):
        path = self.root / 'parts/blender/context.py'
        another = self.root / 'source_backup.py'
        path.replace(another)
        try:
            path.symlink_to(another)
        except OSError:
            self.skipTest('Symlink creation not permitted')
        with self.assertRaises(ValueError):
            self.build(preview_unapproved=True)

    def test_source_hashes_change_when_source_changes(self):
        self.build(preview_unapproved=True)
        with ZipFile(self.output) as archive:
            orig = json.loads(archive.read(f'{PACKAGE_ID}/CBDK_BUILD_INFO.json'))
        source = self.root / 'parts/blender/context.py'
        source.write_text(source.read_text() + '\n# altered test source\n')
        second = self.root / 'changed.zip'
        build_addon(self.recipe, second, preview_unapproved=True, root=self.root)
        with ZipFile(second) as archive:
            new = json.loads(archive.read(f'{PACKAGE_ID}/CBDK_BUILD_INFO.json'))
        self.assertNotEqual(orig['files_sha256']['helpers/context.py'], new['files_sha256']['helpers/context.py'])

    def test_invalid_recipe_json_refused(self):
        self.recipe.write_text('{BROKEN')
        with self.assertRaises(json.JSONDecodeError):
            self.build(preview_unapproved=True)

    def test_cli_refuses_unapproved_without_opt_in(self):
        # argparse exits with SystemExit(2) on a deliberately blocked build.
        with self.assertRaises(SystemExit) as result:
            main(['build-addon', '--recipe', str(ROOT / 'recipes/mesh_inspector.json'),
                  '--output', str(self.output)])
        self.assertEqual(result.exception.code, 2)
        self.assertFalse(self.output.exists())

    def test_cli_opt_in_success(self):
        self.assertEqual(main(['build-addon', '--recipe', str(ROOT / 'recipes/mesh_inspector.json'),
                               '--preview-unapproved', '--output', str(self.output)]), 0)
        self.assertTrue(self.output.is_file())


if __name__ == '__main__':
    unittest.main()
