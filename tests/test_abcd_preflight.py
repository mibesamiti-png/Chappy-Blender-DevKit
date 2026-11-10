"""Offline B/C/D preflight regression cases (no network, PR code or private data)."""
from __future__ import annotations

import unittest

from scripts.abdc_preflight import assess, OWNED, REQUIRED_JOBS
from scripts.ci_cycle_metrics import FIVE

SHA = "a" * 40


def record(team):
    examples = {
        "B": "cbdk/glb_evidence_triage.py",
        "C": "templates/modular_preview/__init__.py",
        "D": "tests/test_extension_reference_race_round14.py",
    }
    return {
        "number": {"B": 107, "C": 108, "D": 106}[team],
        "head_sha": SHA, "base_branch": "feature/v0.18-shape-diagnostics",
        "state": "open", "merged": False, "files": [examples[team]],
        "runs": {"workflow_runs": [{
            "name": name, "head_sha": SHA, "status": "completed",
            "conclusion": "success", "created_at": "2026-11-08T00:00:00Z",
            "updated_at": "2026-11-08T00:01:00Z", "id": i + 10,
        } for i, name in enumerate(FIVE)]},
        "jobs_by_run": {str(i + 10): [
            {"name": job, "status": "completed", "conclusion": "success",
             "head_sha": SHA}
            for job in REQUIRED_JOBS[name]
        ] for i, name in enumerate(FIVE)},
    }


class PreflightTests(unittest.TestCase):
    def test_all_three_eligible_for_review_not_merge(self):
        r = assess({team: record(team) for team in OWNED}, SHA)
        self.assertTrue(r["ready_for_manual_integration_review"])
        self.assertEqual(len(r["manual_review_required"]), 4)
        self.assertEqual(r["team_count"], 3)

    def test_forbidden_shared_file_is_blocked(self):
        data = {team: record(team) for team in OWNED}
        data["C"]["files"].append("docs/project/STATE.json")
        r = assess(data, SHA)
        self.assertFalse(r["ready_for_manual_integration_review"])
        self.assertTrue(any("outside_team_scope" in x for x in r["blockers"]))

    def test_missing_ci_is_blocked(self):
        data = {team: record(team) for team in OWNED}
        data["D"]["runs"] = {"workflow_runs": []}
        self.assertFalse(assess(data, SHA)["ready_for_manual_integration_review"])

    def test_missing_team_is_blocked(self):
        r = assess({"B": record("B"), "D": record("D")}, SHA)
        self.assertFalse(r["ready_for_manual_integration_review"])
        self.assertIn("C:missing_record", r["blockers"])

    def test_skipped_blender_version_cannot_pass(self):
        data = {team: record(team) for team in OWNED}
        blender_run = 10 + FIVE.index("CBDK Blender multi-version runtime smoke")
        data["C"]["jobs_by_run"][str(blender_run)][-1]["conclusion"] = "skipped"
        result = assess(data, SHA)
        self.assertFalse(result["ready_for_manual_integration_review"])
        self.assertTrue(any("required_matrix_job_not_success" in x for x in result["blockers"]))

    def test_missing_windows_version_cannot_pass(self):
        data = {team: record(team) for team in OWNED}
        windows_run = 10 + FIVE.index("CBDK Windows PowerShell launcher regression")
        data["B"]["jobs_by_run"][str(windows_run)].pop()
        result = assess(data, SHA)
        self.assertFalse(result["ready_for_manual_integration_review"])
        self.assertTrue(any("missing_required_matrix_job" in x for x in result["blockers"]))

    def test_job_from_unrelated_commit_cannot_pass(self):
        data = {team: record(team) for team in OWNED}
        python_run = 10 + FIVE.index("CBDK Python tests")
        data["D"]["jobs_by_run"][str(python_run)][0]["head_sha"] = "b" * 40
        result = assess(data, SHA)
        self.assertFalse(result["ready_for_manual_integration_review"])
        self.assertTrue(any("job_head_sha_mismatch" in x for x in result["blockers"]))

    def test_workflow_success_without_job_evidence_is_not_enough(self):
        data = {team: record(team) for team in OWNED}
        data["B"].pop("jobs_by_run")
        result = assess(data, SHA)
        self.assertFalse(result["ready_for_manual_integration_review"])
        self.assertTrue(any("missing_job_matrix_data" in x for x in result["blockers"]))


if __name__ == "__main__":
    unittest.main()
