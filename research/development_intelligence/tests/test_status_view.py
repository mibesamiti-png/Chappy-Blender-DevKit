import copy,json,unittest
from pathlib import Path
from prototype.status_view import observe
ROOT=Path(__file__).resolve().parents[1]

class ObservationTests(unittest.TestCase):
    def test_development_labels(self):
        for row in json.loads((ROOT/'fixtures/development.json').read_text()):
            with self.subTest(row['id']):
                self.assertEqual(observe(row['record'],row['expected'],row['now'])['recently_observed'],row['gold_recently_observed'])
    def test_no_mutation_or_authority(self):
        row=json.loads((ROOT/'fixtures/development.json').read_text())[0];before=copy.deepcopy(row)
        result=observe(row['record'],row['expected'],row['now'])
        self.assertEqual(row,before);self.assertFalse(result['edit_authorized']);self.assertIsNone(result['eta'])
    def test_schema_rejection_no_raw_diagnostics(self):
        row=json.loads((ROOT/'fixtures/development.json').read_text())[0]
        row['record']['private_path']='DO_NOT_ECHO'
        result=observe(row['record'],row['expected'],row['now'])
        self.assertEqual(result['state'],'invalid');self.assertNotIn('DO_NOT_ECHO',json.dumps(result))
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):observe({}, {}, True)
        with self.assertRaises(ValueError):observe({}, {}, 1000,heartbeat_ttl=400)
