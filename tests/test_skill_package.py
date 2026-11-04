"""Check repository-scoped CBDK skill metadata and linked reference files."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "chappy-blender-devkit"


class SkillPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_agent_skill_has_complete_frontmatter(self):
        self.assertTrue(self.main.startswith("---\n"))
        parts = self.main.split("---\n", 2)
        self.assertEqual(len(parts), 3)
        self.assertRegex(parts[1], r"(?m)^name: chappy-blender-devkit$")
        description = re.search(r"(?m)^description: (.+)$", parts[1])
        self.assertIsNotNone(description)
        self.assertGreater(len(description.group(1)), 90)
        self.assertIn("Blender", description.group(1))
        self.assertIn("CBDK", description.group(1))

    def test_all_local_reference_links_resolve(self):
        refs = re.findall(r"\]\((references/[^)]+\.md)\)", self.main)
        self.assertEqual(len(refs), 3)
        for ref in refs:
            with self.subTest(ref=ref):
                path = (SKILL / ref).resolve()
                self.assertTrue(path.is_relative_to(SKILL.resolve()))
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 300)

    def test_skill_requires_nonfictional_test_and_provenance(self):
        required = (
            "AGENTS.md", "docs/PROGRESS.md", "catalog/authored_parts.json",
            "python -m cbdk search", "python -m unittest discover -s tests -v",
            "python -m cbdk verify-parts", "evidence-status",
            ".github/workflows/blender-smoke.yml",
            "input_sources_private/", "approved", "pull request",
        )
        text = self.main.lower()
        for needle in required:
            with self.subTest(needle=needle):
                self.assertIn(needle.lower(), text)

    def test_documented_cli_commands_exist(self):
        code = (ROOT / "cbdk" / "__main__.py").read_text(encoding="utf-8")
        for command in (
            "scan", "search", "triage", "isolate", "bundle", "crossfile",
            "audit-blender", "contracts", "verify-parts", "evidence-status",
        ):
            with self.subTest(command=command):
                self.assertIn(f'"{command}"', code) if f'"{command}"' in code else self.assertIn(f"'{command}'", code)

    def test_metadata_is_nonexecuting_and_skill_only(self):
        metadata = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("display_name:", metadata)
        self.assertIn("short_description:", metadata)
        self.assertIn("default_prompt:", metadata)
        self.assertFalse(any(SKILL.rglob("*.py")))
        self.assertFalse(any(SKILL.rglob("*.blend")))


if __name__ == "__main__":
    unittest.main()
