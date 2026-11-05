"""Draft-to-test-scaffold regression suite: never auto-approve or execute sources."""
import ast
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.addon_builder import ROOT
from cbdk.registration_draft import propose_registration
from cbdk.registration_scaffold import (
    read_saved_draft, render_test_scaffold, scaffold_from_saved_draft,
    validate_saved_draft, write_test_scaffold,
)


class RegistrationScaffoldTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.root = Path(handle.name)
        for name in ("catalog/authored_parts.json", "catalog/addon_features.json"):
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        self.draft = propose_registration(
            "align_vertices", ["BLCTX-001", "BME-004"],
            new_part_id="BME-004", new_part_module="edit_align", root=self.root,
        )
        self.draft_path = "reports/latest/registration_draft.json"

    def save_draft(self, value=None, relative=None):
        target = self.root / (relative or self.draft_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.draft if value is None else value),
                          encoding="utf-8")
        return target

    def test_python_scaffold_is_syntax_valid_and_intentionally_failing(self):
        code = render_test_scaffold(self.draft, root=self.root)
        tree = ast.parse(code)
        names = [node.name for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        self.assertEqual(len(names), 5)
        self.assertEqual(code.count('self.fail("TODO:'), 5)
        self.assertIn("FEATURE_ID = 'align_vertices'", code)
        self.assertIn("NEW_PART_SOURCE = 'parts/blender/edit_align.py'", code)
        self.assertIn("REQUIRED_PARTS = ('BLCTX-001', 'BME-004')", code)
        self.assertNotIn("import bpy", code)
        self.assertNotIn("import parts.blender", code)
        self.assertNotIn("approved = True", code)
        self.assertIn("Do not copy this file into tests/", code)

    def test_generated_source_is_deterministic(self):
        first = render_test_scaffold(self.draft, root=self.root)
        self.assertEqual(first, render_test_scaffold(self.draft, root=self.root))
        self.assertFalse((self.root / "tests").exists())

    def test_new_feature_using_existing_part_only(self):
        existing = propose_registration("inspect_custom", ["BLCTX-001"],
                                        root=self.root)
        code = render_test_scaffold(existing, root=self.root)
        self.assertIn("NEW_PART_SOURCE = None", code)
        self.assertIn("REQUIRED_PARTS = ('BLCTX-001',)", code)
        self.assertEqual(code.count("self.fail("), 5)

    def test_read_canonical_saved_draft(self):
        self.save_draft()
        self.assertEqual(read_saved_draft(self.draft_path, root=self.root), self.draft)

    def test_stale_or_malicious_safety_flags_rejected(self):
        for key, changed in (
            ("approved", True), ("approved", 0),
            ("preview_only", False), ("preview_only", 1),
            ("runtime_verified", True), ("runtime_verified", 0),
            ("source_executed", True), ("catalog_modified", True),
            ("redistribution_cleared", True),
            ("status", "approved"), ("kind", "trusted_registration"),
            ("review_steps", []),
        ):
            with self.subTest(key=key, changed=changed):
                altered = copy.deepcopy(self.draft)
                altered[key] = changed
                with self.assertRaises(ValueError):
                    validate_saved_draft(altered, root=self.root)

    def test_reject_schema_unknown_fields_and_missing_fields(self):
        for mutated in (
            None, [], {}, {"schema_version": 1},
            dict(self.draft, schema_version=True),
            dict(self.draft, extra_code="exec('danger')"),
            {k: v for k, v in self.draft.items() if k != "feature_id"},
        ):
            with self.subTest(value=str(mutated)[:45]), self.assertRaises(ValueError):
                validate_saved_draft(mutated, root=self.root)

    def test_invalid_new_part_object_rejected(self):
        for invalid in (False, [], {}, {"id": "BME-004"},
                        dict(self.draft["new_part"], source="../secret.py"),
                        dict(self.draft["new_part"], source="parts/blender/no-such/.py"),
                        dict(self.draft["new_part"], approved=True)):
            with self.subTest(invalid=str(invalid)[:50]):
                altered = copy.deepcopy(self.draft)
                altered["new_part"] = invalid
                with self.assertRaises(ValueError):
                    validate_saved_draft(altered, root=self.root)

    def test_modified_dependencies_are_not_accepted(self):
        changed = copy.deepcopy(self.draft)
        changed["required_parts"] = ["BLCTX-001"]
        with self.assertRaises(ValueError):
            render_test_scaffold(changed, root=self.root)
        changed = copy.deepcopy(self.draft)
        changed["feature_source"] = "input_sources_private/sneaky.py"
        with self.assertRaises(ValueError):
            render_test_scaffold(changed, root=self.root)

    def test_mutated_catalog_makes_old_draft_stale(self):
        cat = self.root / "catalog/addon_features.json"
        value = json.loads(cat.read_text(encoding="utf-8"))
        value["features"][0]["source"] = "input_sources_private/sneaky.py"
        cat.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ValueError):
            render_test_scaffold(self.draft, root=self.root)

    def test_write_only_ignored_nontracked_scaffold(self):
        saved = write_test_scaffold(self.draft, root=self.root)
        self.assertEqual(saved.relative_to(self.root).as_posix(),
                         "reports/latest/scaffolds/test_align_vertices_review.py")
        self.assertEqual(saved.read_text("utf-8"),
                         render_test_scaffold(self.draft, root=self.root))
        self.assertFalse((self.root / "tests").exists())
        self.assertFalse((self.root / self.draft["feature_source"]).exists())
        with self.assertRaises(FileExistsError):
            write_test_scaffold(self.draft, root=self.root)

    def test_from_saved_draft_generates_same_template(self):
        self.save_draft()
        result = scaffold_from_saved_draft(self.draft_path, root=self.root)
        self.assertIn("self.fail(", result.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "tests").exists())

    def test_missing_and_corrupt_saved_draft_refused(self):
        with self.assertRaises(ValueError):
            read_saved_draft(self.draft_path, root=self.root)
        dest = self.save_draft()
        dest.write_text("{bad json", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            read_saved_draft(self.draft_path, root=self.root)
        dest.write_text("x" * 40_000, encoding="utf-8")
        with self.assertRaises(ValueError):
            read_saved_draft(self.draft_path, root=self.root)

    def test_read_draft_path_escape_refused(self):
        for name in ("../anything.json", "/tmp/a.json", "catalog/anything.json",
                     "reports/latest/../../../evil.json", "reports/ci/a.json",
                     "reports/latest/input.py"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                read_saved_draft(name, root=self.root)

    def test_symlinked_draft_and_directory_refused(self):
        source = self.save_draft()
        link = self.root / "reports/latest/another.json"
        try:
            link.symlink_to(source)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ValueError):
            read_saved_draft("reports/latest/another.json", root=self.root)
        source.unlink()
        external = self.root / "outside"
        external.mkdir()
        latest = self.root / "reports/latest"
        shutil.rmtree(latest)
        latest.symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            read_saved_draft(self.draft_path, root=self.root)

    def test_scaffold_parent_symlink_escape_refused(self):
        base = self.root / "reports/latest"
        base.mkdir(parents=True)
        external = self.root / "outside"
        external.mkdir()
        try:
            (base / "scaffolds").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaisesRegex(ValueError, "escapes"):
            write_test_scaffold(self.draft, root=self.root)
        self.assertEqual(list(external.iterdir()), [])

    def test_output_must_not_create_trusted_implementation(self):
        self.save_draft()
        scaffold_from_saved_draft(self.draft_path, root=self.root)
        self.assertFalse((self.root / "parts/blender/edit_align.py").exists())
        self.assertFalse((self.root / "templates/modular_preview/features/align_vertices.py").exists())
        self.assertFalse((self.root / "tests").exists())


if __name__ == "__main__":
    unittest.main()
