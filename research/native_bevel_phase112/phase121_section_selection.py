"""Research-only retrospective ranking. No product adoption. No partial section scores.
Compare at the same base-face budget and at several exploratory angle targets.
"""
import json, math, argparse
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TOL=1e-5
TARGETS=(15,20,30,45)

def candidate(m, n, label, config=None):
    if not m.get('complete') or m.get('valid')!=n or m.get('total')!=n:return None
    sec=m.get('sections',[])
    if len(sec)!=n or {r.get('section') for r in sec}!=set(range(n)) or any('error' in r for r in sec):return None
    vals=[m.get(k) for k in ('max_turn','p95_turn','mean_turn')]
    if any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=180+TOL for x in vals):return None
    if not isinstance(m.get('faces'),int) or m['faces']<=0:return None
    angles=[r.get('max_turn') for r in sec]
    if any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=180+TOL for x in angles):return None
    actual=[max(angles),float(np.percentile(angles,95)),sum(angles)/n]
    if any(abs(a-b)>TOL for a,b in zip(actual,vals)):return None
    return dict(label=label,config=config,faces=m['faces'],max_turn=vals[0],p95_turn=vals[1],mean_turn=vals[2])

def dominates(a,b):
    return a['faces']<=b['faces'] and a['max_turn']<=b['max_turn']+TOL and (a['faces']<b['faces'] or a['max_turn']<b['max_turn']-TOL)

def rank(custom,native):
    def quality(c):return (c['max_turn'],c['p95_turn'],c['mean_turn'],c['faces'],str(c['config']))
    def economy(c):return (c['faces'],*quality(c))
    equal=[c for c in native if c['faces']<=custom['faces']]
    combined=[custom]+native
    return dict(best_native=min(native,key=quality,default=None),same_face_budget=min(equal,key=quality,default=None),front=[c for c in combined if not any(dominates(a,c) for a in combined)],targets=[dict(max_turn=t,custom_qualifies=custom['max_turn']<=t+TOL,cheapest_native=min((c for c in native if c['max_turn']<=t+TOL),key=economy,default=None)) for t in TARGETS])

def report(d,fixtures):
    assert d['complete'] and len(d['rows'])==12 and d['controls']==9
    fixture={c['name']:c for c in fixtures};assert set(fixture)=={r['name'] for r in d['rows']}
    out=[];seen=screened=rankable=0
    for row in d['rows']:
        n=row['sections'];c=dict(row['custom']);c.setdefault('faces',len(fixture[row['name']]['custom']['faces']))
        custom=candidate(c,n,'custom');assert custom is not None
        native=[];invalid=[]
        for i,r in enumerate(row['candidates']):
            seen+=1
            if not r['prior_screened']:continue
            screened+=1
            k=candidate(r.get('measurement',{}),n,'native',r['config'])
            if k is None:invalid.append(i)
            else:native.append(k);rankable+=1
        out.append(dict(name=row['name'],custom=custom,native_rankable=len(native),native_unrankable=invalid,**rank(custom,native)))
    if d['native_executed']:assert (seen,screened)==(252,245)
    else:assert (seen,screened,rankable)==(0,0,0)
    return dict(approved=False,native_executed=d['native_executed'],targets=TARGETS,seen=seen,screened=screened,rankable=rankable,rows=out)

def controls():
    def m(a,f=30,n=2):return dict(complete=True,valid=n,total=n,faces=f,max_turn=a,p95_turn=a,mean_turn=a,sections=[dict(section=i,max_turn=a) for i in range(n)])
    base=candidate(m(30),2,'custom');assert base
    tests=[]
    for name,mut in [('partial',dict(complete=False)),('missing',dict(valid=1)),('bad_angle',dict(max_turn=float('nan'))),('missing_faces',dict(faces=0)),('duplicate_section',dict(sections=[dict(section=0,max_turn=30)]*2)),('wrong_max',dict(max_turn=31)),('wrong_p95',dict(p95_turn=31)),('wrong_mean',dict(mean_turn=31)),('missing_section_metric',dict(sections=[dict(section=0),dict(section=1,max_turn=30)]))]:
        assert candidate(dict(m(30),**mut),2,'native') is None;tests.append(name)
    a,b,c=[candidate(m(x,f),2,'native',dict(id=i)) for i,(x,f) in enumerate([(10,50),(25,30),(35,20)])]
    r=rank(base,[a,b,c]);assert r['best_native']==a and r['same_face_budget']==b;tests.append('same_face_budget')
    assert base not in r['front'] and all(k in r['front'] for k in (a,b,c));tests.append('pareto')
    assert r['targets'][0]['cheapest_native']==a and r['targets'][2]['cheapest_native']==b and r['targets'][3]['cheapest_native']==c;tests.append('target_min_faces')
    assert rank(base,[])['same_face_budget'] is None and rank(base,[])['front']==[base];tests.append('no_native')
    return tests

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'phase120_native_preflight.json');p.add_argument('--fixtures',type=Path,default=ROOT/'phase111_fixtures.json');p.add_argument('--out',type=Path,default=ROOT/'phase121_selection_preflight.json');a=p.parse_args()
    tests=controls();r=report(json.loads(a.input.read_text()),json.loads(a.fixtures.read_text())['cases']);r['controls']=tests;a.out.write_text(json.dumps(r,indent=2,allow_nan=False));print('controls',len(tests),'native_rankable',r['rankable']);print('custom target counts',[(t,sum(x['custom']['max_turn']<=t+TOL for x in r['rows'])) for t in TARGETS]);print('faces',sum(x['custom']['faces'] for x in r['rows']))
