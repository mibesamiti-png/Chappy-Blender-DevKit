"""Regression coverage for GitHub-first CBDK chat handoff state."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.project_handoff import (
    ROOT, HANDOFF, STATE, render_handoff, validate_state,
    write_ci_snapshot, main,
)


class ProjectHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source_state = json.loads((ROOT / STATE).read_text(encoding="utf-8"))
        self.state = copy.deepcopy(source_state)
        paths = {
            "pyproject.toml", str(STATE), "catalog/authored_parts.json",
            "catalog/addon_features.json",
        }
        paths.update(row["source"] for row in self.state["requirements"] if row["source"])
        parts = json.loads((ROOT / "catalog/authored_parts.json").read_text())
        features = json.loads((ROOT / "catalog/addon_features.json").read_text())
        paths.update(x["source"] for x in parts["parts"])
        paths.update(x["source"] for x in features["features"])
        for rel in paths:
            destination = self.root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, destination)

    def save(self):
        (self.root / STATE).write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")

    def test_current_repository_state_is_valid(self):
        data = validate_state()
        self.assertTrue(data["state"]["release"]["current"])
        self.assertGreaterEqual(len(data["parts"]), 7)
        self.assertGreaterEqual(len(data["features"]), 5)

    def test_render_contains_recovery_plan_issues_and_verified_ci(self):
        rendered = render_handoff(validate_state(self.root))
        for word in ("次にやること", "既知の問題", "前回、実際に確認されたテスト",
                     "件成功", "GitHubからBlenderへの直接インストールは保留"):
            self.assertIn(word, rendered)
        self.assertIn(validate_state(self.root)["state"]["last_verified"]["blender"]["run_url"], rendered)
        self.assertNotIn("input_sources_private/addon.py", rendered)

    def test_deterministic_rendering(self):
        self.assertEqual(render_handoff(validate_state(self.root)),
                         render_handoff(validate_state(self.root)))

    def test_stale_version_fails(self):
        self.state["release"]["current"] = "99.0.0"
        self.save()
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_state(self.root)

    def test_unknown_requirement_source_fails(self):
        self.state["requirements"][0]["source"] = "nonexistent.py"
        self.save()
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_state(self.root)

    def test_duplicate_requirement_id_fails(self):
        self.state["requirements"][1]["id"] = self.state["requirements"][0]["id"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_state(self.root)

    def test_invalid_issue_reference_fails(self):
        self.state["known_issues"][0]["related_requirement"] = "NOPE-001"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unknown requirement"):
            validate_state(self.root)

    def test_silent_approval_fails(self):
        path = self.root / "catalog/authored_parts.json"
        data = json.loads(path.read_text())
        data["parts"][0]["approved"] = True
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "approval"):
            validate_state(self.root)

    def test_duplicate_task_priority_fails(self):
        self.state["next_actions"][1]["priority"] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, "priority"):
            validate_state(self.root)

    def test_newer_evidence_than_release_is_forbidden(self):
        self.state["last_verified"]["release"] = "99.0.0"
        self.save()
        with self.assertRaisesRegex(ValueError, "newer"):
            validate_state(self.root)

    def test_cli_can_regenerate_and_check(self):
        self.assertEqual(main(["--validate"], root=self.root), 0)
        self.assertEqual(main(["--check"], root=self.root), 1)
        self.assertEqual(main(["--write"], root=self.root), 0)
        self.assertTrue((self.root / HANDOFF).is_file())
        self.assertEqual(main(["--check"], root=self.root), 0)
        (self.root / HANDOFF).write_text("outdated")
        self.assertEqual(main(["--check"], root=self.root), 1)

    def test_ci_snapshot_requires_a_genuine_success_log(self):
        log = self.root / "unittest.log"
        output = self.root / "reports/ci/python_observation.json"
        log.write_text("Ran 208 tests in 0.500s\n\nOK\n", encoding="utf-8")
        write_ci_snapshot(self.root, output, log)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["python_tests_passed"], 208)
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["blender_runtime_verified_by_this_job"])

    def test_ci_snapshot_rejects_failed_log(self):
        log = self.root / "unittest.log"
        output = self.root / "reports/ci/python_observation.json"
        for invalid in ("Ran 5 tests in 0.1s\nFAILED (failures=1)\n",
                        "Ran 5 tests in 0.1s\n", "OK\n"):
            with self.subTest(invalid=invalid):
                log.write_text(invalid, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "unsuccessful"):
                    write_ci_snapshot(self.root, output, log)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
