from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest

from cbdk.glb_inspector import GLBInspectionError, inspect_glb, write_glb_inspection


def make_glb(path: Path, doc: dict, binary: bytes = b""):
    raw = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((4 - len(raw) % 4) % 4)
    chunks = [struct.pack("<II", len(raw), 0x4E4F534A) + raw]
    if binary:
        binary += b"\x00" * ((4 - len(binary) % 4) % 4)
        chunks.append(struct.pack("<II", len(binary), 0x004E4942) + binary)
    body = b"".join(chunks)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


class GLBInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _doc(self):
        return {
            "asset": {"version": "2.0", "generator": "CBDK test"},
            "scene": 0,
            "scenes": [{"name": "Main", "nodes": [0]}],
            "nodes": [
                {"name": "Root", "children": [1]},
                {"name": "PartA", "mesh": 0},
            ],
            "meshes": [{"name": "MeshA", "primitives": [{
                "attributes": {"POSITION": 0}, "indices": 1, "material": 0
            }]}],
            "accessors": [
                {"count": 4, "min": [-1, -2, -3], "max": [1, 2, 3]},
                {"count": 6},
            ],
            "materials": [{"name": "Gray"}],
        }

    def test_reads_names_counts_hierarchy_bounds_and_chunk_safety(self):
        path = self.root / "a.glb"
        make_glb(path, self._doc(), b"1234")
        report = inspect_glb(path)
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["counts"]["nodes"], 2)
        self.assertEqual(report["counts"]["meshes"], 1)
        self.assertEqual(report["counts"]["approximate_vertex_references"], 4)
        self.assertEqual(report["counts"]["approximate_index_references"], 6)
        self.assertEqual(report["root_nodes"], [0])
        self.assertEqual(report["nodes"][0]["children"], [1])
        self.assertEqual(report["nodes"][1]["parents"], [0])
        self.assertEqual(report["nodes"][1]["mesh_name"], "MeshA")
        primitive = report["meshes"][0]["primitives"][0]
        self.assertEqual(primitive["position_min"], [-1.0, -2.0, -3.0])
        self.assertEqual(primitive["position_max"], [1.0, 2.0, 3.0])
        self.assertEqual([x["type"] for x in report["chunks"]], ["JSON", "BIN"])
        self.assertTrue(report["safety"]["static_only"])
        self.assertFalse(report["safety"]["loaded_external_uris"])
        self.assertFalse(report["safety"]["loaded_binary_payload"])

    def test_writes_deterministic_json(self):
        source = self.root / "a.glb"
        output = self.root / "report.json"
        make_glb(source, self._doc())
        write_glb_inspection(source, output)
        disk = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(disk["source_name"], "a.glb")
        self.assertEqual(disk["materials"][0]["name"], "Gray")

    def test_rejects_wrong_magic(self):
        path = self.root / "bad.glb"
        path.write_bytes(b"NOTGLB" * 8)
        with self.assertRaises(GLBInspectionError):
            inspect_glb(path)

    def test_rejects_length_mismatch(self):
        path = self.root / "bad.glb"
        make_glb(path, self._doc())
        data = bytearray(path.read_bytes())
        struct.pack_into("<I", data, 8, len(data) + 4)
        path.write_bytes(data)
        with self.assertRaises(GLBInspectionError):
            inspect_glb(path)

    def test_rejects_missing_json_chunk(self):
        path = self.root / "bad.glb"
        payload = b"1234"
        body = struct.pack("<II", len(payload), 0x004E4942) + payload
        path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
        with self.assertRaises(GLBInspectionError):
            inspect_glb(path)

    def test_rejects_non_array_nodes(self):
        path = self.root / "bad.glb"
        doc = self._doc(); doc["nodes"] = {}
        make_glb(path, doc)
        with self.assertRaises(GLBInspectionError):
            inspect_glb(path)

    def test_rejects_invalid_children_type(self):
        path = self.root / "bad.glb"
        doc = self._doc(); doc["nodes"][0]["children"] = ["x"]
        make_glb(path, doc)
        with self.assertRaises(GLBInspectionError):
            inspect_glb(path)

    def test_rejects_missing_child_reference(self):
        path = self.root / "bad.glb"
        doc = self._doc(); doc["nodes"][0]["children"] = [99]
        make_glb(path, doc)
        with self.assertRaisesRegex(GLBInspectionError, "missing node"):
            inspect_glb(path)

    def test_rejects_missing_mesh_reference(self):
        path = self.root / "bad.glb"
        doc = self._doc(); doc["nodes"][1]["mesh"] = 99
        make_glb(path, doc)
        with self.assertRaisesRegex(GLBInspectionError, "missing mesh"):
            inspect_glb(path)

    def test_rejects_node_cycle(self):
        path = self.root / "bad.glb"
        doc = self._doc()
        doc["nodes"][1]["children"] = [0]
        make_glb(path, doc)
        with self.assertRaisesRegex(GLBInspectionError, "cycle"):
            inspect_glb(path)

    def test_missing_names_get_stable_fallbacks(self):
        path = self.root / "a.glb"
        doc = self._doc(); doc["nodes"][1].pop("name"); doc["meshes"][0].pop("name")
        make_glb(path, doc)
        report = inspect_glb(path)
        self.assertEqual(report["nodes"][1]["name"], "Node_1")
        self.assertEqual(report["meshes"][0]["name"], "Mesh_0")
        self.assertEqual(report["nodes"][1]["mesh_name"], "Mesh_0")

    def test_reports_external_uri_references_without_loading_them(self):
        path = self.root / "external.glb"
        doc = self._doc()
        doc["buffers"] = [
            {"byteLength": 16, "uri": "geometry.bin"},
            {"byteLength": 4, "uri": "data:application/octet-stream;base64,AAAA"},
        ]
        doc["images"] = [{"uri": "textures/diffuse.png"}]
        make_glb(path, doc)
        report = inspect_glb(path)
        self.assertEqual(report["counts"]["buffers"], 2)
        self.assertEqual(report["external_uris"], [
            {"kind": "buffer", "index": 0, "uri": "geometry.bin"},
            {"kind": "image", "index": 0, "uri": "textures/diffuse.png"},
        ])
        self.assertTrue(report["safety"]["external_uris_present"])
        self.assertFalse(report["safety"]["loaded_external_uris"])


if __name__ == "__main__":
    unittest.main()
