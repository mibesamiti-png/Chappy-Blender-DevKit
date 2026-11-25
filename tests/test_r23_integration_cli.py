"""A-owned CLI and combined authored recipe regression; no bpy execution."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from cbdk.__main__ import main
from cbdk.extension_recipe_preview import build_recipe_extension_bytes
from test_ui_recipe_r17 import make_r23_recipe


class R23IntegrationCLI(unittest.TestCase):
    def test_combined_cli_exact_bytes_and_fresh_output(self):
        recipe = make_r23_recipe("grouped")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "recipe.json", root / "preview.zip"
            raw = json.dumps(recipe).encode()
            source.write_bytes(raw)
            args = ["build-extension-preview", "--recipe", str(source), "--output", str(target)]
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(args)
            self.assertEqual(exc.exception.code, 2)
            self.assertFalse(target.exists())
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(args + ["--preview-unapproved"]), 0)
            report = json.loads(out.getvalue())
            self.assertEqual(report["feature_count"], 4)
            for flag in ("approved", "install_authorized", "release_authorized", "real_component_license_chosen"):
                self.assertIs(report[flag], False)
            self.assertTrue(report["preview_only"])
            self.assertTrue(report["original_preview_unchanged"])
            blob = target.read_bytes()
            self.assertEqual(blob, build_recipe_extension_bytes(recipe, preview_unapproved=True))
            with ZipFile(target) as z:
                self.assertIn("blender_manifest.toml", z.namelist())
                self.assertIn("features/vertex_nudge.py", z.namelist())
                self.assertIn("features/mesh_center.py", z.namelist())
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(args + ["--preview-unapproved"])
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(target.read_bytes(), blob)
            self.assertEqual(source.read_bytes(), raw)

    def test_duplicate_oversize_and_invalid_recipe_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "recipe.json", root / "preview.zip"
            for raw in (b'{"features":[],"features":[]}', b" " * 32769,
                        b'{"x":NaN}', b'{"schema_version":2,"arbitrary_python":"print(1)"}'):
                source.write_bytes(raw)
                args = ["build-extension-preview", "--recipe", str(source),
                        "--output", str(target), "--preview-unapproved"]
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                    main(args)
                self.assertEqual(exc.exception.code, 2)
                self.assertFalse(target.exists())
                self.assertEqual(source.read_bytes(), raw)
