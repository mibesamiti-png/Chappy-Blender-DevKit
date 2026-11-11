"""Independent compact scoring of directly observed frozen GitHub document metadata.

PROBE ONLY. This does not substitute a real full-corpus SQLite execution of
DIL-04 evaluate.py. The 12 document blobs and their SHA were checked via GitHub.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/'cases.json').read_text())
O=json.loads((ROOT/'observed_matrix.json').read_text())
D=O['entries']
assert all(d['blob_ok'] and d['anchors_ok'] for d in D)
assert len(D)==12 and len(C)==15

def score(name):
    exact=found=historical=bytes_total=0;details=[]
    for c in C:
        if name=='all_context': select=D
        elif name=='metadata_only':select=[d for d in D if d['current'] and d['topic'] in c['topics']]
        elif name=='fts5_trigram_proxy':select=[d for d in D if d['current'] and c['id'] in d['match']]
        elif name=='hybrid_proxy':select=[d for d in D if d['current'] and (d['topic'] in c['topics'] if c['topics'] else c['id'] in d['match'])]
        got={d['id'] for d in select};gold=set(c['gold_ids']);got_old=sum(not d['current'] for d in select)
        n=sum(d['bytes'] for d in select)+len(select)+1
        exact+=int(got==gold);found+=len(got&gold);historical+=got_old;bytes_total+=n
        details.append({'question':c['id'],'selected':sorted(got),'missing':sorted(gold-got),'bytes':n,
                        'historical':got_old,'status':'evidence_candidate_only' if gold<=got and got_old==0 else 'needs_authoritative_source'})
    return {'exact_docsets':exact,'cases':len(C),'required_found':found,'required_total':sum(len(c['gold_ids']) for c in C),
            'historical_returns':historical,'input_bytes':bytes_total,'details':details}

a={method:score(method) for method in ('all_context','metadata_only','fts5_trigram_proxy','hybrid_proxy')}
ratio=a['hybrid_proxy']['input_bytes']/a['all_context']['input_bytes']
result={'study':'DIL-07','record_type':'first_source_content_probe_not_python_sqlite_field_run',
        'result':'transfer_failed_not_ready','source_commit':O['source_commit'],
        'fixed_manifest_source_hashes':all(d['blob_ok'] for d in D),
        'all_predeclared_anchors_present':all(d['anchors_ok'] for d in D),
        'source_method':O['method'],'cases':len(C),'tagged_cases':sum(bool(c['topics']) for c in C),
        'observed':a,'hybrid_vs_full_byte_ratio':ratio,'strong_gate_met':False,
        'product_adoption':False,'can_authorize_merge':False,'can_skip_ci':False,
        'limits':['Same author wrote question/gold labels','Unmodified DIL04 SQLite on full public corpus not executed locally',
                  'Literal-match proxy is not a verified substitute for SQLite FTS trigram tokenizer and bm25 ranking',
                  'No LLM answer, real user questions, AI tokens, costs, actual workflow speed or efficacy tested']}
assert len(D)==len({d['id'] for d in D})
assert all(set(c['gold_ids'])<=set(d['id'] for d in D if d['current']) for c in C)
assert a['hybrid_proxy']['historical_returns']==0
assert a['hybrid_proxy']['required_found']<a['hybrid_proxy']['required_total']
output=ROOT/'results'/'first-source-probe.json'
with output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({'ratio':ratio,'metrics':{k:{n:v for n,v in d.items() if n!='details'} for k,d in a.items()}},ensure_ascii=False,indent=2))
