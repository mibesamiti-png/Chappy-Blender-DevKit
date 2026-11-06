from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_render import GLBRenderError, render_glb_preview


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

    def test_success_requires_and_returns_all_evidence(self):
        self.output.mkdir()
        views = ["front.png", "right.png", "top.png", "iso.png"]
        for name in views:
            (self.output / name).write_bytes(b"png")
        (self.output / "scene_metadata.json").write_text("{}", encoding="utf-8")
        payload = {
            "metadata": "scene_metadata.json",
            "views": views,
            "blender_version": "4.5.15",
            "object_count": 2,
        }
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
