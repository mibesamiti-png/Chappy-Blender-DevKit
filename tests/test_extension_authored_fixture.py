"""R19 bounded authored fixture packaging regression."""
import ast
import io
from pathlib import Path
import tempfile
import tomllib
import unittest
from zipfile import ZipFile

from cbdk.extension_authored_fixture import (FIXTURE_ID, build_authored_fixture_bytes,
                                             write_authored_fixture)


class AuthoredFixtureTests(unittest.TestCase):
    def test_fixed_inventory_determinism_and_manifest(self):
        first = build_authored_fixture_bytes()
        self.assertEqual(first, build_authored_fixture_bytes())
        with ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(len(archive.namelist()), 8)
            self.assertEqual(set(archive.namelist()), {
                "__init__.py", "features/__init__.py", "helpers/__init__.py",
                "features/mesh_bounds.py", "features/mesh_center.py",
                "helpers/context.py", "helpers/measure.py", "blender_manifest.toml"})
            self.assertEqual(tomllib.loads(archive.read("blender_manifest.toml").decode())["id"], FIXTURE_ID)
            tree = ast.parse(archive.read("__init__.py"))
            self.assertFalse(any(isinstance(n, ast.Name) and n.id == "bl_info"
                                 for n in ast.walk(tree)))

    def test_fresh_output_only(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "fixture.zip"
            report = write_authored_fixture(target)
            before = target.read_bytes()
            self.assertFalse(report["release_authorized"])
            self.assertFalse(report["install_authorized"])
            with self.assertRaises(FileExistsError):
                write_authored_fixture(target)
            self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
