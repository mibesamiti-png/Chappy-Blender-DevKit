import hashlib
import tempfile
import unittest
from pathlib import Path

from cbdk.scanner import scan
from cbdk.dedup import duplicates


class InputIsolationTests(unittest.TestCase):
    def test_original_files_unmodified_and_duplicates_not_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'source.py'
            original = 'def first():\n    return 5\n\ndef second():\n    return 5\n'
            file.write_text(original)
            before = hashlib.sha256(file.read_bytes()).hexdigest()
            catalog = scan([tmp])
            results = duplicates(catalog)
            after = hashlib.sha256(file.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(len(results['exact_groups']), 1)
            self.assertEqual(len(catalog['symbols']), 2)

    def test_no_source_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'pwned.txt'
            src = root / 'unsafe.py'
            src.write_text(f'from pathlib import Path\nPath({str(marker)!r}).write_text("BAD")\ndef innocent():\n    return 1\n')
            scan([root])
            self.assertFalse(marker.exists())

if __name__ == '__main__':
    unittest.main()
