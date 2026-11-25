"""Independent R24 closure and fixed-manifest compatibility gates."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from cbdk.extension_recipe_preview import build_recipe_extension_bytes, write_recipe_extension
from cbdk.modular_builder import PACKAGE_ID, build_modular, plan_modular_recipe
from extension_r24_dependency_fixture import (CATALOG, ROOT, ORDER, PARTS, MEMBERS,
                                                dependency_catalog, dependency_recipe)


class DependencyExtensionTests(unittest.TestCase):
    def test_closure_members_and_requested_distinction(self):
        recipe = dependency_recipe()
        with tempfile.TemporaryDirectory() as folder, dependency_catalog() as catalog_sha:
            root = Path(folder)
            legacy, target = root / "legacy.zip", root / "extension.zip"
            plan = plan_modular_recipe(recipe, root=ROOT, include_ui=True)
            self.assertEqual(plan["requested_features"], ["vertex_nudge"])
            self.assertEqual(tuple(plan["ordered_features"]), ORDER)
            self.assertEqual(tuple(plan["part_ids"]), PARTS)
            self.assertEqual(set(plan["dependency_features_added"]), set(ORDER[:-1]))
            build_modular(recipe, legacy, root=ROOT, preview_unapproved=True)
            original = legacy.read_bytes()
            with ZipFile(legacy) as z:
                info = json.loads(z.read(PACKAGE_ID + "/CBDK_BUILD_INFO.json"))
                self.assertEqual(info["requested_features"], ["vertex_nudge"])
                self.assertEqual(tuple(info["features"]), ORDER)
                self.assertEqual(tuple(info["part_ids"]), PARTS)
            report = write_recipe_extension(recipe, target, preview_unapproved=True)
            self.assertEqual(report["original_preview_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(legacy.read_bytes(), original)
            self.assertEqual(report["feature_count"], 4)
            for flag in ("approved", "release_authorized", "install_authorized"):
                self.assertIs(report[flag], False)
            blob = target.read_bytes()
            self.assertEqual(blob, build_recipe_extension_bytes(recipe, preview_unapproved=True))
            with ZipFile(io.BytesIO(blob)) as z:
                self.assertEqual(set(z.namelist()), MEMBERS)
                self.assertEqual(len(z.infolist()), len(MEMBERS))
                tree = ast.parse(z.read("__init__.py"))
                ids = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "_FEATURE_IDS"]
                self.assertEqual(ids, [ORDER])
                fields = tomllib.loads(z.read("blender_manifest.toml").decode())
                self.assertEqual(fields["blender_version_min"], "4.4.0")
                self.assertNotIn("blender_version_max", fields)
            with self.assertRaises(FileExistsError):
                write_recipe_extension(recipe, target, preview_unapproved=True)
            self.assertEqual(target.read_bytes(), blob)
            self.assertEqual(hashlib.sha256(CATALOG.read_bytes()).hexdigest(), catalog_sha)

    def test_narrow_dependency_ranges_rejected_before_generation(self):
        recipe = dependency_recipe()
        for case, minimum, maximum in (("min", "4.5.0", None), ("max", "4.4.0", "5.2.1")):
            with self.subTest(case=case), dependency_catalog(case), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "extension.zip"
                plan = plan_modular_recipe(recipe, root=ROOT, include_ui=True)
                self.assertEqual((plan["minimum_blender"], plan["maximum_blender"]), (minimum, maximum))
                # A narrow but otherwise valid plan must not produce a broader manifest.
                with self.assertRaisesRegex(ValueError, "compatibility"):
                    write_recipe_extension(recipe, target, preview_unapproved=True)
                self.assertFalse(target.exists())

    def test_invalid_graph_rejected_without_output(self):
        for case in ("cycle", "missing", "disjoint"):
            with self.subTest(case=case), dependency_catalog(case), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "extension.zip"
                with patch("cbdk.extension_recipe_preview.build_modular",
                           side_effect=AssertionError("invalid graph reached builder")):
                    with self.assertRaises(ValueError):
                        write_recipe_extension(dependency_recipe(), target, preview_unapproved=True)
                self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
