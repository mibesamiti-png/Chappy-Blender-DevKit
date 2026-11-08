"""R11: static source snapshots are versioned observations, never trust."""
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import test_extension_source_reference_round10 as r10
from cbdk.extension_preflight import inspect_preview_archive


class ExtensionSourceReferenceRound11Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = r10.ExtensionSourceReferenceRound10Tests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work

    def snapshot(self, archive):
        package = inspect_preview_archive(archive)['package_id']
        with ZipFile(archive) as z:
            included = {n.removeprefix(package+'/') for n in z.namelist()}
        return package, r10._current_reference_snapshot(package, included)

    def test_legal_checkout_update_and_rehashed_zip_are_indistinguishable(self):
        original = self.fixture.build('modular_all')
        package, before = self.snapshot(original)
        changed, member, payload = self.fixture.mutate(
            original, 'modular_all', inventory_hash=True, part_hashes=True)
        checkout = self.work/'synthetic-checkout'
        source = r10.PACKAGE_SOURCES[package][member]
        path = checkout/source
        path.parent.mkdir(parents=True)
        path.write_bytes(before[member])
        with patch.object(r10, 'FIXED_REPO_ROOT', checkout):
            first = r10._read_fixed_repository_source(source, root=checkout)
            path.write_bytes(payload)  # lawful synthetic checkout edit
            second = r10._read_fixed_repository_source(source, root=checkout)
        self.assertNotEqual(first, second)
        after = dict(before, **{member: second})
        for archive, snapshot, expected in (
            (original, before, 'same_known_repo_bytes'),
            (original, after, 'different_known_repo_bytes'),
            (changed, before, 'different_known_repo_bytes'),
            (changed, after, 'same_known_repo_bytes'),
        ):
            report = r10._compare_bounded_preview(archive, snapshot)
            self.assertEqual(report['status'], expected)
            self.fixture.assert_sanitized_and_blocked(report)
        # A mismatch alone cannot tell update timing from tampering. No
        # timestamp or self-declared commit in a ZIP can settle that question.
        self.assertEqual(path.read_bytes(), payload)

    def test_crlf_checkout_normalizes_but_rehashed_crlf_zip_is_byte_different(self):
        original = self.fixture.build('mesh_inspector')
        package, references = self.snapshot(original)
        member = next(iter(references))
        source = r10.PACKAGE_SOURCES[package][member]
        checkout = self.work/'newline-checkout'
        path = checkout/source
        path.parent.mkdir(parents=True)
        lf = references[member]
        self.assertIn(b'\n', lf)
        crlf = lf.replace(b'\n', b'\r\n')
        path.write_bytes(crlf)
        with patch.object(r10, 'FIXED_REPO_ROOT', checkout):
            self.assertEqual(r10._read_fixed_repository_source(source, root=checkout), lf)
        self.assertEqual(path.read_bytes(), crlf)
        target = self.work/'crlf-preview.zip'
        with ZipFile(original) as z:
            prefix = package+'/'
            meta = json.loads(z.read(prefix+'CBDK_BUILD_INFO.json'))
            digest = hashlib.sha256(crlf).hexdigest()
            meta['files_sha256'][member] = digest
            for part in meta['parts']:
                if r10.SOURCES[part['source']] == member:
                    part['sha256'] = digest
            with ZipFile(target, 'x') as out:
                for info in z.infolist():
                    data = (crlf if info.filename == prefix+member else
                            json.dumps(meta).encode() if info.filename == prefix+'CBDK_BUILD_INFO.json'
                            else z.read(info.filename))
                    out.writestr(info, data)
        self.assertTrue(inspect_preview_archive(target)['provenance_hashes_verified'])
        report = r10._compare_bounded_preview(target, references)
        self.assertEqual(report['entries_different'], 1)
        self.fixture.assert_sanitized_and_blocked(report)

    def test_case_alias_unknown_root_and_reference_inventory_rejected(self):
        original = self.fixture.build('modular_all')
        package, references = self.snapshot(original)
        member = next(iter(references))
        changed = dict(references)
        changed[member.upper()] = changed.pop(member)
        with self.assertRaises(ValueError):
            r10._compare_bounded_preview(original, changed)
        source = r10.PACKAGE_SOURCES[package][member]
        for alias in (source.upper(), './'+source, 'unknown/source.py'):
            with self.assertRaises(ValueError):
                r10._read_fixed_repository_source(alias)
        with self.assertRaises(ValueError):
            r10._read_fixed_repository_source(source, root=self.work)

    def test_symlink_parent_escape_is_rejected_without_reading_payload(self):
        checkout = self.work/'bounded-root'
        checkout.mkdir()
        outside = self.work/'outside'
        outside.mkdir()
        source = sorted(r10.ALLOWLISTED_REPO_SOURCES)[0]
        relative = Path(source)
        # Redirect the first directory to a sibling containing the expected
        # remaining path. It exists and is small, but is outside trusted root.
        payload = outside/Path(*relative.parts[1:])
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(b'# CBDK synthetic private-like marker\n')
        try:
            (checkout/relative.parts[0]).symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation unavailable; no escape proof on this host')
        with patch.object(r10, 'FIXED_REPO_ROOT', checkout):
            with patch.object(Path, 'open', side_effect=AssertionError('must not read escape')):
                with self.assertRaisesRegex(ValueError, '^Known source is missing or unsafe$'):
                    r10._read_fixed_repository_source(source, root=checkout)
        self.assertEqual(payload.read_bytes(), b'# CBDK synthetic private-like marker\n')
