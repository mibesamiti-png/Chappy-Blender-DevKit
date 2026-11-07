"""Pure-Python regression checks: unavailable Undo must never look verified."""
import json
import tempfile
import unittest
from pathlib import Path

from cbdk.undo_probe_report import PREFIX, PREPARED_CASES, build_report, parse_log, validate_report, main

ROOT = Path(__file__).resolve().parents[1]


class UndoProbeReportTests(unittest.TestCase):
    def extended(self):
        cases = {name: {"undo_status": "passed", "redo_status": "passed", "edit_steps": steps}
                 for name, steps in PREPARED_CASES.items()}
        return build_report("4.5.15 LTS", "unavailable", "not_attempted", prepared_cases=cases)

    def test_prepared_success_never_promotes_normal_or_gui_probe(self):
        record = self.extended()
        self.assertEqual(validate_report(record), record)
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["status"], "unavailable_in_background")
        self.assertFalse(record["gui_hotkey_verified"])
        self.assertEqual(parse_log(PREFIX + json.dumps(record)), record)

    def test_prepared_missing_cases_and_false_state_claims_rejected(self):
        for field, value in (("exact_topology_verified", 1),
                             ("cancelled_edit_unchanged", False),
                             ("prepared_stack_method", "automatic_operator_history"),
                             ("prepared_stack_cases", {})):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_report(dict(self.extended(), **{field: value}))

    def test_prepared_round_count_and_status_consistency(self):
        for field, value in (("edit_steps", True), ("edit_steps", 1),
                             ("redo_status", "not_attempted")):
            record = self.extended()
            record["prepared_stack_cases"]["multi_vertex_repeated"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_report(record)

    def test_duplicate_observation_fields_rejected(self):
        text = json.dumps(self.extended())
        text = text.replace('"undo_status": "unavailable"',
                            '"undo_status": "passed", "undo_status": "unavailable"')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_log(PREFIX + text)

    def test_passed_background_is_not_gui(self):
        report = build_report("4.5.15", "passed", "passed")
        self.assertEqual(report["status"], "verified_background")
        self.assertFalse(report["gui_hotkey_verified"])
        self.assertFalse(report["user_project_tested"])
        self.assertEqual(validate_report(report), report)

    def test_unavailable_is_not_a_success(self):
        report = build_report("5.2.1", "unavailable", "not_attempted")
        self.assertEqual(report["status"], "unavailable_in_background")
        self.assertNotEqual(report["status"], "verified_background")

    def test_undo_only_is_partial(self):
        report = build_report("4.4.3", "passed", "unavailable")
        self.assertEqual(report["status"], "partial_background")

    def test_reject_false_positive_and_inconsistent_statuses(self):
        base = build_report("4.5.15", "unavailable", "not_attempted")
        altered = dict(base, status="verified_background")
        with self.assertRaises(ValueError):
            validate_report(altered)
        with self.assertRaises(ValueError):
            build_report("4.5.15", "unavailable", "passed")
        with self.assertRaises(ValueError):
            build_report("4.5.15", "passed", "not_attempted")

    def test_reject_false_gui_claim_and_malformed_types(self):
        base = build_report("4.5.15", "passed", "passed")
        with self.assertRaises(ValueError):
            validate_report(dict(base, gui_hotkey_verified=True))
        with self.assertRaises(ValueError):
            validate_report(dict(base, operator_completed=1))
        with self.assertRaises(ValueError):
            validate_report(dict(base, unrecognized=True))
        with self.assertRaises(ValueError):
            build_report("", "passed", "passed")

    def test_malformed_types_do_not_escape_validation(self):
        for bad in ([], {}, None, 1, True):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    build_report("4.5.15", bad, "not_attempted")
                with self.assertRaises(ValueError):
                    build_report("4.5.15", "passed", bad)
        valid = build_report("4.5.15", "passed", "passed")
        with self.assertRaises(ValueError):
            validate_report(dict(valid, schema_version=True))
        for bad_version in ("", "4.5.15\nmalformed", "\x00", "x" * 101):
            with self.subTest(bad_version=repr(bad_version)):
                with self.assertRaises(ValueError):
                    build_report(bad_version, "passed", "passed")

    def test_exactly_one_structured_log_record(self):
        record = build_report("4.5.15", "passed", "passed")
        line = PREFIX + json.dumps(record)
        self.assertEqual(parse_log("boot\n" + line + "\ndone\n"), record)
        for bad in ("", "boot\n", line + "\n" + line,
                    PREFIX + "{", PREFIX + "null", PREFIX + json.dumps(
                        dict(record, status="verified_gui"))):
            with self.subTest(bad=bad[:25]), self.assertRaises(ValueError):
                parse_log(bad)

    def test_cli_writes_only_valid_observation(self):
        record = build_report("5.2.1", "unavailable", "not_attempted")
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "input.log"
            out = Path(temp) / "result.json"
            log.write_text(PREFIX + json.dumps(record) + "\n", encoding="utf-8")
            self.assertEqual(main([str(log), str(out)]), 0)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), record)

    def test_ci_uses_real_blender_script_and_strict_parser(self):
        workflow = (ROOT / ".github/workflows/blender-smoke.yml").read_text("utf-8")
        script = (ROOT / "scripts/blender_undo_redo_smoke.py").read_text("utf-8")
        self.assertIn("scripts/blender_undo_redo_smoke.py", workflow)
        self.assertIn("python -m cbdk.undo_probe_report", workflow)
        self.assertIn("bpy.ops.ed.undo.poll()", script)
        self.assertIn("bpy.ops.ed.redo.poll()", script)
        self.assertIn("bpy.ops.cbdk.modular_vertex_nudge(", script)
        self.assertIn("--factory-startup", workflow)
        self.assertIn("SCRIPT_DIR = Path(__file__).resolve().parent", script)
        self.assertIn("sys.path.insert(0, str(SCRIPT_DIR))", script)


if __name__ == "__main__":
    unittest.main()
