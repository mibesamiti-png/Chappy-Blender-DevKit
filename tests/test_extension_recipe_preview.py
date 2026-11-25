"""R23 independent fixed-case inventories and rejection boundaries."""
import hashlib
import io
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from cbdk.extension_authored_fixture import FIXTURE_ID, _recipe, build_authored_fixture_bytes
from cbdk.extension_recipe_preview import (ci_recipe, build_recipe_extension_bytes,
                                           write_recipe_extension)
from cbdk.modular_builder import build_modular

ROOT = Path(__file__).resolve().parents[1]


class RecipeExtensionTests(unittest.TestCase):
    def test_two_distinct_inventories_and_determinism(self):
        common = {"__init__.py", "features/__init__.py", "helpers/__init__.py",
                  "helpers/context.py", "blender_manifest.toml"}
        expected = {
            "read": common | {"features/mesh_bounds.py", "features/mesh_center.py", "helpers/measure.py"},
            "edit": common | {"features/edit_selection.py", "features/vertex_nudge.py",
                              "helpers/edit_mesh.py", "helpers/edit_transform.py", "helpers/edit_audit.py"},
        }
        outputs = {}
        for case, names in expected.items():
            with self.subTest(case=case):
                recipe = ci_recipe(case)
                first = build_recipe_extension_bytes(recipe, preview_unapproved=True)
                self.assertEqual(first, build_recipe_extension_bytes(recipe, preview_unapproved=True))
                with ZipFile(io.BytesIO(first)) as z:
                    self.assertEqual(set(z.namelist()), names)
                    self.assertEqual(len(z.infolist()), len(names))
                    self.assertEqual(tomllib.loads(z.read("blender_manifest.toml").decode())["id"], FIXTURE_ID)
                outputs[case] = first
        self.assertNotEqual(outputs["read"], outputs["edit"])

    def test_r19_fixed_bytes_and_inline_contract_preserved(self):
        self.assertEqual(build_recipe_extension_bytes(_recipe(), preview_unapproved=True),
                         build_authored_fixture_bytes())

    def test_explicit_opt_in_and_invalid_input_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "local.zip"
            recipe = ci_recipe("read")
            with self.assertRaises(ValueError):
                write_recipe_extension(recipe, target)
            for bad in ({**recipe, "source": "/tmp/not-authorized.py"},
                        {**recipe, "features": ["unknown"]},
                        {**recipe, "features": ["mesh_bounds", "mesh_bounds"]},
                        {**recipe, "metadata": {"license": "arbitrary"}},
                        {**recipe, "display_name": float("nan")},
                        {**recipe, "ui_layout": {"raw_code": "import os"}}):
                with self.subTest(keys=tuple(bad)):
                    with self.assertRaises(ValueError):
                        write_recipe_extension(bad, target, preview_unapproved=True)
                    self.assertFalse(target.exists())

    def test_original_preview_digest_and_fresh_output(self):
        with tempfile.TemporaryDirectory() as folder:
            original, target = [Path(folder) / name for name in ("original.zip", "local.zip")]
            recipe = ci_recipe("edit")
            build_modular(recipe, original, root=ROOT, preview_unapproved=True)
            before = original.read_bytes()
            report = write_recipe_extension(recipe, target, preview_unapproved=True)
            self.assertEqual(report["original_preview_sha256"], hashlib.sha256(before).hexdigest())
            self.assertEqual(original.read_bytes(), before)
            for flag in ("approved", "release_authorized", "install_authorized", "real_component_license_chosen"):
                self.assertIs(report[flag], False)
            prior = target.read_bytes()
            with self.assertRaises(FileExistsError):
                write_recipe_extension(recipe, target, preview_unapproved=True)
            self.assertEqual(target.read_bytes(), prior)


if __name__ == "__main__":
    unittest.main()
