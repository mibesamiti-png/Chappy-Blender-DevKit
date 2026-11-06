from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from cbdk.glb_compare import (
    SceneComparisonError,
    compare_scene_metadata,
    write_scene_comparison,
)


def obj(name, center, size, *, vertices=8, edges=12, polygons=6):
    half = [x * 0.5 for x in size]
    return {
        "name": name,
        "vertices": vertices,
        "edges": edges,
        "polygons": polygons,
        "dimensions": list(size),
        "world_matrix": [
            [1, 0, 0, center[0]],
            [0, 1, 0, center[1]],
            [0, 0, 1, center[2]],
            [0, 0, 0, 1],
        ],
        "world_bounds": {
            "min": [c - h for c, h in zip(center, half)],
            "max": [c + h for c, h in zip(center, half)],
            "center": list(center),
            "size": list(size),
        },
    }


def scene(objects, *, name="model.glb"):
    mins = [min(o["world_bounds"]["min"][i] for o in objects) for i in range(3)]
    maxs = [max(o["world_bounds"]["max"][i] for o in objects) for i in range(3)]
    return {
        "schema_version": 3,
        "kind": "cbdk_glb_blender_scene_metadata",
        "source_name": name,
        "object_count": len(objects),
        "bounds": {
            "min": mins,
            "max": maxs,
            "center": [(a + b) * 0.5 for a, b in zip(mins, maxs)],
            "size": [b - a for a, b in zip(mins, maxs)],
        },
        "objects": objects,
    }


class GLBCompareTests(unittest.TestCase):
    def test_identical_shape_passes(self):
        a = scene([obj("A", [0, 0, 0], [2, 2, 2]), obj("B", [3, 0, 0], [1, 1, 1])])
        result = compare_scene_metadata(a, a)
        self.assertTrue(result["passed"])
        self.assertEqual(result["summary"]["matched_objects"], 2)
        self.assertEqual(result["summary"]["errors"], 0)

    def test_dimension_drift_fails_with_specific_diagnostic(self):
        ref = scene([obj("Socket", [0, 0, 0], [2, 2, 2])])
        cand = scene([obj("Socket", [0, 0, 0], [2.3, 2, 2])])
        result = compare_scene_metadata(ref, cand, dimension_rel_tol=0.05, scene_rel_tol=0.2)
        self.assertFalse(result["passed"])
        self.assertIn("object_dimensions", {x["code"] for x in result["differences"]})

    def test_geometry_fallback_matches_renamed_part(self):
        ref = scene([obj("Socket_L", [1, 0, 0], [2, 3, 4])])
        cand = scene([obj("GeneratedPart", [1, 0, 0], [2, 3, 4])])
        result = compare_scene_metadata(ref, cand, profile="shape")
        self.assertTrue(result["passed"])
        self.assertEqual(result["matches"][0]["match"], "geometry")
        self.assertIn("object_name_fallback", {x["code"] for x in result["differences"]})

    def test_strict_profile_rejects_renamed_part(self):
        ref = scene([obj("Socket_L", [0, 0, 0], [2, 2, 2])])
        cand = scene([obj("GeneratedPart", [0, 0, 0], [2, 2, 2])])
        result = compare_scene_metadata(ref, cand, profile="strict")
        self.assertFalse(result["passed"])

    def test_shape_profile_allows_topology_change_as_info(self):
        ref = scene([obj("Body", [0, 0, 0], [2, 2, 2], vertices=8)])
        cand = scene([obj("Body", [0, 0, 0], [2, 2, 2], vertices=100)])
        result = compare_scene_metadata(ref, cand, profile="shape")
        self.assertTrue(result["passed"])
        topo = next(x for x in result["differences"] if x["code"] == "object_topology")
        self.assertEqual(topo["severity"], "info")

    def test_missing_major_part_fails(self):
        ref = scene([
            obj("Body", [0, 0, 0], [4, 4, 4]),
            obj("Hinge", [5, 0, 0], [2, 2, 2]),
        ])
        cand = scene([obj("Body", [0, 0, 0], [4, 4, 4])])
        result = compare_scene_metadata(ref, cand, scene_rel_tol=1.0)
        self.assertFalse(result["passed"])
        self.assertIn("missing_reference_object", {x["code"] for x in result["differences"]})

    def test_invalid_duplicate_names_rejected(self):
        bad = scene([obj("A", [0, 0, 0], [1, 1, 1]), obj("A", [2, 0, 0], [1, 1, 1])])
        with self.assertRaises(SceneComparisonError):
            compare_scene_metadata(bad, bad)

    def test_writes_comparison_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = scene([obj("A", [0, 0, 0], [1, 1, 1])])
            ref = root / "ref.json"; cand = root / "cand.json"; out = root / "compare.json"
            ref.write_text(json.dumps(data), encoding="utf-8")
            cand.write_text(json.dumps(data), encoding="utf-8")
            result = write_scene_comparison(ref, cand, out)
            self.assertTrue(result["passed"])
            self.assertTrue(out.is_file())
            self.assertTrue(json.loads(out.read_text())["passed"])


if __name__ == "__main__":
    unittest.main()
