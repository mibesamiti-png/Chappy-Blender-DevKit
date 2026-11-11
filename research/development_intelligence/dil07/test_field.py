import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import snapshot


class TestPinnedEvidence(unittest.TestCase):
    def test_git_sha(self):
        data = b'Hello!'
        self.assertEqual(snapshot.git_blob_sha(data),
                         __import__('hashlib').sha1(b'blob 6\0Hello!').hexdigest())

    def test_reject_traversal(self):
        for path in ('../foo', '/etc/passwd', 'dir/../../file', 'a\\b'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    snapshot.git_bytes(Path('.'), 'a'*40, path)

    def test_incorrect_sha_fails_closed(self):
        d = {'repository': 'x/y', 'source_commit': 'a'*40,
             'documents':[{'id':'one','path':'docs/test.md','blob_sha':'0'*40,
                           'topic':'policy','current':True}]}
        with patch.object(snapshot, 'git_bytes', return_value=b'data'):
            with self.assertRaisesRegex(ValueError, 'blob SHA mismatch'):
                snapshot.load_corpus('.', d)

    def test_duplicate_ids_refused(self):
        d = {'repository': 'x/y', 'source_commit': 'a'*40,
             'documents':[{'id':'one','path':'docs/test.md','blob_sha':snapshot.git_blob_sha(b'data'),
                           'topic':'policy','current':True}]*2}
        with patch.object(snapshot, 'git_bytes', return_value=b'data'):
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                snapshot.load_corpus('.', d)

    def test_invalid_commit(self):
        with self.assertRaises(ValueError):
            snapshot.load_corpus('.', {'source_commit':'main','documents':[]})

    def test_gold_anchor_required(self):
        docs = [{'id':'r16','revision':'current','text':'R16 valid'}]
        ok = [{'id':'Q','gold_ids':['r16'],'anchors':{'r16':'R16'}}]
        snapshot.check_gold(ok, docs)
        for c in [{'id':'Q','gold_ids':['r16'],'anchors':{'r16':'absent'}},
                  {'id':'Q','gold_ids':['r15'],'anchors':{'r15':'R15'}},
                  {'id':'Q','gold_ids':[],'anchors':{}}]:
            with self.assertRaises(ValueError):
                snapshot.check_gold([c], docs)

    def test_historical_gold_rejected(self):
        with self.assertRaises(ValueError):
            snapshot.check_gold([{'id':'Q','gold_ids':['old'],'anchors':{'old':'R15'}}],
                                [{'id':'old','revision':'historical','text':'R15'}])

    def test_source_not_modified(self):
        m = {'repository': 'x/y', 'source_commit':'a'*40,
             'documents':[{'id':'x','path':'docs/test.md','blob_sha':snapshot.git_blob_sha(b'data'),
                           'topic':'policy','current':True}]}
        with patch.object(snapshot, 'git_bytes', return_value=b'data'):
            before = json.dumps(m)
            result = snapshot.load_corpus('.', m)
            self.assertEqual(json.dumps(m), before)
            self.assertEqual(result[0]['text'], 'data')
            self.assertIn('/blob/'+'a'*40+'/', result[0]['source'])


    def test_historical_is_excluded_by_dil04(self):
        from evaluate import metadata_only, all_context
        d = [{'id':'old','project':'CBDK','topic':'round','status':'approved',
              'revision':'historical','visibility':'public_synthetic'},
             {'id':'new','project':'CBDK','topic':'round','status':'approved',
              'revision':'current','visibility':'public_synthetic'}]
        q = {'project':'CBDK','topics':['round'],'max_docs':12,'query':'R16'}
        self.assertEqual([x['id'] for x in metadata_only(d, q)], ['new'])
        self.assertEqual(len(all_context(d, q)), 2)

    def test_mistagged_topic_yields_absence_not_permission(self):
        from evaluate import hybrid
        d = [{'id':'new','project':'CBDK','topic':'round','status':'approved',
              'revision':'current','visibility':'public_synthetic'}]
        self.assertEqual(hybrid(d, {'project':'CBDK','topics':['incorrect'],
                                    'max_docs':12,'query':'R16'}), [])

    def test_fts_matches_exact_unstructured_phrase(self):
        from evaluate import fts_only
        d = [{'id':'new','project':'CBDK','topic':'round','status':'approved',
              'revision':'current','visibility':'public_synthetic',
              'title':'R16','text':'R16実装を開始しない','aliases':[]}]
        q={'project':'CBDK','topics':[],'query':'R16','max_docs':12}
        self.assertEqual([x['id'] for x in fts_only(d,q)],['new'])

    def test_frozen_dil04_is_exact_blob(self):
        from evaluate import DIL04
        self.assertEqual(snapshot.git_blob_sha((DIL04/'retrieval.py').read_bytes()),
                         '6d2ab052ff3ba40a16fb99288e82a0a646624c58')

if __name__ == '__main__':
    unittest.main()
