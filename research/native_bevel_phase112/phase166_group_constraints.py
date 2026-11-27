"""Research only: finite-grid joint hole relocation with explicit geometric constraints.
Fixed rectangular block, parallel circular holes, at most three holes.
No continuous optimum or arbitrary CAD constraint solver claim.
"""
import copy,itertools,json,math,sys,time
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase164_multi_hole_clearance import hole,preflight,execute,MIN
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
STEP=.01;MARGIN=.001;TOL=1e-9;CAP=300000
def make(name,hs,limits,relation,expected,intent='relocate'):
    return dict(name=name,holes=hs,limits=limits,relation=relation,expected=expected,intent=intent)
def pair():
    return [hole(-.31,0,.25),hole(.31,0,.25)]
def triple():
    return [hole(-.42,0,.15),hole(0,0,.15),hole(.42,0,.15)]
CASES=[
 make('free_pair',pair(),[.05,.05],'free','proposal_verified'),
 make('axis_pair',pair(),[.05,.05],'axis_x','proposal_verified'),
 make('aligned_pair',pair(),[.05,.05],'aligned_x','proposal_verified'),
 make('symmetric_pair',pair(),[.05,.05],'symmetric_x','proposal_verified'),
 make('fixed_middle',triple(),[.10,0,.10],'free','proposal_verified'),
 make('equally_spaced',triple(),[.10,0,.10],'equal_x','proposal_verified'),
 make('diagonal',[hole(-.21,-.21,.25),hole(.21,.21,.25)],[.08,.08],'free','proposal_verified'),
 make('too_little_motion',pair(),[.03,.03],'free','no_grid_solution'),
 make('fixed',pair(),[0,0],'free','no_grid_solution'),
 make('unknown',pair(),[.05,.05],'free','needs_permission','unknown'),
 make('valid',[hole(-.45,0,.25),hole(.45,0,.25)],[.05,.05],'symmetric_x','unchanged'),
]
def candidates(h,lim,relation):
    x,y=h['xy'];n=math.floor(lim/STEP+TOL);out=[]
    for i in range(-n,n+1):
        for j in range(-n,n+1):
            if relation in ('axis_x','symmetric_x','equal_x') and j:continue
            d2=(i*i+j*j)*STEP*STEP
            if d2>lim*lim+TOL:continue
            a,b=x+i*STEP,y+j*STEP
            if 1-max(abs(a),abs(b))-h['r']<MIN+MARGIN-TOL:continue
            q=copy.deepcopy(h);q['xy']=(a,b)
            out.append((q,i,j,d2))
    return sorted(out,key=lambda z:(z[3],abs(z[2]),z[1],z[2]))
def relation_ok(a,relation,complete):
    xy=[z[0]['xy'] for z in a]
    if relation=='aligned_x':return not xy or all(abs(y-xy[0][1])<=TOL for x,y in xy)
    if relation=='symmetric_x' and complete:return abs(xy[0][0]+xy[1][0])<=TOL and abs(xy[0][1]-xy[1][1])<=TOL
    if relation=='equal_x' and complete:return abs(xy[0][0]+xy[2][0]-2*xy[1][0])<=TOL and all(abs(y-xy[0][1])<=TOL for x,y in xy)
    return True
def solve(c):
    hs=c['holes'];rel=c['relation'];lim=c['limits']
    if c['intent']!='relocate':return 'needs_permission',None,0,0
    if preflight(hs)['passed'] and relation_ok([(h,0,0,0) for h in hs],rel,True):return 'unchanged',None,0,0
    if any(h['kind']=='blind' and h['floor']<MIN for h in hs):return 'depth_conflict',None,0,0
    opts=[candidates(h,l,rel) for h,l in zip(hs,lim)]
    best=None;key=None;nodes=0;feasible=0;exhausted=False
    def visit(a):
        nonlocal best,key,nodes,feasible,exhausted
        if exhausted:return
        if nodes>=CAP:exhausted=True;return
        nodes+=1
        if len(a)==len(hs):
            if not relation_ok(a,rel,True):return
            feasible+=1
            k=(round(max(z[3] for z in a),12),round(sum(z[3] for z in a),12),tuple((z[1],z[2]) for z in a))
            if key is None or k<key:key=k;best=list(a)
            return
        for z in opts[len(a)]:
            if exhausted:break
            h=z[0]
            if any(math.dist(h['xy'],v[0]['xy'])-h['r']-v[0]['r']<MIN+MARGIN-TOL for v in a):continue
            if not relation_ok(a+[z],rel,False):continue
            visit(a+[z])
    visit([])
    if exhausted:return 'search_budget_exhausted',None,nodes,feasible
    return ('proposal',[z[0] for z in best],nodes,feasible) if best is not None else ('no_grid_solution',None,nodes,feasible)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for c in CASES:
        original=copy.deepcopy(c['holes']);status,p,nodes,feasible=solve(c);native=None;movements=None
        if p is not None:
            assert preflight(p)['passed']
            assert relation_ok([(h,0,0,0) for h in p],c['relation'],True)
            movements=[math.dist(a['xy'],b['xy']) for a,b in zip(original,p)]
            assert all(d<=l+TOL for d,l in zip(movements,c['limits']))
            for a,b,l in zip(original,p,c['limits']):
                assert all(a[k]==b[k] for k in a if k!='xy')
                if l==0:assert a==b
                if c['relation'] in ('axis_x','symmetric_x','equal_x'):assert a['xy'][1]==b['xy'][1]
            native=execute(p)
            status='proposal_verified' if native['passed'] and native['rollback_exact'] and all(x['clean'] for x in native['stages']) else 'proposal_failed_audit'
        assert original==c['holes']
        row=dict(name=c['name'],relation=c['relation'],status=status,expected=c['expected'],matched=status==c['expected'],
            original=original,proposal=p,movements=movements,limits=c['limits'],nodes=nodes,feasible=feasible,
            native=native,persistent_edit=False)
        rows.append(row);print('PHASE166_ROW',json.dumps(row,allow_nan=False),flush=True)
    out=dict(complete=True,native_executed=True,approved=False,grid_step=STEP,margin=MARGIN,node_cap=CAP,
             continuous_optimality_claim=False,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase166_group_constraints.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE166_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),verified=sum(r['status']=='proposal_verified' for r in rows),nodes=sum(r['nodes'] for r in rows),elapsed=out['elapsed'])),flush=True)
    assert len(rows)==11 and all(r['matched'] for r in rows)
if __name__=='__main__':main()
