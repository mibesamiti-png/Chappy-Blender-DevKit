"""R6: fail-closed reload before losing registered Blender resources.

This pure-Python suite compiles only the trusted module-level reload preflight.
It does not substitute for the actual Blender 4.4/4.5/5.2 native R6 checks,
which now run through A's previously connected R5 lifecycle smoke step.
"""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cbdk.addon_builder import ROOT, build_addon


TEMPLATE = ROOT / "templates/modular_preview/__init__.py"
NATIVE = ROOT / "tests/blender_ui_lifecycle_r5.py"
R6_MARKERS = (
    "native_r6_shared_mesh_nudge_refused_no_mutation",
    "native_r6_live_reload_rejected_without_leaks",
    "native_r6_detached_reload_reregistered",
    "native_r6_dual_foreign_descriptors_preserved",
    "native_r6_partial_registration_retry",
)


def _reload_guard():
    tree = ast.parse(TEMPLATE.read_text(encoding="utf-8"))
    guards = [node for node in tree.body
              if isinstance(node, ast.If)
              and "CBDK preview must be unregistered before module reload"
              in ast.unparse(node)]
    if len(guards) != 1:
        raise AssertionError("Exactly one owned-module reload preflight required")
    return compile(ast.fix_missing_locations(
        ast.Module(body=guards, type_ignores=[])), "<CBDK-R6-reload-guard>", "exec")


class R6ReloadGuardTests(unittest.TestCase):
    def test_detached_or_first_import_is_allowed(self):
        guard = _reload_guard()
        for ledgers in (
                {},
                {"_REGISTERED": [], "_OWNED_PROPERTIES": [],
                 "_OWNED_PROPERTY_TOKENS": {}},
        ):
            with self.subTest(ledgers=ledgers):
                namespace = dict(ledgers)
                exec(guard, namespace)
                self.assertEqual({k: v for k, v in namespace.items()
                                  if k in ledgers}, ledgers)

    def test_any_live_ledger_blocks_without_discarding_ownership(self):
        guard = _reload_guard()
        cases = (
            {"_REGISTERED": [object()]},
            {"_OWNED_PROPERTIES": ["cbdk_modular_result"]},
            {"_OWNED_PROPERTY_TOKENS": {"cbdk_modular_result": None}},
            {"_REGISTERED": [object()],
             "_OWNED_PROPERTIES": ["cbdk_modular_nudge_offset"],
             "_OWNED_PROPERTY_TOKENS": {"cbdk_modular_result": object()}},
        )
        for case in cases:
            with self.subTest(names=tuple(case)):
                namespace = dict(case)
                with self.assertRaisesRegex(RuntimeError, "unregistered before module reload"):
                    exec(guard, namespace)
                for key, value in case.items():
                    self.assertIs(namespace[key], value)

    def test_preflight_precedes_class_and_registration_ledger_assignments(self):
        tree = ast.parse(TEMPLATE.read_text(encoding="utf-8"))
        guard_idx = next(i for i, n in enumerate(tree.body)
                         if isinstance(n, ast.If)
                         and "CBDK preview must be unregistered before module reload"
                         in ast.unparse(n))
        for i, node in enumerate(tree.body):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id in {
                            "_FEATURE_MODULES", "_OPERATORS", "_REGISTERED",
                            "_OWNED_PROPERTIES", "_OWNED_PROPERTY_TOKENS"}:
                        self.assertLess(guard_idx, i, target.id)
            if isinstance(node, ast.ClassDef) and node.name == "VIEW3D_PT_cbdk_modular_preview":
                self.assertLess(guard_idx, i)

    def test_native_fixture_contains_bounded_real_blender_r6_checks(self):
        source = NATIVE.read_text(encoding="utf-8")
        ast.parse(source)
        for marker in R6_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(source.count('checks.append("' + marker + '")'), 1)
        self.assertIn("importlib.reload(module)", source)
        self.assertIn('bpy.ops.mesh.select_all(action="SELECT")', source)
        self.assertIn("mesh.users == 2", source)
        self.assertIn("bpy.utils.register_class = fail_second_registration", source)
        self.assertIn('CBDK_R5_UI_LIFECYCLE_PASS ', source)
        self.assertNotIn("input_sources_private/", source)
        # This is a static script contract, not an actual native pass.

    def test_all_five_features_remain_in_six_preview_recipes(self):
        names = ("modular_objects", "modular_edit", "modular_combined",
                 "modular_geometry", "modular_nudge", "modular_all")
        all_ids = set()
        with tempfile.TemporaryDirectory(prefix="cbdk-r6-") as d:
            for name in names:
                with self.subTest(name=name):
                    recipe = ROOT / "recipes" / (name + ".json")
                    out = Path(d) / (name + ".zip")
                    result = build_addon(recipe, out, root=ROOT, preview_unapproved=True)
                    self.assertTrue(result["preview_only"])
                    self.assertFalse(result["approved"])
                    with ZipFile(out) as archive:
                        metadata = json.loads(archive.read(
                            "cbdk_modular_preview/CBDK_BUILD_INFO.json"))
                        self.assertFalse(metadata["redistribution_cleared"])
                        self.assertFalse(metadata["approved"])
                        features = set(metadata["features"])
                        all_ids.update(features)
                        self.assertTrue(features)
            self.assertEqual(all_ids, {
                "object_selection", "edit_selection", "mesh_bounds",
                "modifier_summary", "vertex_nudge"})


if __name__ == "__main__":
    unittest.main()
