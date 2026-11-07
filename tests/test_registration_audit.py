"""Adversarial static registration checks without importing preview Python."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cbdk.addon_builder import ROOT
from cbdk.modular_builder import build_modular
from cbdk.registration_audit import audit_registration, validate_registration_assets


class RegistrationAuditTests(unittest.TestCase):
    def test_current_six_builds_and_ci_match(self):
        result = audit_registration(root=ROOT)
        self.assertEqual(result["recipe_count"], 6)
        self.assertFalse(result["runtime_verified"])
        self.assertFalse(result["approved"])

    def assets(self):
        return {"features/a.py": b'from ..helpers.tool import run\nclass A:\n bl_idname="cbdk.a"\nOPERATOR_CLASS=A\n',
                "helpers/tool.py": b'def run(): pass\n'}

    def test_missing_transitive_helper_rejected(self):
        assets = self.assets()
        assets["helpers/tool.py"] = b'from .missing import run\n'
        with self.assertRaisesRegex(ValueError, "Unpackaged"):
            validate_registration_assets(assets, ("a",))

    def test_registration_collision_rejected(self):
        assets = self.assets()
        assets["features/b.py"] = assets["features/a.py"].replace(b'class A:', b'class B:').replace(b'=A', b'=B')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_registration_assets(assets, ("a", "b"))

    def test_missing_helper_symbol_rejected(self):
        assets = self.assets()
        assets["helpers/tool.py"] = b'def renamed(): pass\n'
        with self.assertRaisesRegex(ValueError, "Unresolved static helper export"):
            validate_registration_assets(assets, ("a",))

    def test_unresolved_class_and_multiple_binding_rejected(self):
        for suffix in (b'\nOPERATOR_CLASS=Missing', b'\nOPERATOR_CLASS=A'):
            assets = self.assets()
            assets["features/a.py"] += suffix
            with self.assertRaisesRegex(ValueError, "OPERATOR_CLASS"):
                validate_registration_assets(assets, ("a",))

    def test_source_never_executed(self):
        assets = self.assets()
        assets["features/a.py"] += b'\nraise RuntimeError("must not run")\n'
        self.assertEqual(validate_registration_assets(assets, ("a",))["operator_ids"], ["cbdk.a"])

    def test_invalid_syntax_and_escape_rejected(self):
        for text in (b'invalid python !', b'from ...outside import x'):
            assets = self.assets()
            assets["helpers/tool.py"] = text
            with self.assertRaises(ValueError):
                validate_registration_assets(assets, ("a",))

    def test_build_rejects_dependency_drift_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for directory in ("catalog", "templates", "parts"):
                shutil.copytree(ROOT / directory, root / directory)
            source = root / "templates/modular_preview/features/vertex_nudge.py"
            source.write_text(source.read_text() + '\nfrom ..helpers.undeclared import run\n')
            recipe = json.loads((ROOT / "recipes/modular_nudge.json").read_text())
            output = root / "preview.zip"
            with self.assertRaisesRegex(ValueError, "Unpackaged"):
                build_modular(recipe, output, root=root, preview_unapproved=True)
            self.assertFalse(output.exists())

    def test_ci_and_runtime_inventory_drift_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for directory in ("catalog", "templates", "parts", "recipes", "scripts", ".github"):
                shutil.copytree(ROOT / directory, root / directory)
            smoke = root / "scripts/blender_modular_addon_smoke.py"
            original = smoke.read_text()
            smoke.write_text(original.replace('"vertex_nudge"}', '"unreviewed"}'))
            with self.assertRaisesRegex(ValueError, "Runtime feature inventory"):
                audit_registration(root=root)
            smoke.write_text(original)
            workflow = root / ".github/workflows/blender-smoke.yml"
            workflow.write_text(workflow.read_text().replace(' modular_nudge modular_all; do', ' modular_all; do'))
            with self.assertRaisesRegex(ValueError, "CI recipe inventory"):
                audit_registration(root=root)
