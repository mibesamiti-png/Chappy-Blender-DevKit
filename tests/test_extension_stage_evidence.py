"""R25 fixed evidence reducer tests, including synthetic failure controls.

Synthetic records exercise the reducer only; they are not native proof.
"""
import copy
import hashlib
import json
import unittest

from cbdk.extension_authored_fixture import fixture_metadata
from cbdk.extension_preflight import PreviewArchiveError
from cbdk.extension_recipe_preview import build_recipe_extension_bytes, ci_recipe
from cbdk.extension_stage_evidence import (
    CASES, VERSIONS, STAGES, FAILURES, generation_diagnostic,
    official_validate_observation, reduce_stage_records,
)
from test_ui_recipe_r17 import make_r23_recipe

RUN = "1" * 32
SHA = "a" * 64
PRIVATE = "private/path/never-copy-this"


def observations(case="grouped", blender="4.4.3", run_id=RUN, digest=SHA,
                 failure=None, diagnostic=None):
    rows = []
    for stage in STAGES:
        status = ("failed" if stage == failure else "not_run"
                  if failure is not None and STAGES.index(stage) > STAGES.index(failure)
                  else "passed")
        rows.append({"case": case, "blender": blender, "run_id": run_id,
                     "artifact_sha256": None if failure == "generation" else digest,
                     "stage": stage, "status": status,
                     "reason": FAILURES[stage] if status == "failed" else None,
                     "diagnostic": diagnostic if status == "failed" else None})
    return rows


def reduce(rows, case="grouped", blender="4.4.3", run_id=RUN):
    return reduce_stage_records(rows, case=case, blender=blender, run_id=run_id)


