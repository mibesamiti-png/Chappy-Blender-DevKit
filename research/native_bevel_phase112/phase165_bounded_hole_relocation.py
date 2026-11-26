"""Research only: bounded proposals for one movable hole, fixed rectangular block.
Search a finite displacement grid, preserve all radii/depths and other hole centers.
Never infer permission from geometry. No global optimality or infeasibility claim.
"""
import copy,json,math,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase164_multi_hole_clearance import hole,preflight,execute,MIN
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
STEP=.01
MARGIN=.001
CASES=[
 dict(name='thin_web',holes=[hole(-.31,0,.25),hole(.31,0,.25)],movable=1,limit=.20,intent='relocate',expected='proposal_verified'),
 dict(name='thin_outer',holes=[hole(-.45,0,.25),hole(.65,0,.25)],movable=1,limit=.20,intent='relocate',expected='proposal_verified'),
 dict(name='diagonal_web',holes=[hole(-.3,-.3,.25),hole(.12,.12,.25)],movable=1,limit=.20,intent='relocate',expected='proposal_verified'),
 dict(name='three_holes',holes=[hole(-.55,0,.15),hole(0,0,.15),hole(.42,0,.15)],movable=2,limit=.20,intent='relocate',expected='proposal_verified'),
 dict(name='breakout',holes=[hole(-.45,0,.25),hole(.90,0,.25)],movable=1,limit=.40,intent='relocate',expected='proposal_verified'),
 dict(name='limited_motion',holes=[hole(-.31,0,.25),hole(.31,0,.25)],movable=1,limit=.05,intent='relocate',expected='no_grid_solution'),
 dict(name='thin_floor',holes=[hole(-.45,0,.25),hole(.45,0,.25,.10)],movable=1,limit=.20,intent='relocate',expected='depth_conflict'),
 dict(name='unknown',holes=[hole(-.31,0,.25),hole(.31,0,.25)],movable=1,limit=.20,intent='unknown',expected='needs_permission'),
 dict(name='locked',holes=[hole(-.31,0,.25),hole(.31,0,.25)],movable=None,limit=.20,intent='relocate',expected='needs_permission'),
 dict(name='already_valid',holes=[hole(-.45,0,.25),hole(.45,0,.25)],movable=1,limit=.20,intent='relocate',expected='unchanged'),
]
def clearance_ok(hs,index):
    pre=preflight(hs)
    # Margin is required only at constraints involving the moving hole.
    return (pre['passed'] and pre['outer'][index]>=MIN+MARGIN-1e-9
            and all(p['clearance']>=MIN+MARGIN-1e-9 for p in pre['pairs'] if index in (p['i'],p['j'])))
def propose(hs,index,limit,intent):
    original=preflight(hs)
    if original['passed']:return 'unchanged',None,0
    if intent!='relocate' or index is None:return 'needs_permission',None,0
    if 'blind_floor' in original['reasons']:return 'depth_conflict',None,0
    assert 0<=index<len(hs) and 0<=limit<=.4
    x,y=hs[index]['xy'];bound=math.floor(limit/STEP+1e-9);candidates=[]
    for i in range(-bound,bound+1):
        for j in range(-bound,bound+1):
            d=math.hypot(i*STEP,j*STEP)
            if d<=limit+1e-9:candidates.append((d,i,j))
    candidates.sort(key=lambda z:(z[0],abs(z[2]),z[1],z[2]))
    tested=0
    for d,i,j in candidates:
        tested+=1
        changed=copy.deepcopy(hs)
        changed[index]['xy']=(x+i*STEP,y+j*STEP)
        if clearance_ok(changed,index):return 'proposal',changed,tested
    return 'no_grid_solution',None,tested
def validate_unchanged(before,after,index,limit):
    assert len(before)==len(after)
    for i,(a,b) in enumerate(zip(before,after)):
        assert all(a[k]==b[k] for k in a if k!='xy')
        if i!=index:assert a==b
    assert math.dist(before[index]['xy'],after[index]['xy'])<=limit+1e-9
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for c in CASES:
        hs=c['holes'];frozen=copy.deepcopy(hs)
        status,proposal,tested=propose(hs,c['movable'],c['limit'],c['intent'])
        assert hs==frozen
        evidence=None;move=None;post=None
        if proposal is not None:
            validate_unchanged(hs,proposal,c['movable'],c['limit'])
            move=math.dist(hs[c['movable']]['xy'],proposal[c['movable']]['xy'])
            post=preflight(proposal);assert post['passed']
            # Verification on an isolated synthetic object only; no persistent edit.
            evidence=execute(proposal)
            status='proposal_verified' if evidence['passed'] and evidence['rollback_exact'] and all(x['clean'] for x in evidence['stages']) else 'proposal_failed_audit'
        row=dict(name=c['name'],status=status,expected=c['expected'],matched=status==c['expected'],
            original=hs,preflight=preflight(hs),proposal=proposal,postflight=post,
            movement=move,limit=c['limit'],tested=tested,native=evidence,persistent_edit=False)
        assert hs==frozen
        rows.append(row)
        print('PHASE165_ROW',json.dumps(row,allow_nan=False),flush=True)
    out=dict(complete=True,native_executed=True,approved=False,grid_step=STEP,safety_margin=MARGIN,
        global_optimality_claim=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase165_bounded_hole_relocation.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE165_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        proposals=sum(r['status']=='proposal_verified' for r in rows),
        native_cases=sum(r['native'] is not None for r in rows),
        grid_tests=sum(r['tested'] for r in rows),persistent_edits=0,elapsed=out['elapsed'])),flush=True)
    assert len(rows)==10 and all(r['matched'] for r in rows)
if __name__=='__main__':main()
