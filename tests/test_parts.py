import tempfile
import unittest
from pathlib import Path

from parts.common.safe_path import sanitize_filename, unique_filename


class SafePathTests(unittest.TestCase):
    def test_reserved_names_and_invalid_characters(self):
        self.assertEqual(sanitize_filename('CON.txt'), '_CON.txt')
        self.assertEqual(sanitize_filename('a/b:c'), 'a_b_c')
        self.assertEqual(sanitize_filename('  '), 'Object')

    def test_unique_file(self):
        with tempfile.TemporaryDirectory() as path:
            p = Path(path)
            (p / 'part.stl').touch()
            self.assertEqual(unique_filename(p, 'part', 'stl'), p / 'part_1.stl')


if __name__ == '__main__':
    unittest.main()
