import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from r25_stage_observer import STAGE_PREFIX, stage_record, parse_records, finish_failure
from cbdk.extension_stage_evidence import STAGES, reduce_stage_records


class R25StageTransportTests(unittest.TestCase):
    def test_missing_child_is_not_fabricated_failure(self):
        rows = [stage_record("grouped", "4.4.3", "a"*32, "b"*64, stage, "passed")
                for stage in STAGES[:2]]
        finish_failure(rows)
        self.assertEqual(len(rows), 2)
        self.assertEqual(reduce_stage_records(rows, case="grouped", blender="4.4.3",
                         run_id="a"*32)["status"], "incomplete")

    def test_explicit_failure_and_not_run(self):
        rows = [stage_record("grouped", "4.4.3", "a"*32, "b"*64, stage,
                             "failed" if stage == "enable" else "passed")
                for stage in STAGES[:3]]
        finish_failure(rows)
        self.assertEqual([r["status"] for r in rows], ["passed", "passed", "failed",
                         "not_run", "not_run", "not_run"])
        self.assertEqual(reduce_stage_records(rows, case="grouped", blender="4.4.3",
                         run_id="a"*32)["failure_reason"], "enable_failed")

    def test_strict_transport(self):
        row = stage_record("read", "4.4.3", "a"*32, "b"*64, "enable", "passed")
        log = STAGE_PREFIX + json.dumps(row)
        self.assertEqual(parse_records(log, STAGE_PREFIX, max_records=3), [row])
        for bad in (STAGE_PREFIX + '{"case":"read","case":"edit"}',
                    STAGE_PREFIX + 'null', "\n".join([log]*4)):
            with self.assertRaises(ValueError):
                parse_records(bad, STAGE_PREFIX, max_records=3)
