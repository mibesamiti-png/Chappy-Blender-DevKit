"""One preregistered DIL-07 real-document study using unmodified DIL-04 engine."""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIL04 = ROOT.parent / 'dil04'
sys.path.insert(0, str(DIL04))
from retrieval import all_context, metadata_only, fts_only, hybrid, input_bytes  # noqa
from snapshot import load_corpus, check_gold, git_blob_sha  # noqa

ARMS = {'all_context': all_context, 'metadata_only': metadata_only,
        'fts5_trigram': fts_only, 'hybrid': hybrid}


def validate_freeze():
    freeze = json.loads((ROOT / 'FREEZE.json').read_text(encoding='utf8'))
    expected_dil04_blob = '6d2ab052ff3ba40a16fb99288e82a0a646624c58'
    if git_blob_sha((DIL04 / 'retrieval.py').read_bytes()) != expected_dil04_blob:
        raise ValueError('DIL-04 implementation changed: not the frozen original')
    for rel, sha in freeze['sha256'].items():
        raw = (ROOT / rel).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError(f'frozen file changed: {rel}')
    return freeze


def run(repo):
    frozen = validate_freeze()
    docs = load_corpus(repo)
    cases = json.loads((ROOT / 'cases.json').read_text(encoding='utf8'))
    check_gold(cases, docs)
    reports = {}
    for name, method in ARMS.items():
        found = exact = stale = bytes_total = 0
        details = []
        for c in cases:
            q = {'project': 'CBDK', 'topics': c['topics'],
                 'query': c['query'], 'max_docs': len(docs)}
            selected = method(docs, q)
            got = {x['id'] for x in selected}
            gold = set(c['gold_ids'])
            hit = gold & got
            old = sum(x['revision'] != 'current' for x in selected)
            nbytes = input_bytes(selected)
            found += len(hit)
            exact += int(got == gold)
            stale += old
            bytes_total += nbytes
            details.append({'question': c['id'], 'topics_present': bool(c['topics']),
                            'required': c['gold_ids'], 'found': sorted(got),
                            'missing': sorted(gold - got), 'historical_documents': old,
                            'bytes': nbytes,
                            'status': 'evidence_candidate_only' if gold.issubset(got) and old == 0 else 'needs_authoritative_source',
                            'can_authorize_merge': False, 'can_skip_ci': False})
        reports[name] = {'exact_docsets': exact, 'cases': len(cases),
                         'required_found': found, 'required_total': sum(len(x['gold_ids']) for x in cases),
                         'historical_returns': stale, 'input_bytes': bytes_total,
                         'details': details}
    hy = reports['hybrid']; baseline = reports['all_context']
    strong = hy['required_found'] == hy['required_total'] and hy['historical_returns'] == 0 \
        and hy['input_bytes'] <= baseline['input_bytes'] / 4
    return {'study': 'DIL-07', 'result': 'limited_transfer_pass' if strong else 'transfer_failed_not_ready',
            'source_commit': json.loads((ROOT / 'manifest.json').read_text())['source_commit'],
            'frozen_sha256': frozen['sha256'],
            'environment': {'python': platform.python_version(), 'sqlite': __import__('sqlite3').sqlite_version},
            'data': {'docs': len(docs), 'questions': len(cases), 'tagged_questions': sum(bool(c['topics']) for c in cases),
                     'synthetic': False, 'human_independent_gold': False, 'model_answer_accuracy_evaluated': False,
                     'real_user_queries': False},
            'methods': reports,
            'hybrid_vs_full_byte_ratio': hy['input_bytes'] / baseline['input_bytes'],
            'can_authorize_merge': False, 'can_skip_ci': False, 'product_adoption': False}


if __name__ == '__main__':
    arg = argparse.ArgumentParser()
    arg.add_argument('--repo', type=Path, required=True, help='local checkout containing frozen git objects')
    arg.add_argument('--output', type=Path, required=True)
    a = arg.parse_args()
    report = run(a.repo)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': report['result'], 'metrics': {
        k: {n:v for n,v in r.items() if n != 'details'} for k,r in report['methods'].items()}},
        ensure_ascii=False, indent=2))
