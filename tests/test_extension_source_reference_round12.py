"""R12 test-only snapshot basis and native filesystem probes; no code exec."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import test_extension_source_reference_round10 as r10


BASIS_COMMIT = 'faab6ab023f50495c719d091b29f320aa6ab36df'


def snapshot_basis(references, commit):
    """Test-only independent reference descriptor, not ZIP self-assertion."""
    if (not isinstance(commit, str) or len(commit) != 40
            or any(c not in '0123456789abcdef' for c in commit)):
        raise ValueError('Unknown reference commit')
    digest = hashlib.sha256(json.dumps(
        {key: hashlib.sha256(value).hexdigest()
         for key, value in sorted(references.items())},
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'commit': commit, 'normalization': 'checkout_crlf_to_lf_zip_exact',
            'inventory_sha256': digest}


def compare_at_basis(archive, references, recorded, expected):
    if (not isinstance(recorded, dict) or recorded != expected
            or recorded != snapshot_basis(references, recorded.get('commit'))):
        return {'status': 'inconclusive_reference_basis',
                'release_authorized': False, 'source_authenticity_verified': False,
                'python_code_executed': False}
    return r10._compare_bounded_preview(archive, references)


class R12SourceBasisTests(unittest.TestCase):
    def setUp(self):
        self.fixture = r10.ExtensionSourceReferenceRound10Tests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work.resolve()
        # Canonicalize BEFORE binding FIXED_REPO_ROOT, including Windows
        # short-name/junction aliases in the runner temporary directory.
        self.root = (self.work/'CBDK R12 Synthetic Checkout Long Name').resolve()
        self.root.mkdir()
        self.source = sorted(r10.ALLOWLISTED_REPO_SOURCES)[0]
        self.path = self.root/self.source
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'# CBDK synthetic inert source\r\n')

    def read(self, root=None):
        with patch.object(r10, 'FIXED_REPO_ROOT', self.root):
            return r10._read_fixed_repository_source(
                self.source, root=self.root if root is None else root)

    def test_snapshot_basis_is_independent_and_mismatch_inconclusive(self):
        archive = self.fixture.build('modular_all')
        package = r10.inspect_preview_archive(archive)['package_id']
        with ZipFile(archive) as z:
            included = {n.removeprefix(package+'/') for n in z.namelist()}
        refs = r10._current_reference_snapshot(package, included)
        basis = snapshot_basis(refs, BASIS_COMMIT)
        original = compare_at_basis(archive, refs, basis, basis)
        self.assertEqual(original['status'], 'same_known_repo_bytes')
        self.fixture.assert_sanitized_and_blocked(original)
        for altered in (None, {}, dict(basis, commit='0'*40),
                        dict(basis, normalization='unknown'),
                        dict(basis, inventory_sha256='0'*64)):
            report = compare_at_basis(archive, refs, altered, basis)
            self.assertEqual(report['status'], 'inconclusive_reference_basis')
            self.assertFalse(report['release_authorized'])
        changed, member, payload = self.fixture.mutate(
            archive, 'modular_all', inventory_hash=True, part_hashes=True)
        after = dict(refs, **{member: payload})
        # Both a lawful checkout update and ZIP tampering compare unequal
        # to the other snapshot; neither mismatch explains its own cause.
        for candidate, reference in ((archive, after), (changed, refs)):
            current_basis = snapshot_basis(reference, BASIS_COMMIT)
            report = compare_at_basis(candidate, reference, current_basis, current_basis)
            self.assertEqual(report['status'], 'different_known_repo_bytes')
            self.fixture.assert_sanitized_and_blocked(report)
        self.assertNotEqual(snapshot_basis(after, BASIS_COMMIT), basis)

    def test_canonical_root_newlines_unknown_root_and_source_case(self):
        self.assertEqual(self.read(), b'# CBDK synthetic inert source\n')
        self.assertEqual(self.path.read_bytes(), b'# CBDK synthetic inert source\r\n')
        with self.assertRaises(ValueError):
            self.read(self.work)
        for alias in (self.source.upper(), './'+self.source, '../unknown.py'):
            with patch.object(r10, 'FIXED_REPO_ROOT', self.root):
                with self.assertRaises(ValueError):
                    r10._read_fixed_repository_source(alias, root=self.root)

    def test_leaf_symlink_outside_root_is_rejected_before_open(self):
        outside = self.work/'outside-source.py'
        outside.write_bytes(b'# CBDK outside fixture\n')
        self.path.unlink()
        try:
            self.path.symlink_to(outside)
        except OSError:
            self.skipTest('Leaf symlink permission unavailable')
        with patch.object(Path, 'open', side_effect=AssertionError('forbidden read')):
            with self.assertRaisesRegex(ValueError, 'Known source is missing or unsafe'):
                self.read()
        self.assertEqual(outside.read_bytes(), b'# CBDK outside fixture\n')

    def test_parent_symlink_escape_is_rejected_before_open(self):
        self._directory_escape(junction=False)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction probe only')
    def test_windows_junction_escape_is_rejected_before_open(self):
        self._directory_escape(junction=True)

    def _directory_escape(self, junction):
        root = (self.work/('junction-root' if junction else 'symlink-root')).resolve()
        root.mkdir()
        outside = self.work/'outside-tree'
        outside.mkdir(exist_ok=True)
        parts = Path(self.source).parts
        target = outside/Path(*parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'# CBDK outside fixture\n')
        link = root/parts[0]
        if junction:
            result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J',
                                     str(link), str(outside)], capture_output=True)
            if result.returncode:
                self.skipTest('Windows junction creation unavailable')
        else:
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Parent symlink permission unavailable')
        try:
            with patch.object(r10, 'FIXED_REPO_ROOT', root):
                with patch.object(Path, 'open', side_effect=AssertionError('forbidden read')):
                    with self.assertRaisesRegex(ValueError, 'Known source is missing or unsafe'):
                        r10._read_fixed_repository_source(self.source, root=root)
        finally:
            # Remove only link/junction, never recurse into the sibling target.
            if junction:
                link.rmdir()
            else:
                link.unlink()
        self.assertEqual(target.read_bytes(), b'# CBDK outside fixture\n')

    @unittest.skipUnless(os.name == 'nt', 'Windows root alias probe only')
    def test_windows_short_name_and_case_alias_root_are_canonicalized(self):
        self.assertEqual(self.read(Path(str(self.root).swapcase())), self.read())
        function = ctypes.windll.kernel32.GetShortPathNameW
        function.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        function.restype = ctypes.c_uint
        size = function(str(self.root), None, 0)
        if not size:
            self.skipTest('Windows short-path lookup unavailable (case alias tested)')
        buffer = ctypes.create_unicode_buffer(size)
        count = function(str(self.root), buffer, size)
        self.assertGreater(count, 0)
        self.assertLess(count, size)
        short = Path(buffer.value)
        if str(short).casefold() == str(self.root).casefold():
            self.skipTest('8.3 short names disabled (case alias tested)')
        self.assertEqual(self.read(short), self.read())
