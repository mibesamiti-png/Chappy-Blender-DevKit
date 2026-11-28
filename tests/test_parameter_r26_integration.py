"""A bridge negative controls (no Blender or private input)."""
import tempfile
import unittest
from pathlib import Path

from scripts.verify_parameter_r26 import normalize, read_json, require_radius_candidate, write_new


class R26IntegrationTests(unittest.TestCase):
    def test_normalization_never_infers_expected_identity(self):
        expected = dict(case_id="parameter_fixture_r26", blender_version="4.4.3",
                        run_id="a"*32, source_sha256="b"*64)
        row = {**expected, "properties": []}
        self.assertEqual(normalize(row, expected)["case"], expected["case_id"])
        for key in expected:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "identity"):
                normalize({**row, key: "different"}, expected)
        with self.assertRaisesRegex(ValueError, "schema"):
            normalize({**row, "auto_approves": True}, expected)

    def test_duplicate_json_and_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                read_json(path)
            with self.assertRaises(FileExistsError):
                write_new(path, {"a": 1})

    def test_missing_radius_diagnosis_is_not_fabricated(self):
        report = {"kind": "cbdk_glb_scene_comparison", "schema_version": 1,
                  "passed": False, "summary": {"errors": 1},
                  "differences": [{"code": "object_dimensions", "severity": "error",
                                   "metrics": {"reference_object": "CBDK_Param_Sphere"}}]}
        self.assertEqual(require_radius_candidate(report), [
            {"property": "sphere_radius", "target": "CBDK_Param_Sphere",
             "category": "part_size_parameter"}])
        report["differences"][0]["metrics"]["reference_object"] = "Other"
        with self.assertRaisesRegex(ValueError, "mapping_missing"):
            require_radius_candidate(report)
