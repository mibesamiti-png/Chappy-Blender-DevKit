"""DIL-03 synthetic fault trace comparison, freeze-checked before execution."""
import argparse
import hashlib
import json
import platform
import tempfile
from pathlib import Path
from handoff import Store, ReferenceStore, simulate

ROOT=Path(__file__).resolve().parent

def verify_freeze():
    manifest=json.loads((ROOT/'FREEZE.json').read_text(encoding='utf-8'))
    for path,sha in manifest['sha256'].items():
        actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if actual != sha:
            raise ValueError('freeze SHA256 mismatch: '+path)
    return manifest

def evaluate(rows,method):
    count=0
    missed_events=0
    bad_states=0
    bad_recoveries=0
    cases=[]
    for row in rows:
        with tempfile.TemporaryDirectory() as directory:
            store=(Store(Path(directory)/'synthetic.db') if method=='guarded_sqlite'
                   else ReferenceStore(revision_cas=(method=='owner_revision')))
            try:
                actual=simulate(store,row)
            finally:
                store.close()
        gold=row['gold']
        event_match=actual['statuses']==gold['statuses']
        state_match=actual['state']==gold['state']
        recovery_match=actual['recovery']==gold['recovery']
        ok=event_match and state_match and recovery_match
        count+=ok
        missed_events+=not event_match
        bad_states+=not state_match
        bad_recoveries+=not recovery_match
        cases.append(dict(id=row['id'],pass_all=ok,event_match=event_match,state_match=state_match,recovery_match=recovery_match,actual=actual))
    return dict(pass_all=count,total=len(rows),wrong_event_cases=missed_events,wrong_final_state_cases=bad_states,wrong_recovery_cases=bad_recoveries,details=cases)

def run():
    freeze=verify_freeze()
    out={'study':'DIL-03','artificial_data_only':True,'model':'cooperative SQLite transaction+epoch+revision',
         'environment':{'python':platform.python_version(),'platform':platform.platform()},
         'freeze':freeze,'splits':{}}
    for split in ('development','holdout'):
        rows=json.loads((ROOT/'fixtures'/f'{split}.json').read_text(encoding='utf8'))
        out['splits'][split]={name:evaluate(rows,name) for name in ('owner_only','owner_revision','guarded_sqlite')}
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=run()
    with open(args.output,'x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:{n:{m:v for m,v in s.items() if m!='details'} for n,s in t.items()} for k,t in result['splits'].items()},indent=2))
