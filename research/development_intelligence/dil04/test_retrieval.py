import unittest,json
from pathlib import Path
from retrieval import all_context,metadata_only,fts_only,hybrid,bundle,input_bytes,_terms
ROOT=Path(__file__).parent
D=json.loads((ROOT/'corpus.json').read_text(encoding='utf8'))

class TestRetrieval(unittest.TestCase):
 def q(self,project='model',topics=None,query='自己交差',max_docs=3):
  return {'project':project,'topics':topics or [],'query':query,'max_docs':max_docs}
 def test_metadata_lookup(self):self.assertEqual([x['id'] for x in metadata_only(D,self.q(topics=['ci']))],['model-ci-r2'])
 def test_metadata_two_topics(self):self.assertEqual({x['topic'] for x in metadata_only(D,self.q(topics=['ci','privacy']))},{'ci','privacy'})
 def test_no_tags_falls_back(self):self.assertEqual([x['id'] for x in hybrid(D,self.q())],['model-geometry-r2'])
 def test_long_japanese_word(self):self.assertEqual([x['id'] for x in fts_only(D,self.q(query='私有ファイル'))],['model-privacy-r2'])
 def test_project_boundary(self):self.assertTrue(all(x['project']=='laser' for x in hybrid(D,self.q('laser',query='中断再開'))))
 def test_no_retired(self):self.assertTrue(all(x['revision']=='current' for x in hybrid(D,self.q(query='中断再開'))))
 def test_public_only(self):self.assertTrue(all(x['visibility']=='public_synthetic' for x in hybrid(D,self.q(query='自己交差'))))
 def test_unmatched_query_returns_empty(self):self.assertEqual(hybrid(D,self.q(query='不明な専門用語xyz')),[])
 def test_short_query_cannot_match_trigram(self):self.assertEqual(hybrid(D,self.q(query='AB')),[])
 def test_query_lexing_safe_quotes(self):self.assertIsInstance(_terms('"hello" OR X'),list)
 def test_input_no_summary(self):self.assertEqual(bundle(D[:1])[0]['text'],D[0]['text'])
 def test_full_baseline_large(self):self.assertGreater(input_bytes(all_context(D,self.q())),input_bytes(hybrid(D,self.q())))
 def test_does_not_mutate_corpus(self):
  old=json.dumps(D,ensure_ascii=False);hybrid(D,self.q());self.assertEqual(json.dumps(D,ensure_ascii=False),old)
 def test_limit(self):self.assertEqual(len(hybrid(D,self.q(topics=['ci','privacy'],max_docs=1))),1)

if __name__=='__main__':unittest.main()