class StageEvidenceTests(unittest.TestCase):
    def assert_boundary(self, result):
        for field in ("approved", "release_authorized", "install_authorized",
                      "gui_hotkey_verified", "official_install_exercised",
                      "license_compatibility_verified", "redistribution_authorized",
                      "authenticates_observations", "undo_redo_verified_by_reducer"):
            self.assertIs(result[field], False, field)
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_fixed_case_and_version_matrix(self):
        for case in sorted(CASES):
            for version in sorted(VERSIONS):
                with self.subTest(case=case, version=version):
                    rows = observations(case, version)
                    original = copy.deepcopy(rows)
                    report = reduce(rows, case, version)
                    self.assertEqual(rows, original)
                    self.assertEqual(report["status"], "verified_fixed_stages")
                    self.assertIs(report["same_artifact_stages_verified"], True)
                    self.assertEqual(report["passed_stages"], list(STAGES))
                    self.assertEqual(report["artifact_sha256"], SHA)
                    self.assert_boundary(report)

    def test_each_stage_failure_stops_success(self):
        for index, stage in enumerate(STAGES):
            with self.subTest(stage=stage):
                rows = observations(failure=stage)
                report = reduce(rows)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["failure_reason"], FAILURES[stage])
                self.assertEqual(report["failure_stage"], stage)
                self.assertEqual(report["passed_stages"], list(STAGES[:index]))
                self.assertFalse(report["same_artifact_stages_verified"])
                self.assert_boundary(report)
                if index + 1 < len(rows):
                    rows[index + 1]["status"] = "passed"
                    self.assertEqual(reduce(rows)["failure_reason"], "evidence_mismatch")

    def test_missing_and_duplicate_or_out_of_order(self):
        rows = observations()
        for count in range(len(STAGES)):
            self.assertEqual(reduce(rows[:count])["failure_reason"], "incomplete_evidence")
        for broken in (rows[:2] + rows[3:], rows[:2] + rows[1:5],
                       [rows[1], rows[0], *rows[2:]], rows + [rows[-1]]):
            self.assertEqual(reduce(broken)["failure_reason"], "evidence_mismatch")
        failed = observations(failure="operation")
        self.assertEqual(reduce(failed[:4])["failure_reason"], "incomplete_evidence")

    def test_identity_digest_and_claim_mismatch(self):
        for key, value in (("case", "read"), ("blender", "5.2.1"), ("run_id", "2"*32),
                           ("artifact_sha256", "b"*64), ("artifact_sha256", None),
                           ("artifact_sha256", "A"*64), ("status", "unknown"),
                           ("reason", PRIVATE), ("diagnostic", PRIVATE), ("stage", "undo")):
            with self.subTest(key=key, value=value):
                rows = observations()
                rows[3][key] = value
                report = reduce(rows)
                self.assertEqual(report["failure_reason"], "evidence_mismatch")
                self.assertFalse(report["same_artifact_stages_verified"])
                self.assert_boundary(report)
        for key in ("approved", "gui_hotkey_verified", "path"):
            rows = observations()
            rows[0][key] = True
            self.assertEqual(reduce(rows)["failure_reason"], "evidence_mismatch")
        self.assertEqual(reduce(observations(), run_id="2"*32)["failure_reason"], "evidence_mismatch")
        self.assertEqual(reduce(observations(), blender=PRIVATE)["failure_reason"], "evidence_mismatch")

    def test_no_digest_before_generation_and_not_run_requires_failure(self):
        rows = observations(failure="generation")
        self.assertIsNone(reduce(rows)["artifact_sha256"])
        rows[0]["artifact_sha256"] = SHA
        self.assertEqual(reduce(rows)["failure_reason"], "evidence_mismatch")
        rows = observations()
        rows[2]["status"] = "not_run"
        self.assertEqual(reduce(rows)["failure_reason"], "evidence_mismatch")

    def test_diagnostics_reuse_and_privacy(self):
        category = generation_diagnostic(PreviewArchiveError("archive_integrity", "hash_mismatch", PRIVATE))
        self.assertEqual(category, "archive_integrity")
        report = reduce(observations(failure="generation", diagnostic=category))
        self.assertEqual(report["diagnostic"], category)
        self.assert_boundary(report)
        self.assertEqual(generation_diagnostic(ValueError(PRIVATE)), "invalid_input")
        self.assertEqual(generation_diagnostic(RuntimeError(PRIVATE)), "unclassified_generation")
        self.assertEqual(reduce(observations(failure="generation", diagnostic=PRIVATE))["failure_reason"],
                         "evidence_mismatch")
        self.assertEqual(reduce(observations(failure="operation", diagnostic="archive_integrity"))["failure_reason"],
                         "evidence_mismatch")

    def test_official_comparison_does_not_promote_rejection_or_unknown(self):
        fields = fixture_metadata()
        success = 'Success parsing TOML in "' + PRIVATE + '"'
        self.assertEqual(official_validate_observation(fields, 0, success), ("passed", None))
        self.assertEqual(official_validate_observation(fields, 0, success + "\n" + PRIVATE),
                         ("failed", "official_unclassified"))
        self.assertEqual(official_validate_observation(fields, 1, success),
                         ("failed", "official_unclassified"))
        invalid = {**fields, "license": None}
        rejected = 'Error parsing TOML "' + PRIVATE + '"\nmissing "license"'
        self.assertEqual(official_validate_observation(invalid, 1, rejected),
                         ("failed", "official_rejected"))
        self.assertEqual(official_validate_observation(invalid, 0, success),
                         ("failed", "official_disagreement"))
        report = reduce(observations(failure="validate", diagnostic="official_rejected"))
        self.assertEqual(report["failure_reason"], "validate_failed")
        self.assert_boundary(report)

    def test_real_generation_digest_only_is_not_native_evidence(self):
        for case in sorted(CASES):
            recipe = make_r23_recipe("grouped") if case == "grouped" else ci_recipe(case)
            actual = hashlib.sha256(build_recipe_extension_bytes(recipe, preview_unapproved=True)).hexdigest()
            report = reduce(observations(case=case, digest=actual)[:1], case)
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual(report["artifact_sha256"], actual)
            self.assertFalse(report["same_artifact_stages_verified"])
            self.assert_boundary(report)


if __name__ == "__main__":
    unittest.main()
