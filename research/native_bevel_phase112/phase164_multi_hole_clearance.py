"""Research only: parallel circular holes in a fixed synthetic block.
Analytic conservative clearance before machining, native Boolean and sampled audit after.
No arbitrary-mesh thickness claim or manufacturing certification.
"""
import itertools,json,math,sys,time
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase163_hole_contracts import N,EPS,BOX,FACES,make,cutter,snapshot,near,ray
from phase160_operation_contracts import close
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
MIN=.20
def hole(x,y,r,floor=0.):
    return dict(xy=(x,y),r=r,floor=floor,kind='through' if floor==0 else 'blind')
CASES=[
 ('two_through',[hole(-.45,0,.25),hole(.45,0,.25)],True,True),
 ('mixed_diagonal',[hole(-.4,-.3,.25),hole(.4,.3,.30,.40)],True,True),
 ('three_through',[hole(-.55,0,.15),hole(0,0,.15),hole(.55,0,.15)],True,True),
 ('thin_web',[hole(-.31,0,.25),hole(.31,0,.25)],False,True),
 ('thin_outer',[hole(-.45,0,.25),hole(.65,0,.25)],False,True),
 ('thin_floor',[hole(-.45,0,.25),hole(.45,0,.25,.10)],False,True),
 ('overlap',[hole(-.15,0,.25),hole(.15,0,.25)],False,False),
 ('breakout',[hole(-.45,0,.25),hole(.90,0,.25)],False,False)]
def preflight(hs):
    outer=[min(1-abs(h['xy'][0]),1-abs(h['xy'][1]))-h['r'] for h in hs]
    pairs=[dict(i=i,j=j,clearance=math.dist(a['xy'],b['xy'])-a['r']-b['r'])
           for (i,a),(j,b) in itertools.combinations(enumerate(hs),2)]
    floors=[h['floor'] for h in hs if h['kind']=='blind']
    reasons=[]
    if min(outer)<MIN-1e-9:reasons.append('outer_wall')
    if any(x['clearance']<MIN-1e-9 for x in pairs):reasons.append('hole_web')
    if any(x<MIN-1e-9 for x in floors):reasons.append('blind_floor')
    return dict(passed=not reasons,reasons=reasons,outer=outer,pairs=pairs,floors=floors)
def pair_measure(ob,hs):
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
    try:
        m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
        tree=BVHTree.FromPolygons([v.co.copy() for v in m.vertices],T,all_triangles=True,epsilon=0.)
        out=[]
        for (i,a),(j,b) in itertools.combinations(enumerate(hs),2):
            dx=b['xy'][0]-a['xy'][0];dy=b['xy'][1]-a['xy'][1];dist=math.hypot(dx,dy)
            u=(dx/dist,dy/dist,0.)
            ra=ray(tree,(*a['xy'],.90),u);rb=ray(tree,(*b['xy'],.90),tuple(-x for x in u))
            gap=None if ra is None or rb is None else dist-ra-rb
            # An inscribed regular polygon gives a conservative circle clearance interval.
            lower=dist-a['r']-b['r'];upper=dist-(a['r']+b['r'])*math.cos(math.pi/N)
            out.append(dict(i=i,j=j,measured=gap,lower=lower,upper=upper,
                agrees=gap is not None and lower-EPS<=gap<=upper+EPS))
        return out
    finally:ev.to_mesh_clear()
