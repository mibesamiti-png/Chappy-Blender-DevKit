"""Offline, deterministic tests for SHA-aware read-only CI timing aggregation."""
from __future__ import annotations

import unittest

from scripts.ci_cycle_metrics import FIVE, SEVEN, summarize

SHA = "a" * 40
OTHER = "b" * 40


def run(name, sha=SHA, status="completed", conclusion="success", ident=1,
        created="2026-11-08T02:44:03Z", updated="2026-11-08T02:47:03Z"):
    return {
        "name": name, "head_sha": sha, "status": status,
        "conclusion": conclusion, "id": ident, "run_attempt": 1,
        "created_at": created, "updated_at": updated,
        "html_url": "https://github.com/example/actions/runs/1",
    }


class TimingReportTests(unittest.TestCase):
    def test_five_full_success_and_critical_path(self):
        data = {"workflow_runs": [run(name, ident=i) for i, name in enumerate(FIVE, 1)]}
        report = summarize(data, SHA, gate=5)
        self.assertEqual(report["gate_result"], "success")
        self.assertEqual(report["workflow_successes"], 5)
        self.assertEqual(report["observed_wall_seconds"], 180)
        self.assertEqual(report["slowest_workflow_seconds"], 180)

    def test_required_seven_must_all_be_present(self):
        data = {"workflow_runs": [run(name, ident=i) for i, name in enumerate(FIVE, 1)]}
        report = summarize(data, SHA, gate=7)
        self.assertEqual(report["gate_result"], "incomplete_or_failed")
        self.assertEqual(report["workflow_successes"], 5)
        self.assertEqual(sum(w["state"] == "missing" for w in report["workflows"]), 2)

    def test_wrong_sha_success_is_not_evidence(self):
        data = {"workflow_runs": [run(name, sha=OTHER) for name in SEVEN]}
        self.assertEqual(summarize(data, SHA, gate=7)["workflow_successes"], 0)

    def test_latest_attempt_overrides_old_green(self):
        data = {"workflow_runs": [run(name, ident=i) for i, name in enumerate(FIVE, 1)]}
        data["workflow_runs"].append(run(FIVE[0], ident=99, status="in_progress", conclusion=None,
                                          created="2026-11-08T03:00:00Z", updated="2026-11-08T03:00:30Z"))
        report = summarize(data, SHA, gate=5)
        self.assertEqual(report["gate_result"], "incomplete_or_failed")
        self.assertEqual(report["extra_matching_runs"], 1)
        self.assertEqual(report["workflows"][0]["state"], "in_progress")

    def test_invalid_data_is_not_success(self):
        with self.assertRaises(ValueError):
            summarize({}, SHA)
        with self.assertRaises(ValueError):
            summarize({"workflow_runs": []}, "oops")
        with self.assertRaises(ValueError):
            summarize({"workflow_runs": []}, SHA, gate=6)


if __name__ == "__main__":
    unittest.main()
