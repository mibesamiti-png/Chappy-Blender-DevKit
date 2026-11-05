"""Behavior-specific review scaffold contracts (no Blender execution)."""
import ast
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.addon_builder import ROOT
from cbdk.registration_draft import propose_registration
from cbdk.registration_scaffold import (
    read_saved_draft, render_test_scaffold, scaffold_from_saved_draft,
    validate_saved_draft,
)


class RegistrationBehaviorTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.root = Path(handle.name)
        for source in ("catalog/authored_parts.json", "catalog/addon_features.json"):
            target = self.root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, target)

    def plan(self, behavior="unspecified"):
        return propose_registration(
            "test_behavior", ["BLCTX-001"], root=self.root, behavior=behavior
        )

    def methods(self, source):
        tree = ast.parse(source)
        return [node.name for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]

    def test_legacy_omitted_behavior_keeps_five_todos(self):
        draft = self.plan()
        self.assertNotIn("behavior", draft)
        self.assertEqual(validate_saved_draft(draft, root=self.root), draft)
        source = render_test_scaffold(draft, root=self.root)
        self.assertEqual(len(self.methods(source)), 5)
        self.assertEqual(source.count('self.fail("TODO:'), 5)
        self.assertIn("DECLARED_BEHAVIOR = 'unspecified'", source)

    def test_explicit_unspecified_preserves_legacy_json_shape(self):
        self.assertEqual(self.plan("unspecified"), self.plan())
        self.assertNotIn("behavior", self.plan("unspecified"))

    def test_read_only_generates_eight_failed_review_assertions(self):
        draft = self.plan("read_only")
        self.assertEqual(draft["behavior"], "read_only")
        source = render_test_scaffold(draft, root=self.root)
        methods = self.methods(source)
        self.assertEqual(len(methods), len(set(methods)))
        self.assertEqual(len(methods), 8)
        self.assertEqual(source.count('self.fail("TODO:'), 8)
        self.assertIn("test_read_only_preserves_geometry_and_selection", methods)
        self.assertIn("test_read_only_preserves_modifiers_and_object_transforms", methods)
        self.assertIn("test_read_only_does_not_add_an_undo_operation", methods)
        self.assertNotIn("test_edit_undo_redo_replays_exact_expected_delta", methods)
        self.assertIn("DECLARED_BEHAVIOR = 'read_only'", source)

    def test_mesh_edit_generates_eight_failed_review_assertions(self):
        source = render_test_scaffold(self.plan("mesh_edit"), root=self.root)
        methods = self.methods(source)
        self.assertEqual(len(methods), 8)
        self.assertEqual(source.count('self.fail("TODO:'), 8)
        self.assertIn("test_edit_changes_only_selected_mesh_elements", methods)
        self.assertIn("test_edit_bad_input_rolls_back_topology_and_selection", methods)
        self.assertIn("test_edit_undo_redo_replays_exact_expected_delta", methods)
        self.assertNotIn("test_read_only_does_not_add_an_undo_operation", methods)
        self.assertIn("DECLARED_BEHAVIOR = 'mesh_edit'", source)

    def test_every_generated_behavior_stays_untrusted_and_inert(self):
        for behavior in ("unspecified", "read_only", "mesh_edit"):
            with self.subTest(behavior=behavior):
                source = render_test_scaffold(self.plan(behavior), root=self.root)
                ast.parse(source)
                self.assertIn("UNREVIEWED CBDK TEST SCAFFOLD", source)
                self.assertIn("Do not copy this file into tests/", source)
                self.assertNotIn("import bpy", source)
                self.assertNotIn("from parts.blender", source)
                self.assertNotIn("approved = True", source)
                self.assertEqual(source.count('self.fail("TODO:'), len(self.methods(source)))
        self.assertFalse((self.root / "tests").exists())

    def test_invalid_or_implicit_behavior_rejected(self):
        for value in ("auto", "object", "write", "mesh_edit\ncode",
                      "../private", "", 0, None, False, ["mesh_edit"]):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                propose_registration("test_behavior", ["BLCTX-001"],
                                     root=self.root, behavior=value)

    def test_rejected_behavior_payload_does_not_produce_python(self):
        for value in ("auto", "read_only<script>", None, False):
            draft = self.plan()
            draft["behavior"] = value
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                render_test_scaffold(draft, root=self.root)
        self.assertFalse((self.root / "reports").exists())

    def test_explicit_unspecified_field_is_not_canonical(self):
        draft = self.plan()
        draft["behavior"] = "unspecified"
        with self.assertRaisesRegex(ValueError, "stale or modified"):
            validate_saved_draft(draft, root=self.root)

    def test_saved_declared_behavior_roundtrip(self):
        relative = "reports/latest/edit_draft.json"
        path = self.root / relative
        path.parent.mkdir(parents=True)
        draft = self.plan("mesh_edit")
        path.write_text(json.dumps(draft), encoding="utf-8")
        loaded = read_saved_draft(relative, root=self.root)
        self.assertEqual(loaded["behavior"], "mesh_edit")
        output = scaffold_from_saved_draft(relative, root=self.root)
        self.assertIn("test_edit_undo_redo_replays_exact_expected_delta",
                      output.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "tests").exists())

    def test_behavior_scaffold_is_deterministic(self):
        for behavior in ("read_only", "mesh_edit"):
            with self.subTest(behavior=behavior):
                draft = self.plan(behavior)
                self.assertEqual(render_test_scaffold(draft, root=self.root),
                                 render_test_scaffold(draft, root=self.root))

    def test_cli_reports_author_declared_behavior_without_approval(self):
        for behavior in ("read_only", "mesh_edit"):
            with self.subTest(behavior=behavior):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = main(["registration-draft", "--feature-id", "demo_helper_candidate",
                               "--requires-part", "BLCTX-001", "--behavior", behavior])
                self.assertEqual(rc, 0)
                data = json.loads(stdout.getvalue())
                self.assertEqual(data["behavior"], behavior)
                self.assertFalse(data["approved"])
                self.assertFalse(data["runtime_verified"])
                self.assertFalse(data["source_executed"])

    def test_cli_refuses_unknown_behavior_before_running(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as err:
                main(["registration-draft", "--feature-id", "new_feature",
                      "--requires-part", "BLCTX-001", "--behavior", "auto"])
        self.assertEqual(err.exception.code, 2)

    def test_no_trusted_source_or_catalog_is_rewritten(self):
        path = self.root / "catalog/addon_features.json"
        before = path.read_bytes()
        for behavior in ("unspecified", "read_only", "mesh_edit"):
            render_test_scaffold(self.plan(behavior), root=self.root)
        self.assertEqual(before, path.read_bytes())
        self.assertFalse((self.root / "templates").exists())
        self.assertFalse((self.root / "parts").exists())


if __name__ == "__main__":
    unittest.main()
