"""Frozen DIL-04 evaluation; imports only stdlib and local retrieval engine."""
import argparse, hashlib, json, platform, statistics, time
from pathlib import Path
from retrieval import all_context,metadata_only,fts_only,hybrid,input_bytes
ROOT=Path(__file__).resolve().parent
METHODS={'all_context':all_context,'metadata_only':metadata_only,'fts5_trigram':fts_only,'hybrid':hybrid}

def verify_freeze():
 freeze=json.loads((ROOT/'FREEZE.json').read_text(encoding='utf-8'))
 for path,sha in freeze['sha256'].items():
  got=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  if got!=sha:raise ValueError(f'Freeze mismatch: {path}')
 return freeze

def score(docs,cases,fn):
 correct=0;needed=0;found=0;foreign=0;retired=0;total_bytes=0;per=[]
 for c in cases:
  got=fn(docs,c);ids={d['id'] for d in got};gold=set(c['gold_ids'])
  correct+=int(ids==gold)
  needed+=len(gold);found+=len(ids & gold)
  foreign+=sum(d['project']!=c['project'] for d in got)
  retired+=sum(d['revision']!='current' or d['status']!='approved' for d in got)
  byte_count=input_bytes(got);total_bytes+=byte_count
  per.append({'id':c['id'],'gold_ids':c['gold_ids'],'returned_ids':[d['id'] for d in got],
              'all_required_found':gold.issubset(ids),'exact':ids==gold,'bytes':byte_count})
 return {'cases':len(cases),'exact_cases':correct,'required_found':found,
         'required_total':needed,'foreign_project_documents':foreign,
         'retired_or_unapproved_documents':retired,'total_input_bytes':total_bytes,
         'median_bytes_per_case':statistics.median(x['bytes'] for x in per),
         'details':per}

def run():
 freeze=verify_freeze()
 docs=json.loads((ROOT/'corpus.json').read_text(encoding='utf-8'))
 result={'experiment':'DIL-04','synthetic_only':True,'environment':{'python':platform.python_version(),
       'sqlite':__import__('sqlite3').sqlite_version,'platform':platform.system()},
       'frozen_sha256':freeze['sha256'],'splits':{}}
 for split in ('development','holdout'):
  cases=json.loads((ROOT/'fixtures'/f'{split}.json').read_text(encoding='utf-8'))
  result['splits'][split]={name:score(docs,cases,fn) for name,fn in METHODS.items()}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
 start=time.perf_counter();result=run();result['benchmark_wall_seconds']=time.perf_counter()-start
 with open(args.output,'x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print(json.dumps({split:{name:{k:v for k,v in metrics.items() if k!='details'} for name,metrics in methods.items()}
                   for split,methods in result['splits'].items()},ensure_ascii=False,indent=2))
