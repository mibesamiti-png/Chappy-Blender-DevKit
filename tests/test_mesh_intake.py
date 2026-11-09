"""Regression tests for the offline, non-executing private mesh inventory."""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.mesh_intake import ALLOWED_SUFFIXES, collect_meshes


class MeshIntakeTests(unittest.TestCase):
    def test_format_inventory_and_privacy_labels(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "job").mkdir()
            payload = b"not actually a GLB - inventory must not parse it"
            (root / "job" / "reference.glb").write_bytes(payload)
            (root / "scene.blend").write_bytes(b"not a real blend")
            (root / "material.mtl").write_text("ignored")
            report = collect_meshes(root, role="reference")
            self.assertEqual(report["counts"], {"accepted": 2, "skipped": 1})
            self.assertFalse(report["source_files_executed"])
            self.assertFalse(report["geometry_validated"])
            self.assertEqual([x["relative_path"] for x in report["items"]],
                             ["job/reference.glb", "scene.blend"])
            glb = report["items"][0]
            self.assertEqual(glb["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(glb["role"], "reference")
            self.assertEqual(glb["geometry_validation"], "not_run")
            self.assertEqual(glb["usage_approval"], "pending")
            self.assertEqual(glb["model_id"], "MESH-" + glb["sha256"][:16].upper())

    def test_empty_and_unsupported_files_are_not_accepted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "zero.stl").touch()
            (root / "archive.zip").write_bytes(b"fake ZIP")
            (root / "mesh.OBJ").write_bytes(b"v 0 0 0")
            report = collect_meshes(root)
            self.assertEqual(report["counts"], {"accepted": 1, "skipped": 2})
            self.assertEqual(report["items"][0]["format"], ".obj")
            self.assertEqual(report["items"][0]["role"], "unassigned")

    def test_symlinked_input_is_never_read(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            outside = Path(tmp) / "outside.glb"
            outside.write_bytes(b"confidential")
            try:
                (root / "linked.glb").symlink_to(outside)
                (root / "linked_dir").symlink_to(Path(tmp), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not supported in test environment")
            report = collect_meshes(root)
            self.assertEqual(report["items"], [])
            self.assertGreaterEqual(report["counts"]["skipped"], 1)

    def test_invalid_root_and_role_fail_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                collect_meshes(root, role="publish")
            with self.assertRaises(ValueError):
                collect_meshes(root / "missing")
            self.assertIn(".blend", ALLOWED_SUFFIXES)
            self.assertNotIn(".zip", ALLOWED_SUFFIXES)


if __name__ == "__main__":
    unittest.main()
