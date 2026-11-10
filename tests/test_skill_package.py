"""Check repository-scoped CBDK skill metadata and linked reference files."""
from __future__ import annotations

import re
import json
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile
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
        self.assertEqual(len(set(refs)), 4)
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

    def test_standalone_and_plugin_archives(self):
        with tempfile.TemporaryDirectory() as folder:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "package_skill.py"),
                 "--output-dir", folder],
                check=False, capture_output=True, text=True, cwd=ROOT,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
            source = Path(folder) / "CBDK_Skill_v1.1.0.zip"
            plugin = Path(folder) / "CBDK_Skill_Plugin_v1.1.0.zip"
            self.assertTrue(source.exists())
            self.assertTrue(plugin.exists())
            with ZipFile(source) as archive:
                self.assertIn("chappy-blender-devkit/SKILL.md", archive.namelist())
                self.assertEqual(len(archive.namelist()), 6)
                self.assertNotIn(b"\r\n", archive.read("chappy-blender-devkit/SKILL.md"))
            with ZipFile(plugin) as archive:
                info = json.loads(archive.read("plugin.json").decode("utf-8"))
                self.assertEqual(info["name"], "chappy-blender-devkit")
                self.assertEqual(info["version"], "1.1.0")
                self.assertIn("skills/chappy-blender-devkit/SKILL.md", archive.namelist())
                self.assertEqual(len(archive.namelist()), 7)

    def test_parallel_development_codex_optional_and_authority(self):
        manual = (ROOT / "docs" / "PARALLEL_DEVELOPMENT.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        milestone = (SKILL / "references" / "MILESTONE.md").read_text(encoding="utf-8")
        for text in (self.main, agents, milestone):
            self.assertIn("docs/PARALLEL_DEVELOPMENT.md", text)
            self.assertIn("Codex", text)
        self.assertIn("Codexは**任意**", manual)
        self.assertIn("Codexの利用上限", manual)
        self.assertIn("work/v018-integration-", manual)
        self.assertIn("STATE.json", manual)
        self.assertIn("ドラフトPR", manual)
        self.assertIn("main", manual)

    def test_current_milestone_reference_is_included(self):
        milestone = (SKILL / "references" / "MILESTONE.md").read_text(encoding="utf-8")
        self.assertIn("docs/project/STATE.json", milestone)
        self.assertIn("docs/V018_COMPLETION_GATES.md", milestone)
        self.assertIn("python scripts/project_handoff.py --write", milestone)
        self.assertIn("Notion", milestone)
        self.assertIn("private GLB", milestone)
        self.assertIn("v0.19", milestone)
        self.assertIn("draft PR", milestone)

    def test_no_stale_three_part_claim_in_runbook(self):
        runbook = (SKILL / "references" / "WORKFLOW.md").read_text(encoding="utf-8")
        quality = (SKILL / "references" / "QUALITY_GATES.md").read_text(encoding="utf-8")
        self.assertNotIn("only three authored parts", runbook)
        self.assertNotIn("checks BLCTX-001, BLCTX-002 and BME-001 only", quality)
        self.assertIn("4.4.3", runbook)
        self.assertIn("5.2.1", runbook)
        self.assertIn("extension-preflight", runbook)
        self.assertIn("not", quality.lower())

    def test_metadata_is_nonexecuting_and_skill_only(self):
        metadata = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("display_name:", metadata)
        self.assertIn("short_description:", metadata)
        self.assertIn("default_prompt:", metadata)
        self.assertFalse(any(SKILL.rglob("*.py")))
        self.assertFalse(any(SKILL.rglob("*.blend")))


if __name__ == "__main__":
    unittest.main()
