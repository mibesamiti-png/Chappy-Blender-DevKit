from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from cbdk.glb_quick_render import (
    EXPECTED_QUICK_VIEWS,
    GLBQuickRenderError,
    _load_optional_dependencies,
    _validate_budget,
    _view_definitions,
    quick_render_glb,
)


def make_glb(path: Path, doc: dict):
    raw = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((4 - len(raw) % 4) % 4)
    body = struct.pack("<II", len(raw), 0x4E4F534A) + raw
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


class GLBQuickRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_has_same_seven_evidence_views_as_blender_renderer(self):
        self.assertEqual(set(_view_definitions()), EXPECTED_QUICK_VIEWS)

    def test_budget_rejects_large_mesh_before_rendering(self):
        with self.assertRaisesRegex(GLBQuickRenderError, "face limit"):
            _validate_budget([{"vertex_count": 3, "face_count": 250_001}])

    def test_missing_optional_dependency_is_controlled(self):
        with patch("cbdk.glb_quick_render.importlib.import_module", side_effect=ImportError("x")):
            with self.assertRaisesRegex(GLBQuickRenderError, "optional dependencies"):
                _load_optional_dependencies()

    def test_external_uri_is_rejected_before_optional_loader(self):
        source = self.root / "external.glb"
        make_glb(source, {
            "asset": {"version": "2.0"},
            "buffers": [{"byteLength": 12, "uri": "other.bin"}],
        })
        with patch("cbdk.glb_quick_render._load_optional_dependencies") as deps:
            with self.assertRaisesRegex(GLBQuickRenderError, "external URI"):
                quick_render_glb(source, self.root / "out")
        deps.assert_not_called()


if __name__ == "__main__":
    unittest.main()
