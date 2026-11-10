"""Data-only review keeps manifest values and paths out of generated reports."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.extension_manifest_review import review_manifest_file, write_manifest_review


class ManifestFileReviewTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / 'SECRET_manifest.toml'
        self.source.write_text('schema_version="1.0.0"\nmaintainer="Private Person email@example.invalid"\n'
                               '"PRIVATE_KEY_IDENTIFIER"="private value"\n', encoding='utf-8')

    def test_r7_limit_controls_do_not_claim_release_approval(self):
        """R7: exactly-on-budget TOML is review-only; oversized stays blocked."""
        from cbdk.extension_manifest_review import MAX_BYTES
        prefix = 'schema_version="1.0.0"\n# private-review-r7 '
        for size in (MAX_BYTES - 1, MAX_BYTES):
            with self.subTest(bytes=size):
                text = prefix + ("x" * (size - len(prefix)))
                self.source.write_bytes(text.encode("ascii"))
                self.assertEqual(self.source.stat().st_size, size)
                result = review_manifest_file(self.source)
                self.assertEqual(result["status"], "review_only")
                self.assertFalse(result["release_authorized"])
                self.assertFalse(result["official_validation_ran"])
                self.assertNotIn("private-review-r7", json.dumps(result))
        self.source.write_bytes((prefix + "x" * (MAX_BYTES + 1 - len(prefix))).encode("ascii"))
        with self.assertRaises(ValueError):
            review_manifest_file(self.source)

    def test_file_values_unknown_keys_and_paths_are_not_exposed(self):
        before = self.source.read_bytes()
        report = review_manifest_file(self.source)
        text = json.dumps(report)
        for secret in ('Private Person', 'email@example', 'PRIVATE_KEY_IDENTIFIER', str(self.source), 'private value'):
            self.assertNotIn(secret, text)
        self.assertFalse(report['source_executed'])
        self.assertFalse(report['release_authorized'])
        self.assertEqual(self.source.read_bytes(), before)

    def test_duplicates_and_oversize_are_rejected(self):
        for value in ('maintainer="private"\nmaintainer="again"', 'x="'+'p'*33000+'"',
                      'value='+'['*1200+'0'+']'*1200):
            self.source.write_text(value, encoding='utf-8')
            with self.assertRaises(ValueError):
                review_manifest_file(self.source)

    def test_source_and_destination_symlink_escapes_are_rejected(self):
        link = self.root / 'link.toml'
        try:
            link.symlink_to(self.source)
        except OSError:
            self.skipTest('Symlinks unavailable in this environment')
        with self.assertRaises(ValueError):
            review_manifest_file(link)
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'reports').mkdir()
        (self.root / 'reports/latest').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            write_manifest_review(self.source, 'reports/latest/leak.json', root=self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_outputs_are_fresh_and_local(self):
        output = 'reports/latest/manifest-review.json'
        report = write_manifest_review(self.source, output, root=self.root)
        saved = (self.root/output).read_bytes()
        self.assertEqual(json.loads(saved), report)
        with self.assertRaises(ValueError):
            write_manifest_review(self.source, output, root=self.root)
        self.assertEqual((self.root/output).read_bytes(), saved)
        for bad in ('docs/leak.json', 'reports/latest/../leak.json', str(self.root/'absolute.json')):
            with self.assertRaises(ValueError):
                write_manifest_review(self.source, bad, root=self.root)

    def test_cli_never_runs_source_or_prints_manifest_values(self):
        from cbdk.extension_manifest_review import write_manifest_review as writer
        with patch('cbdk.extension_manifest_review.write_manifest_review', side_effect=lambda s,o: writer(s,o,root=self.root)), \
             patch('subprocess.run') as runtime, contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main(['extension-manifest-review',str(self.source)]),0)
        runtime.assert_not_called()
        self.assertNotIn('Private Person',stdout.getvalue())
        self.assertNotIn(str(self.source),stdout.getvalue())
