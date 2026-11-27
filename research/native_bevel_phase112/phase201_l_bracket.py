"""Phase 201: practical fixed L-bracket, four holes on two orthogonal flanges.
Reuse the exact Boolean drill, independent ray probe and native mesh audit.
No new solver, arbitrary shape support, or manufacturing certification.
"""
import json,math,sys,time
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase195_tapered_spacer import drill,write_obj,basis
from phase196_spacer_verification import Rays,ray_controls
from phase160_operation_contracts import measure
from phase167_protected_local_bevel import signature
from phase171_planar_topology_variants import arrays
from phase163_hole_contracts import N
ROOT=Path(__file__).resolve().parent
T=.5;L=2.;MIN=.20;EPS=1e-4

def blank():
    profile=[(0,0),(L,0),(L,T),(T,T),(T,L),(0,L)]
    v=[(x,y,z) for y in (-1.,1.) for x,z in profile]
    f=[tuple(range(6)),tuple(reversed(range(6,12)))]
    f.extend(((i+1)%6,i,i+6,(i+1)%6+6) for i in range(6))
    m=bpy.data.meshes.new('p201_blank');m.from_pydata(v,[],f);m.update();return m

def holes():
    return [dict(axis=a,u=1.25,y=y,r=.18) for a in ('Z','X') for y in (-.5,.5)]

def preflight(hs):
    reasons=[];walls=[]
    for h in hs:
        u,y,r=h['u'],h['y'],h['r']
        w=min(u-T,L-u,1-abs(y))-r;walls.append(w)
        if h['axis'] not in ('X','Z') or r<=0:reasons.append('invalid')
        if w<MIN-1e-9:reasons.append('flange_margin')
    for i,a in enumerate(hs):
        for b in hs[i+1:]:
            if a['axis']==b['axis'] and math.hypot(a['u']-b['u'],a['y']-b['y'])-a['r']-b['r']<MIN-1e-9:
                reasons.append('hole_web')
    return dict(passed=not reasons,reasons=sorted(set(reasons)),margins=walls)

def frame(h):
    u,y=h['u'],h['y']
    c=np.array([u,y,T/2] if h['axis']=='Z' else [T/2,y,u])
    a=np.array([0.,0.,1.] if h['axis']=='Z' else [1.,0.,0.])
    return c,basis(a)

def audit(m,hs):
    q=measure(m,'cube');rays=Rays(m);per=[]
    for h in hs:
        c,M=frame(h);a=M[:,2];r=h['r'];inside=[];radial=[]
        for i in range(9):
            off=np.zeros(3) if i==0 else M@np.array([.5*r*math.cos(i*math.pi/4),.5*r*math.sin(i*math.pi/4),0.])
            inside.extend(rays.cast(c+off+s*a*.75,-s*a,1.5) is None for s in (-1,1))
        for i in range(8):
            d=M@np.array([math.cos(i*math.pi/4),math.sin(i*math.pi/4),0.])
            hit=rays.cast(c,d,1.5);radial.append(hit is not None and abs(hit-r)<=EPS)
        per.append(dict(axis=h['axis'],clear=all(inside),radius=all(radial)))
    expected=2*(2*L*T-T*T)-sum(N*.5*h['r']**2*math.sin(2*math.pi/N)*T for h in hs)
    checks=dict(clean=q['clean'],closed=q['metrics']['boundary_edges']==0,
        topology=q['metrics']['euler']==2-2*len(hs),
        bounds=bool(np.max(np.abs(np.array(q['bounds'])-[[0,-1,0],[L,1,L]]))<=EPS),
        volume=abs(q['volume']-expected)<=EPS,
        holes=all(x['clear'] and x['radius'] for x in per))
    return dict(passed=all(checks.values()),checks=checks,per_hole=per,volume=q['volume'],
                expected_volume=expected,euler=q['metrics']['euler'],faces=q['metrics']['faces'])

def run(hs,probe,path):
    pre=preflight(hs);stages=[];m=blank();before=signature(*arrays(m));current=m
    if path.exists():path.unlink()
    try:
        base=measure(m,'cube');assert base['clean'] and abs(base['volume']-3.5)<=EPS
        if not pre['passed']:
            return dict(status='preflight_rejected',preflight=pre,stages=stages,exported=False,source_unchanged=True)
        for i,h in enumerate(hs):
            if probe=='skip_last' and i==len(hs)-1:continue
            c,M=frame(h);new=drill(current,c,M,.6,h['r']*(.8 if probe=='wrong_radius' and i==0 else 1))
            if current!=m:bpy.data.meshes.remove(current)
            current=new;q=measure(current,'cube');stages.append(dict(clean=q['clean'],euler=q['metrics']['euler'],faces=q['metrics']['faces']))
        a=audit(current,hs)
        ok=a['passed'] and all(s['clean'] for s in stages)
        if ok and probe=='normal':write_obj(current,path)
        return dict(status='complete' if ok else 'audit_rejected',preflight=pre,stages=stages,
            audit=a,exported=path.exists(),source_unchanged=signature(*arrays(m))==before)
    finally:
        if current!=m:bpy.data.meshes.remove(current)
        bpy.data.meshes.remove(m)

def main():
    assert bpy.app.version_string=='4.4.3';assert ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    edge=holes();edge[0]['u']=1.85
    web=holes();web[1]['y']=-.05
    corner=holes();corner[2]['u']=.65
    cases=[('bracket',holes(),'normal','complete'),('edge',edge,'normal','preflight_rejected'),
           ('web',web,'normal','preflight_rejected'),('corner',corner,'normal','preflight_rejected'),
           ('skip_last',holes(),'skip_last','audit_rejected'),('wrong_radius',holes(),'wrong_radius','audit_rejected')]
    rows=[]
    for name,hs,probe,expected in cases:
        r=run(hs,probe,dest/f'phase201_{name}.obj')
        row=dict(name=name,expected=expected,matched=r['status']==expected,**r)
        rows.append(row);print('PHASE201_ROW',json.dumps(row,allow_nan=False),flush=True)
    gate=len(rows)==6 and all(r['matched'] and r['source_unchanged'] and r['exported']==(r['expected']=='complete')
        and (r['expected']!='preflight_rejected' or not r['stages']) for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,elapsed=time.perf_counter()-start)
    (dest/'phase201_l_bracket.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE201_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        parts=sum(r['exported'] for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
