from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_render import GLBRenderError, EXPECTED_SCENE_VIEWS, render_glb_preview


class GLBRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.blender = self.root / "blender"
        self.blender.write_text("placeholder", encoding="utf-8")
        self.source = self.root / "model.glb"
        self.source.write_bytes(b"glTF-placeholder")
        self.output = self.root / "preview"

    def tearDown(self):
        self.tmp.cleanup()

    def _valid_evidence(self):
        self.output.mkdir(exist_ok=True)
        views = sorted(EXPECTED_SCENE_VIEWS)
        for name in views:
            (self.output / name).write_bytes(b"png")
        (self.output / "objects").mkdir(exist_ok=True)
        thumbnails = [
            {"object": "Cube", "file": "objects/000.png"},
            {"object": "Sphere", "file": "objects/001.png"},
        ]
        for row in thumbnails:
            (self.output / row["file"]).write_bytes(b"png")
        metadata = {
            "kind": "cbdk_glb_blender_scene_metadata",
            "object_count": 2,
            "views": views,
            "object_thumbnails": thumbnails,
        }
        (self.output / "scene_metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )
        payload = {
            "metadata": "scene_metadata.json",
            "views": views,
            "object_thumbnails": thumbnails,
            "blender_version": "4.5.15",
            "object_count": 2,
        }
        return payload

    def test_rejects_missing_blender(self):
        with self.assertRaises(GLBRenderError):
            render_glb_preview(self.root / "missing", self.source, self.output)

    def test_rejects_non_glb_input(self):
        bad = self.root / "model.obj"
        bad.write_text("x", encoding="utf-8")
        with self.assertRaises(GLBRenderError):
            render_glb_preview(self.blender, bad, self.output)

    def test_rejects_resolution_outside_guard(self):
        with self.assertRaises(GLBRenderError):
            render_glb_preview(self.blender, self.source, self.output, resolution=64)

    def test_success_requires_seven_views_thumbnails_and_metadata_consistency(self):
        payload = self._valid_evidence()
        fake = subprocess.CompletedProcess(
            args=["blender"],
            returncode=0,
            stdout="CBDK_GLB_RENDER_PASS " + json.dumps(payload) + "\n",
            stderr="",
        )
        with patch("cbdk.glb_render.subprocess.run", return_value=fake) as run:
            result = render_glb_preview(
                self.blender, self.source, self.output,
                resolution=512, timeout=90,
            )
        self.assertEqual(result, payload)
        command = run.call_args.args[0]
        self.assertIn("--background", command)
        self.assertIn("--factory-startup", command)
        self.assertIn("--python-exit-code", command)
        self.assertEqual(command[-1], "512")

    def test_rejects_missing_object_thumbnail(self):
        payload = self._valid_evidence()
        (self.output / "objects/001.png").unlink()
        fake = subprocess.CompletedProcess(
            args=["blender"], returncode=0,
            stdout="CBDK_GLB_RENDER_PASS " + json.dumps(payload) + "\n", stderr="",
        )
        with patch("cbdk.glb_render.subprocess.run", return_value=fake):
            with self.assertRaisesRegex(GLBRenderError, "Missing object thumbnail"):
                render_glb_preview(self.blender, self.source, self.output)

    def test_rejects_path_escape_from_blender_payload(self):
        payload = self._valid_evidence()
        payload["object_thumbnails"][0]["file"] = "../escape.png"
        fake = subprocess.CompletedProcess(
            args=["blender"], returncode=0,
            stdout="CBDK_GLB_RENDER_PASS " + json.dumps(payload) + "\n", stderr="",
        )
        with patch("cbdk.glb_render.subprocess.run", return_value=fake):
            with self.assertRaisesRegex(GLBRenderError, "path escape"):
                render_glb_preview(self.blender, self.source, self.output)

    def test_rejects_metadata_mismatch(self):
        payload = self._valid_evidence()
        payload["object_count"] = 3
        fake = subprocess.CompletedProcess(
            args=["blender"], returncode=0,
            stdout="CBDK_GLB_RENDER_PASS " + json.dumps(payload) + "\n", stderr="",
        )
        with patch("cbdk.glb_render.subprocess.run", return_value=fake):
            with self.assertRaisesRegex(GLBRenderError, "object count"):
                render_glb_preview(self.blender, self.source, self.output)

    def test_nonzero_blender_exit_is_controlled_error(self):
        fake = subprocess.CompletedProcess(
            args=["blender"],
            returncode=7,
            stdout="render failed\n",
            stderr="trace tail\n",
        )
        with patch("cbdk.glb_render.subprocess.run", return_value=fake):
            with self.assertRaisesRegex(GLBRenderError, "render failed"):
                render_glb_preview(self.blender, self.source, self.output)


if __name__ == "__main__":
    unittest.main()
