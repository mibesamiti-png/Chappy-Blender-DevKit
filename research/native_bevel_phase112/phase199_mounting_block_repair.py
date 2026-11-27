"""Phase 199: recover a manufacturable layout for the Phase 198 block.
Reuse existing bounded relocation and Boolean contracts. Only the blind hole
may move, and only with explicit permission. No new solver or optimization.
Fixed synthetic research; not a manufacturing certificate.
"""
import copy,json,math,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase198_mounting_block import layout
from phase165_bounded_hole_relocation import propose,validate_unchanged
from phase164_multi_hole_clearance import preflight,execute
from phase195_tapered_spacer import write_obj

ROOT=Path(__file__).resolve().parent
def main():
    assert bpy.app.version_string=='4.4.3';start=time.perf_counter()
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[
        ('repair_web',layout(blind_y=-.35),2,.30,'relocate','proposal_verified'),
        ('limited_motion',layout(blind_y=-.35),2,.05,'relocate','no_grid_solution'),
        ('no_permission',layout(blind_y=-.35),2,.30,'unknown','needs_permission'),
        ('locked',layout(blind_y=-.35),None,.30,'relocate','needs_permission'),
        ('thin_floor',layout(floor=.10,blind_y=-.35),2,.30,'relocate','depth_conflict'),
        ('already_valid',layout(),2,.30,'relocate','unchanged')]
    rows=[]
    for name,hs,index,limit,intent,expected in cases:
        frozen=copy.deepcopy(hs);status,p,tested=propose(hs,index,limit,intent)
        original_pre=preflight(hs);post=None;native=None;movement=None;captures=[]
        path=dest/f'phase199_{name}.obj'
        # Keep artifacts only from validated positive trials.
        if path.exists():path.unlink()
        if p is not None:
            validate_unchanged(frozen,p,index,limit)
            movement=math.dist(frozen[index]['xy'],p[index]['xy'])
            post=preflight(p)
            def observe(m):captures.append(True);write_obj(m,path)
            if post['passed']:
                native=execute(p,observer=observe)
            ok=bool(native and native['passed'] and native['rollback_exact'] and
                all(x['clean'] for x in native['stages']) and len(captures)==1)
            status='proposal_verified' if ok else 'proposal_failed_audit'
            if not ok and path.exists():path.unlink()
        row=dict(name=name,status=status,expected=expected,matched=status==expected,
            original=hs,proposal=p,original_preflight=original_pre,postflight=post,
            movement=movement,limit=limit,tested=tested,native=native,
            exported=path.exists(),input_unchanged=hs==frozen,persistent_edit=False)
        rows.append(row);print('PHASE199_ROW',json.dumps(row,allow_nan=False),flush=True)
    gate=len(rows)==6 and all(r['matched'] and r['input_unchanged'] and
        r['exported']==(r['expected']=='proposal_verified') and
        (r['native'] is None)==(r['expected']!='proposal_verified') for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,
        elapsed=time.perf_counter()-start)
    (dest/'phase199_mounting_block_repair.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE199_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        verified=sum(r['status']=='proposal_verified' for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
