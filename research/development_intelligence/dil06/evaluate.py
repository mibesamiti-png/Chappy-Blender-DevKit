"""One reproducible research evaluation. No network, no production actions."""
import argparse
import hashlib
import json
from pathlib import Path

from measure import analyze_snapshot

ROOT = Path(__file__).parent

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    manifest=json.loads((ROOT/'FREEZE.json').read_text(encoding='utf-8'))
    for path, expected in manifest['sha256'].items():
        actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if actual!=expected:
            raise SystemExit(f'frozen_source_mismatch:{path}')
    snapshot=json.loads((ROOT/'observed.json').read_text(encoding='utf-8'))
    report=analyze_snapshot(snapshot)
    output=args.output
    with output.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'complete_rounds':report['observable_complete_rounds'],
                      'rounds':[{"round":r['round'],"gap_seconds":r['ci_to_integration_pr_publication_gap_seconds'],"blockers":r['blockers']} for r in report['rounds']]},indent=2))

if __name__=='__main__':
    main()
