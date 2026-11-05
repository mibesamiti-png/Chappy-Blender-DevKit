"""Offline-only tests for the trusted CBDK recipe dependency matrix."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.recipe_matrix import (
    CHECKED_BLENDER_VERSIONS, EXPECTED_RECIPES,
    audit_recipe_matrix, main,
)
from cbdk.addon_builder import ROOT
from cbdk.feature_catalog import TRUSTED_FEATURES, TRUSTED_PART_SOURCES


class RecipeMatrixTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        sources = {
            "catalog/addon_features.json",
            "catalog/authored_parts.json",
            *(f"recipes/{name}.json" for name in EXPECTED_RECIPES),
            *(entry["source"] for entry in TRUSTED_FEATURES.values()),
            *TRUSTED_PART_SOURCES.values(),
        }
        for relative in sources:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def modify(self, relative, change):
        path = self.root / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_complete_six_recipe_matrix_without_runtime_claim(self):
        result = audit_recipe_matrix(root=self.root)
        self.assertEqual(result["status"], "static_checks_passed")
        self.assertEqual(result["recipe_count"], 6)
        self.assertEqual(set(result["covered_features"]), set(TRUSTED_FEATURES))
        self.assertEqual(set(result["covered_parts"]), set(TRUSTED_PART_SOURCES))
        self.assertEqual(tuple(result["checked_blender_target_versions"]),
                         CHECKED_BLENDER_VERSIONS)
        self.assertFalse(result["blender_runtime_verified"])
        self.assertFalse(result["gui_tested"])
        self.assertFalse(result["approved"])
        self.assertFalse(result["redistribution_cleared"])
        for row in result["recipes"]:
            self.assertEqual(len(row["target_versions_static_compatible"]), 3)

    def test_all_recipe_resolves_every_trusted_dependency(self):
        rows = {r["recipe"]: r for r in audit_recipe_matrix(root=self.root)["recipes"]}
        self.assertEqual(set(rows["modular_all"]["resolved_features"]), set(TRUSTED_FEATURES))
        self.assertEqual(set(rows["modular_all"]["part_ids"]), set(TRUSTED_PART_SOURCES))
        self.assertEqual(set(rows["modular_nudge"]["requested_features"]), {"vertex_nudge"})

    def test_known_recipe_changes_fail_closed(self):
        self.modify("recipes/modular_objects.json",
                    lambda x: x.update(features=["edit_selection"]))
        with self.assertRaisesRegex(ValueError, "drift"):
            audit_recipe_matrix(root=self.root)

    def test_unknown_recipe_code_is_not_accepted(self):
        self.modify("recipes/modular_objects.json",
                    lambda x: x.update(execute="input_sources_private/inject.py"))
        with self.assertRaises(ValueError):
            audit_recipe_matrix(root=self.root)

    def test_missing_trusted_feature_source_rejected(self):
        (self.root / TRUSTED_FEATURES["vertex_nudge"]["source"]).unlink()
        with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
            audit_recipe_matrix(root=self.root)

    def test_missing_trusted_part_source_rejected(self):
        (self.root / TRUSTED_PART_SOURCES["BLMOD-001"]).unlink()
        with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
            audit_recipe_matrix(root=self.root)

    def test_catalog_dependency_tampering_fails(self):
        def tamper(x):
            for feature in x["features"]:
                if feature["id"] == "vertex_nudge":
                    feature["required_parts"].remove("BME-003")
        self.modify("catalog/addon_features.json", tamper)
        with self.assertRaisesRegex(ValueError, "Part dependencies"):
            audit_recipe_matrix(root=self.root)

    def test_minimum_blender_drift_is_rejected(self):
        def bump(x):
            for feature in x["features"]:
                if feature["id"] == "edit_selection":
                    feature["min_blender"] = "5.3.0"
        self.modify("catalog/addon_features.json", bump)
        with self.assertRaisesRegex(ValueError, "outside"):
            audit_recipe_matrix(root=self.root)

    def test_oversize_recipe_is_rejected_before_parse(self):
        path = self.root / "recipes/modular_nudge.json"
        path.write_text(" " * 21_000, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "size limit"):
            audit_recipe_matrix(root=self.root)

    def test_symlinked_recipe_is_rejected(self):
        path = self.root / "recipes/modular_nudge.json"
        other = self.root / "backup.json"
        shutil.copyfile(path, other)
        path.unlink()
        try:
            path.symlink_to(other)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
            audit_recipe_matrix(root=self.root)

    def test_cli_writes_deterministic_static_report(self):
        output = self.root / "reports" / "matrix.json"
        self.assertEqual(main(["--root", str(self.root), "--output", str(output)]), 0)
        first = output.read_bytes()
        self.assertEqual(main(["--root", str(self.root), "--output", str(output)]), 0)
        self.assertEqual(output.read_bytes(), first)
        self.assertEqual(json.loads(first)["recipe_count"], 6)

    def test_cli_leaves_no_success_output_after_audit_failure(self):
        output = self.root / "reports" / "matrix.json"
        (self.root / "recipes/modular_all.json").unlink()
        with self.assertRaises(ValueError):
            main(["--root", str(self.root), "--output", str(output)])
        self.assertFalse(output.exists())

    def test_no_recipe_code_exec_or_input_mutation(self):
        source = self.root / "recipes/modular_all.json"
        before = source.read_bytes()
        audit_recipe_matrix(root=self.root)
        self.assertEqual(before, source.read_bytes())
        self.assertFalse((self.root / "dist").exists())


if __name__ == "__main__":
    unittest.main()
