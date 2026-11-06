"""Regression tests for the non-executable, review-only registration draft."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.addon_builder import ROOT
from cbdk.registration_draft import propose_registration, write_draft


class RegistrationDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("catalog/authored_parts.json", "catalog/addon_features.json"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def propose(self, **extra):
        return propose_registration("align_vertices", ["BLCTX-001", "BME-004"],
                                    new_part_id="BME-004", new_part_module="edit_align",
                                    root=self.root, **extra)

    def test_proposal_records_deps_but_never_approves_or_executes(self):
        before = (self.root / "catalog/authored_parts.json").read_bytes()
        report = self.propose()
        self.assertEqual(report["status"], "proposal_only")
        self.assertEqual(report["feature_id"], "align_vertices")
        self.assertEqual(report["new_part"]["source"], "parts/blender/edit_align.py")
        self.assertEqual(report["required_parts"], ["BLCTX-001", "BME-004"])
        for name in ("approved", "redistribution_cleared", "runtime_verified",
                     "source_executed", "catalog_modified"):
            self.assertIs(report[name], False)
        self.assertEqual(before, (self.root / "catalog/authored_parts.json").read_bytes())
        self.assertFalse((self.root / report["feature_source"]).exists())
        self.assertFalse((self.root / report["new_part"]["source"]).exists())

    def test_deterministic_plan(self):
        self.assertEqual(self.propose(), self.propose())
        self.assertIn("cbdk/recipe_matrix.py", str(self.propose()["review_steps"]))

    def test_existing_part_only_feature_plan(self):
        report = propose_registration("new_measure", ["BLCTX-001", "BLGEO-001"],
                                      root=self.root)
        self.assertIsNone(report["new_part"])
        self.assertEqual(len(report["required_parts"]), 2)

    def test_duplicate_or_unknown_feature_refused(self):
        for feature in ("vertex_nudge", "object_selection", "x", "../private",
                        "x;exec", "AFeature", "x" * 41, 25, None):
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                propose_registration(feature, ["BLCTX-001"], root=self.root)

    def test_new_part_id_and_module_must_be_paired(self):
        for options in ({"new_part_id": "BME-004"},
                        {"new_part_module": "edit_align"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                propose_registration("align_vertices", ["BLCTX-001"],
                                     root=self.root, **options)

    def test_invalid_new_part_ids_or_paths_are_refused(self):
        for part, module in (("BME-002", "edit_align"), ("bme-004", "edit_align"),
                             ("BME-004", "../secret"), ("BME-004", "Bad-Module"),
                             ("BME-004", "x" * 41)):
            with self.subTest(part=part, module=module), self.assertRaises(ValueError):
                propose_registration("align_vertices", ["BLCTX-001", "BME-004"],
                                     new_part_id=part, new_part_module=module,
                                     root=self.root)

    def test_unregistered_missing_and_duplicate_deps_are_refused(self):
        for deps in ([], ["BME-999"], ["BLCTX-001", "BLCTX-001"],
                     ["BLCTX-001", 2], ["BLCTX-001"] * 9, "BLCTX-001"):
            with self.subTest(deps=deps), self.assertRaises(ValueError):
                propose_registration("new_measure", deps, root=self.root)

    def test_new_part_is_required_dependency(self):
        with self.assertRaisesRegex(ValueError, "required dependency"):
            propose_registration("align_vertices", ["BLCTX-001"],
                                 new_part_id="BME-004", new_part_module="edit_align",
                                 root=self.root)

    def test_existing_source_path_is_never_claimed_as_new(self):
        path = self.root / "templates/modular_preview/features/align_vertices.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("do not touch", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.propose()
        self.assertEqual(path.read_text(encoding="utf-8"), "do not touch")
        path.unlink()
        path = self.root / "parts/blender/edit_align.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("do not touch", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.propose()

    def test_catalog_tampering_or_silent_approval_refused(self):
        path = self.root / "catalog/authored_parts.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["parts"][0]["approved"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "review state"):
            self.propose()

    def test_feature_catalog_drift_refused(self):
        path = self.root / "catalog/addon_features.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["features"][0]["source"] = "input_sources_private/code.py"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.propose()

    def test_private_output_is_created_exclusively(self):
        report = self.propose()
        name = "reports/latest/my_draft.json"
        target = write_draft(report, root=self.root, relative_path=name)
        self.assertEqual(json.loads(target.read_text("utf-8")), report)
        self.assertFalse((self.root / "catalog/authored_parts.json").is_symlink())
        with self.assertRaises(FileExistsError):
            write_draft(report, root=self.root, relative_path=name)

    def test_no_output_escape_or_overwrite(self):
        report = self.propose()
        for name in ("../escape.json", "/tmp/external.json", "catalog/authored_parts.json",
                     "reports/latest/../../catalog/x.json", "reports/latest/result.txt",
                     "reports/ci/unsafe.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                write_draft(report, root=self.root, relative_path=name)

    def test_private_output_symlink_parent_refused(self):
        external = self.root / "outside"
        external.mkdir()
        reports = self.root / "reports"
        reports.mkdir()
        try:
            (reports / "latest").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        with self.assertRaisesRegex(ValueError, "escapes"):
            write_draft(self.propose(), root=self.root,
                        relative_path="reports/latest/escape.json")

    def test_cli_only_prints_review_plan_by_default(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["registration-draft", "--feature-id", "demo_helper_candidate",
                           "--requires-part", "BLCTX-001"])
        self.assertEqual(result, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "proposal_only")
        self.assertIs(report["catalog_modified"], False)
        self.assertIs(report["runtime_verified"], False)

    def test_cli_invalid_id_exits_without_writing(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(["registration-draft", "--feature-id", "../private",
                      "--requires-part", "BLCTX-001"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
