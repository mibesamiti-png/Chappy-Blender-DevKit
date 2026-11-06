from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.package_windows_kit import default_output, project_version


class WindowsKitVersionTests(unittest.TestCase):
    def test_version_and_default_output_follow_pyproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "0.17.0"\n',
                encoding="utf-8",
            )
            self.assertEqual(project_version(root), "0.17.0")
            self.assertEqual(
                default_output(root),
                root / "dist" / "CBDK_v0.17.0_Windows_Blender_DevKit.zip",
            )

    def test_rejects_unsafe_version_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "../bad"\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                project_version(root)


if __name__ == "__main__":
    unittest.main()
