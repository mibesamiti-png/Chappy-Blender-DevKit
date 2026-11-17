"""Regression tests for the offline, non-executing private mesh inventory."""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.mesh_intake import ALLOWED_SUFFIXES, ASSET_STATES, IMAGE_SUFFIXES, collect_meshes


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
            self.assertEqual(glb["asset_kind"], "mesh")
            self.assertEqual(glb["asset_id"], glb["model_id"])
            self.assertEqual(glb["asset_state"], "work_in_progress")
            self.assertEqual(glb["state_basis"], "default_unfinished")
            self.assertEqual(glb["reference_truth"], "not_established")
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

    def test_images_are_inventoried_as_wip_not_perfect_references(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "draft.PNG").write_bytes(b"work in progress image")
            (root / "viewport.JPEG").write_bytes(b"not a real jpeg")
            (root / "notes.webp").write_bytes(b"not a real webp")
            (root / "malicious.svg").write_bytes(b"<svg onload='code()'/>")
            report = collect_meshes(root, role="reference")
            self.assertEqual(report["schema"], "cbdk_private_mesh_intake_v2")
            self.assertEqual(report["counts"], {"accepted": 3, "skipped": 1})
            for entry in report["items"]:
                self.assertEqual(entry["asset_kind"], "image")
                self.assertTrue(entry["asset_id"].startswith("IMG-"))
                self.assertEqual(entry["role"], "reference")
                self.assertEqual(entry["asset_state"], "work_in_progress")
                self.assertEqual(entry["reference_truth"], "not_established")
                self.assertEqual(entry["image_interpretation"], "not_run")
                self.assertEqual(entry["geometry_validation"], "not_run")
            self.assertFalse(report["source_files_executed"])

    def test_only_explicit_state_option_marks_complete_or_reference(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "photo.png").write_bytes(b"x")
            wip = collect_meshes(root)
            complete = collect_meshes(root, state="declared_complete")
            gold = collect_meshes(root, state="declared_reference")
            self.assertEqual(wip["items"][0]["asset_state"], "work_in_progress")
            self.assertEqual(complete["items"][0]["asset_state"], "declared_complete")
            self.assertEqual(complete["items"][0]["reference_truth"], "not_established")
            self.assertEqual(gold["items"][0]["asset_state"], "declared_reference")
            self.assertEqual(gold["items"][0]["reference_truth"], "user_declared")
            self.assertEqual(gold["items"][0]["state_basis"], "explicit_manual_label")
            with self.assertRaises(ValueError):
                collect_meshes(root, state="verified_by_ai")
            self.assertIn("declared_reference", ASSET_STATES)
            self.assertIn(".png", IMAGE_SUFFIXES)

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
