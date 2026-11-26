"""Research only: state-driven completion of a protected synthetic part.
Reuses Phase 168 native operations and measured contracts. No arbitrary mesh inference.
All edits on disposable copies; no persistent edits or production adoption.
"""
import json,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase168_combined_local_operations import fixture,inspect,compact,apply,hole_mesh,X,WIDTH,REMOVED,EPS
from phase160_operation_contracts import close
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def classify(a,rounded_volume):
    q=a['metrics']
    if not (a['clean'] and a['closed'] and a['scope_ok'] and a['exterior_ok']
            and close(a['bounds'],[[-1,-1,-1],[1,1,1]])):
        return 'invalid'
    rounded=a['local_round_faces']>=4
    if a['local_round_faces'] and not rounded:return 'invalid'
    hole=a['hole']
    expected=(rounded_volume if rounded else 8.)-(REMOVED if hole else 0.)
    if abs(a['volume']-expected)>EPS or q['euler']!=(0 if hole else 2):
        return 'invalid'
    return {(False,False):'raw',(True,False):'rounded',(False,True):'holed',(True,True):'complete'}[(rounded,hole)]
def operate(m,op):
    if op=='bevel':
        n=m.copy()
        try:apply(n,'right',WIDTH);return n
        except Exception:bpy.data.meshes.remove(n);raise
    if op=='global':
        n=m.copy()
        try:apply(n,'all',WIDTH);return n
        except Exception:bpy.data.meshes.remove(n);raise
    if op in ('hole','wrong_hole','offset_hole'):
        return hole_mesh(m,X if op=='hole' else -.5 if op=='wrong_hole' else X-.05)
    raise ValueError(op)
CASES=[
 ('raw',(), 'finish',2,None,'goal_met',['bevel','hole']),
 ('rounded',('bevel',),'finish',2,None,'goal_met',['hole']),
 ('holed',('hole',),'finish',2,None,'goal_met',['bevel']),
 ('complete',('bevel','hole'),'finish',2,None,'goal_met',[]),
 ('complete_reverse',('hole','bevel'),'finish',2,None,'goal_met',[]),
 ('protected_violation',('wrong_hole',),'finish',2,None,'needs_review',[]),
 ('offset_violation',('offset_hole',),'finish',2,None,'needs_review',[]),
 ('unknown',(),'unknown',2,None,'preserved',[]),
 ('budget_one',(),'finish',1,None,'budget_exhausted',['bevel']),
 ('rollback_resume',('bevel',),'finish',2,'wrong_hole','goal_met',['wrong_hole','hole']),
 ('global_rollback',(),'finish',3,'global','goal_met',['global','bevel','hole']),
]
def execute(base,source,rounded_volume,prefix,intent,budget,probe):
    start=base.copy();work=None
    try:
        for op in prefix:
            n=operate(start,op);bpy.data.meshes.remove(start);start=n
        initial=inspect(start,source);initial_state=classify(initial,rounded_volume)
        work=start.copy();state=initial;label=initial_state;trace=[]
        def trial(op):
            nonlocal work,state,label
            before=state;before_label=label
            candidate=operate(work,op)
            adopted=False
            try:
                a=inspect(candidate,source);after=classify(a,rounded_volume)
                expected={('raw','bevel'):'rounded',('raw','hole'):'holed',
                          ('rounded','hole'):'complete',('holed','bevel'):'complete'}.get((before_label,op))
                adopted=bool(expected and after==expected and a['sha256']!=before['sha256'])
                if adopted:
                    bpy.data.meshes.remove(work);work=candidate;state=a;label=after
                else:
                    assert inspect(work,source)['sha256']==before['sha256']
                trace.append(dict(op=op,accepted=adopted,before=before_label,candidate=after,
                    rollback_exact=not adopted and inspect(work,source)['sha256']==before['sha256'],
                    before_sha=before['sha256'],after_sha=state['sha256'],candidate_sha=a['sha256'],
                    protected=a['scope_ok'],candidate_summary=compact(a)))
            finally:
                if not adopted:bpy.data.meshes.remove(candidate)
            return adopted
        if intent=='unknown':status='preserved'
        elif label=='invalid':status='needs_review'
        else:
            if probe is not None and len(trace)<budget:assert not trial(probe)
            while label!='complete' and len(trace)<budget:
                op={'raw':'bevel','rounded':'hole','holed':'bevel'}.get(label)
                if op is None or not trial(op):break
            status='goal_met' if label=='complete' else 'budget_exhausted' if len(trace)>=budget else 'needs_review'
        assert inspect(start,source)['sha256']==initial['sha256']
        return dict(status=status,initial_state=initial_state,final_state=label,trace=trace,
                    input_unchanged=True,initial_sha=initial['sha256'],final_sha=state['sha256'],
                    final=compact(state),persistent_edit=False)
    finally:
        if work is not None:bpy.data.meshes.remove(work)
        bpy.data.meshes.remove(start)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    source=fixture();V,F=source;base=bpy.data.meshes.new('p169_source');base.from_pydata(V,[],F);base.update()
    try:
        a=inspect(base,source);ref=operate(base,'bevel')
        try:rounded_volume=inspect(ref,source)['volume']
        finally:bpy.data.meshes.remove(ref)
        rows=[]
        for name,prefix,intent,budget,probe,expected,expected_ops in CASES:
            r=execute(base,source,rounded_volume,prefix,intent,budget,probe)
            row=dict(name=name,prefix=list(prefix),intent=intent,budget=budget,expected=expected,
                     expected_ops=expected_ops,matched=r['status']==expected and [t['op'] for t in r['trace']]==expected_ops,**r)
            assert len(r['trace'])<=budget
            assert all(t['accepted'] or t['rollback_exact'] for t in r['trace'])
            assert inspect(base,source)['sha256']==a['sha256']
            if not r['trace']:assert r['initial_sha']==r['final_sha']
            rows.append(row);print('PHASE169_ROW',json.dumps(row,allow_nan=False),flush=True)
        out=dict(complete=True,native_executed=True,approved=False,rows=rows,elapsed=time.perf_counter()-start,
                 scope='fixed synthetic prism and explicit machining contract')
        P.mkdir(exist_ok=True);(P/'phase169_combined_state_planner.json').write_text(json.dumps(out,indent=2,allow_nan=False))
        print('PHASE169_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
            goal_met=sum(r['status']=='goal_met' for r in rows),attempts=sum(len(r['trace']) for r in rows),
            rollbacks=sum(t['rollback_exact'] for r in rows for t in r['trace']),
            no_ops=sum(not r['trace'] for r in rows),elapsed=out['elapsed']),flush=True)
        assert len(rows)==11 and all(r['matched'] for r in rows)
    finally:bpy.data.meshes.remove(base)
if __name__=='__main__':main()