def audit(ob,hs):
    snaps=[snapshot(ob,h) for h in hs];a=snaps[0];q=a['metrics']
    area=lambda h:N*.5*h['r']**2*math.sin(2*math.pi/N)
    volume=4.-sum(area(h)*(1-h['floor']) for h in hs)
    per=[]
    for h,s in zip(hs,snaps):
        wanted=(None,None) if h['kind']=='through' else (2-h['floor'],1.)
        cavity=all(all(near(x,y) for x,y in zip(p,wanted)) for p in s['inside_rays'])
        radius=all(near(x,h['r']) for x in s['radii'])
        floor=None if h['kind']=='through' else 2-s['inside_rays'][0][0] if s['inside_rays'][0][0] is not None else None
        per.append(dict(cavity=cavity,radius=radius,floor_measured=floor,
            outer_min=min(w for w in s['axis_wall_estimates'] if w is not None),
            exterior_samples=all(all(near(x,y) for x,y in zip(p,(1.,1.))) for p in s['outside_rays'])))
    pairs=pair_measure(ob,hs)
    checks=dict(clean=a['clean'],closed=q['boundary_edges']==0,topology=q['euler']==2-2*sum(h['kind']=='through' for h in hs),
        bounds=close(a['bounds'],[[-1,-1,0],[1,1,1]]),volume=abs(a['volume']-volume)<=EPS,
        cavities=all(x['cavity'] and x['radius'] and x['exterior_samples'] for x in per),
        outer=all(x['outer_min']>=MIN-EPS for x in per),
        web=all(x['agrees'] and x['measured']>=MIN-EPS for x in pairs),
        floor=all(h['kind']=='through' or (x['floor_measured'] is not None and x['floor_measured']>=MIN-EPS)
                  for h,x in zip(hs,per)))
    return dict(passed=all(checks.values()),checks=checks,volume=a['volume'],expected_volume=volume,
                euler=q['euler'],faces=q['faces'],per_hole=per,pairs=pairs)
def execute(hs,observer=None):
    ob,m=make('p164_block',BOX,FACES);cutters=[];mods=[]
    try:
        base=snapshot(ob,hs[0]);stages=[]
        for h in hs:
            co,cm=cutter(h['xy'],h['r'],h['floor']);cutters.append((co,cm))
            mod=ob.modifiers.new('p164_difference','BOOLEAN');mods.append(mod)
            mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=co
            s=snapshot(ob,h);stages.append(dict(clean=s['clean'],euler=s['metrics']['euler'],faces=s['metrics']['faces']))
        result=audit(ob,hs);result['stages']=stages
        if observer is not None and preflight(hs)['passed'] and result['passed'] and all(x['clean'] for x in stages):
            dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);candidate=ev.to_mesh()
            try:observer(candidate)
            finally:ev.to_mesh_clear()
        for mod in reversed(mods):ob.modifiers.remove(mod)
        restored=snapshot(ob,hs[0]);result['rollback_exact']=restored['sha256']==base['sha256']
        assert result['rollback_exact']
        return result
    finally:
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
        for co,cm in cutters:bpy.data.objects.remove(co,do_unlink=True);bpy.data.meshes.remove(cm)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3';rows=[]
    for name,hs,expected,diagnostic in CASES:
        pre=preflight(hs);assert pre['passed']==expected
        # Unsafe requests never enter the normal operation path.
        # Only explicitly enumerated non-overlapping negatives are evaluated on isolated artificial copies.
        result=execute(hs) if pre['passed'] or diagnostic else None
        accepted=bool(pre['passed'] and result and result['passed'] and all(x['clean'] for x in result['stages']))
        row=dict(name=name,expected=expected,preflight=pre,diagnostic_only=not pre['passed'] and diagnostic,
                 native=result,accepted=accepted)
        assert not accepted or expected
        rows.append(row);print('PHASE164_ROW',json.dumps(row,allow_nan=False),flush=True)
    out=dict(complete=True,native_executed=True,approved=False,minimum_wall=MIN,rows=rows,elapsed=time.perf_counter()-start)
    P.mkdir(exist_ok=True);(P/'phase164_multi_hole_clearance.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE164_SUMMARY',json.dumps(dict(cases=len(rows),preflight_rejected=sum(not r['preflight']['passed'] for r in rows),
        accepted=sum(r['accepted'] for r in rows),native_cases=sum(r['native'] is not None for r in rows),
        diagnostic_rejected=sum(r['diagnostic_only'] and not r['native']['passed'] for r in rows),
        rollbacks=sum(r['native'] is not None and r['native']['rollback_exact'] for r in rows),elapsed=out['elapsed'])),flush=True)
    assert len(rows)==8 and all(not r['accepted'] for r in rows if not r['expected'])
if __name__=='__main__':main()
