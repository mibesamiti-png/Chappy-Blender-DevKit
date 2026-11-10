"""DIL-02 repeatable synthetic comparison; frozen after first holdout run."""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
from decision_gate import decide, idea_first, quality_max, admissible

ROOT = Path(__file__).resolve().parent


def load_and_verify():
    freeze = json.loads((ROOT / 'FREEZE.json').read_text(encoding='utf-8'))
    for path, expected in freeze['sha256'].items():
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('modified after freeze: ' + path)
    return freeze


def score(rows, fn):
    correct = violations = unnecessary = 0
    details = []
    for row in rows:
        output = fn(row)
        ok = output['action'] == row['gold']['action'] and output['option'] == row['gold']['option']
        correct += ok
        option = next((o for o in row['options'] if o['id'] == output['option']), None)
        if output['action'] == 'choose' and (option is None or not admissible(option, row['budget'])):
            violations += 1
        done = row['accepted_revision'] == row['goal_revision'] and row['checks_passed'] and row['evidence_fresh']
        if done and output['action'] != 'stop':
            unnecessary += 1
        details.append({'id': row['id'], 'gold': row['gold'], 'actual': {'action': output['action'], 'option': output['option']}, 'pass': ok})
    return {'correct': correct, 'total': len(rows), 'constraint_violations': violations,
            'unnecessary_after_acceptance': unnecessary, 'details': details}


def run():
    freeze = load_and_verify()
    out = {'experiment': 'DIL-02', 'synthetic_only': True, 'source_sha256': freeze['sha256'],
           'python': platform.python_version(), 'platform': platform.platform(), 'splits': {}}
    for split in ('development', 'holdout'):
        rows = json.loads((ROOT / 'fixtures' / (split + '.json')).read_text(encoding='utf-8'))
        out['splits'][split] = {name: score(rows, fn) for name, fn in
                                [('idea_first', idea_first), ('quality_max', quality_max), ('decision_gate', decide)]}
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    t0 = time.perf_counter()
    result = run()
    result['run_wall_seconds'] = time.perf_counter() - t0
    with open(args.output, 'x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({split: {name: {k: v for k, v in data.items() if k != 'details'}
                              for name, data in block.items()}
                      for split, block in result['splits'].items()}, indent=2))
