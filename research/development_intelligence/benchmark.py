"""Offline synthetic evidence classification, no external data acquisition."""
import argparse,hashlib,json,platform,statistics,time,tracemalloc
from pathlib import Path
from prototype.status_view import observe
ROOT=Path(__file__).resolve().parent


def status_only(r,e,n):
    return r.get('status')=='running'


def ttl_only(r,e,n):
    t=r.get('updated_at')
    return status_only(r,e,n) and type(t) is int and 0<=n-t<=300


def bound(r,e,n):
    return observe(r,e,n)['recently_observed']


def run():
    frozen=json.loads((ROOT/'FROZEN.json').read_text())
    for name,sha in frozen['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha, name
    out=dict(python=platform.python_version(),platform=platform.system(),synthetic_only=True,
             trials=7,iterations_per_trial=100,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*.py'))},splits={})
    for split in ('development','holdout'):
        rows=json.loads((ROOT/'fixtures'/f'{split}.json').read_text());summary={}
        for name,fn in [('status_only',status_only),('ttl_only',ttl_only),('bound_evidence',bound)]:
            values=[fn(r['record'],r['expected'],r['now']) for r in rows]
            fp=sum(v and not r['gold_recently_observed'] for v,r in zip(values,rows))
            fn_count=sum(not v and r['gold_recently_observed'] for v,r in zip(values,rows))
            timings=[]
            for _ in range(7):
                start=time.perf_counter()
                for _ in range(100):
                    for r in rows:fn(r['record'],r['expected'],r['now'])
                timings.append((time.perf_counter()-start)/(100*len(rows)))
            tracemalloc.start()
            for r in rows:fn(r['record'],r['expected'],r['now'])
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            summary[name]=dict(false_positive=fp,false_negative=fn_count,total=len(rows),median_seconds_per_record=statistics.median(timings),samples=timings,python_peak_bytes=peak)
        out['splits'][split]=summary
    out['holdout_details']=[dict(id=r['id'],expected=r['gold_recently_observed'],result=observe(r['record'],r['expected'],r['now'])) for r in rows]
    out['record_bytes']=[len(json.dumps(r['record'],separators=(',',':')).encode()) for r in rows]
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    result=run()
    with open(a.output,'x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result['splits'],indent=2))
