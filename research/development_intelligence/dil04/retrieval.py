"""DIL-04 synthetic evidence retrieval; no AI, no trusted state changes."""
from __future__ import annotations
from contextlib import closing
import sqlite3
import re


def _live(d):
    return d['status'] == 'approved' and d['revision'] == 'current' and d['visibility'] == 'public_synthetic'


def _ordered(docs):
    return sorted(docs, key=lambda d: d['id'])


def _eligible(docs, query):
    return _ordered([d for d in docs if d['project'] == query['project'] and _live(d)])


def all_context(docs, query):
    """Full input baseline: indiscriminately submit all docs (including retired)."""
    return _ordered(docs)


def metadata_only(docs, query):
    """No text search: precise when the caller has structured topic labels."""
    need = set(query['topics'])
    if not need:
        return []
    return [d for d in _eligible(docs, query) if d['topic'] in need][:query['max_docs']]


def _terms(text):
    """Very small query lexer; quotes and Boolean FTS syntax never exposed."""
    return list(dict.fromkeys(w.lower() for w in re.findall(r'[\w\u3040-\u30ff\u3400-\u9fff-]{3,}', text) if len(w)>=3))[:6]


def _fts_records(docs, query):
    """FTS5 trigram on synthetic approved/active documents of the requested project."""
    terms = _terms(query['query'])
    if not terms:
        return []
    with closing(sqlite3.connect(':memory:')) as con:
        con.execute("CREATE VIRTUAL TABLE knowledge USING fts5(content, tokenize='trigram')")
        rows = _eligible(docs, query)
        con.executemany('INSERT INTO knowledge(rowid,content) VALUES (?,?)',
                        [(i+1, d['title']+' '+d['text']+' '+ ' '.join(d['aliases'])) for i,d in enumerate(rows)])
        # Whole snippets as FTS quoted phrases; all search strings are bound parameters.
        fts_query=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
        ids=con.execute('SELECT rowid FROM knowledge WHERE knowledge MATCH ? ORDER BY bm25(knowledge),rowid LIMIT ?',
                        (fts_query, query['max_docs'])).fetchall()
        return [rows[i-1] for (i,) in ids]


def fts_only(docs, query):
    try:
        return _fts_records(docs, query)
    except sqlite3.OperationalError as exc:
        if 'no such module: fts5' in str(exc) or 'no such tokenizer: trigram' in str(exc):
            raise RuntimeError('FTS5 trigram unavailable') from exc
        raise


def hybrid(docs, query):
    """Fast path on metadata. FTS only when no topic key is supplied.

    No opaque generated summary; original evidence + metadata returned.
    This prototype cannot know if structured labels are wrong or incomplete.
    """
    if query['topics']:
        return metadata_only(docs, query)
    return fts_only(docs, query)


def bundle(docs):
    """Exact source text + explicit version/provenance, no summary rewriting."""
    return [{'id':d['id'],'source':d['source'],'revision':d['revision'],
             'status':d['status'],'text':d['text']} for d in docs]


def input_bytes(docs):
    import json
    return len(json.dumps(bundle(docs),ensure_ascii=False,separators=(',',':')).encode('utf-8'))
