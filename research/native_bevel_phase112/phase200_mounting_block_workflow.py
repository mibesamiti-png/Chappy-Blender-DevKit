"""Phase 200: bounded end-to-end mounting-block workflow.
Choose direct fabrication, permitted relocation, or stop. Reuse Phase 164/165;
no new solver, geometric predicate, or machining operator.
Fixed synthetic block and three-hole layout family only.
"""
import copy,json,sys,time,math
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase198_mounting_block import layout
from phase164_multi_hole_clearance import preflight,execute
from phase165_bounded_hole_relocation import propose,validate_unchanged
from phase195_tapered_spacer import write_obj
ROOT=Path(__file__).resolve().parent

def produce(hs,intent,permission,movable,limit,path):
    original=copy.deepcopy(hs);trace=[];native=None;candidate=None;captures=[]
    if path.exists():path.unlink()
    def finish(status,chosen=None,movement=None):
        return dict(status=status,trace=trace,chosen=chosen,movement=movement,
                    native=native,exported=path.exists(),input_unchanged=hs==original,
                    persistent_edit=False)
    if intent!='fabricate':
        return finish('unknown_intent')
    pre=preflight(hs);trace.append(dict(step='preflight',passed=pre['passed'],reasons=pre['reasons']))
    chosen=hs;movement=0.;route='direct'
    if not pre['passed']:
        status,p,tested=propose(hs,movable,limit,'relocate' if permission else 'unknown')
        trace.append(dict(step='relocation',status=status,tested=tested))
        if p is None:return finish(status)
        validate_unchanged(original,p,movable,limit)
        chosen=p;movement=math.dist(original[movable]['xy'],p[movable]['xy']);route='repaired'
        post=preflight(chosen);trace.append(dict(step='postflight',passed=post['passed'],reasons=post['reasons']))
        if not post['passed']:return finish('proposal_rejected')
    def observe(m):captures.append(m.copy())
    try:
        native=execute(chosen,observer=observe)
        ok=bool(native['passed'] and native['rollback_exact'] and
                all(s['clean'] for s in native['stages']) and len(captures)==1)
        trace.append(dict(step='native_audit',passed=ok))
        if not ok:return finish('native_rejected')
        write_obj(captures[0],path)
        trace.append(dict(step='export',passed=path.is_file()))
        return finish(route,copy.deepcopy(chosen),movement)
    finally:
        for m in captures:bpy.data.meshes.remove(m)

def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter()
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[
        ('direct',layout(),'fabricate',False,None,0.,'direct'),
        ('repair_web',layout(blind_y=-.35),'fabricate',True,2,.30,'repaired'),
        ('repair_outer',layout(right=.75),'fabricate',True,1,.20,'repaired'),
        ('no_permission',layout(blind_y=-.35),'fabricate',False,2,.30,'needs_permission'),
        ('locked',layout(blind_y=-.35),'fabricate',True,None,.30,'needs_permission'),
        ('small_limit',layout(blind_y=-.35),'fabricate',True,2,.05,'no_grid_solution'),
        ('thin_floor',layout(floor=.10),'fabricate',True,2,.30,'depth_conflict'),
        ('unknown_intent',layout(),'unknown',False,None,0.,'unknown_intent')]
    rows=[]
    for name,hs,intent,permission,index,limit,expected in cases:
        path=dest/f'phase200_{name}.obj'
        r=produce(hs,intent,permission,index,limit,path)
        expected_export=expected in ('direct','repaired')
        steps=[x['step'] for x in r['trace']]
        direct_ok=expected!='direct' or (r['chosen']==hs and r['movement']==0 and 'relocation' not in steps)
        repair_ok=expected!='repaired' or (r['movement'] is not None and 0<r['movement']<=limit+1e-9
            and steps==['preflight','relocation','postflight','native_audit','export'])
        matched=(r['status']==expected and r['exported']==expected_export
                 and (r['native'] is not None)==expected_export and direct_ok and repair_ok)
        row=dict(name=name,expected=expected,matched=matched,original=hs,permission=permission,
                 movable=index,limit=limit,**r)
        rows.append(row);print('PHASE200_ROW',json.dumps(row,allow_nan=False),flush=True)
    gate=len(rows)==8 and all(r['matched'] and r['input_unchanged'] and not r['persistent_edit'] for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,elapsed=time.perf_counter()-start)
    (dest/'phase200_mounting_block_workflow.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE200_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        direct=sum(r['status']=='direct' for r in rows),repaired=sum(r['status']=='repaired' for r in rows),
        stopped=sum(not r['exported'] for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
