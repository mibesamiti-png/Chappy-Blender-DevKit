"""Load commit/blob-pinned public CBDK docs from an existing local git checkout.

This never checks out, modifies or writes the source repo. Source git objects must
already exist locally; network access and GitHub credentials are not required.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def git_bytes(repo, commit, path):
    if not path or path.startswith('/') or '..' in Path(path).parts or '\\' in path:
        raise ValueError('unsafe public repository path')
    return subprocess.check_output(['git', '-C', str(repo), 'show', f'{commit}:{path}'])


def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def load_corpus(repo, manifest=None):
    m = manifest or json.loads((ROOT / 'manifest.json').read_text(encoding='utf8'))
    sha = m['source_commit']
    if len(sha) != 40 or any(ch not in '0123456789abcdef' for ch in sha):
        raise ValueError('source commit must be a full SHA1')
    known_ids = set()
    out = []
    for d in m['documents']:
        if d['id'] in known_ids:
            raise ValueError('duplicate document id')
        known_ids.add(d['id'])
        raw = git_bytes(repo, sha, d['path'])
        if git_blob_sha(raw) != d['blob_sha']:
            raise ValueError(f'blob SHA mismatch for {d["path"]}')
        body = raw.decode('utf8')
        out.append({
            'id': d['id'], 'project': 'CBDK', 'topic': d['topic'],
            'title': d['path'], 'source': f'https://github.com/{m["repository"]}/blob/{sha}/{d["path"]}',
            'text': body, 'aliases': [],
            # Adapter fields required by frozen DIL-04 prototype. "approved" is NOT
            # a licensing, deployment, or release approval, just an eligibility flag.
            'status': 'approved',
            'revision': 'current' if d['current'] else 'historical',
            'visibility': 'public_synthetic',
        })
    return out


def check_gold(cases, docs):
    by_id = {d['id']: d for d in docs}
    for c in cases:
        if not c['gold_ids'] or len(c['gold_ids']) != len(set(c['gold_ids'])):
            raise ValueError('empty or repeated gold ids')
        for doc_id in c['gold_ids']:
            if doc_id not in by_id or by_id[doc_id]['revision'] != 'current':
                raise ValueError(f'unknown or historical gold: {c["id"]} {doc_id}')
            anchor = c['anchors'].get(doc_id)
            if not anchor or anchor not in by_id[doc_id]['text']:
                raise ValueError(f'mandatory source anchor absent: {c["id"]} {doc_id}')
