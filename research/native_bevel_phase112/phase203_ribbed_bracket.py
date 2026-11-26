"""Phase 203: add one central gusset to the qualified rounded L-bracket.
Fixed synthetic geometry, native Exact union/bevel/drill, existing audits.
Geometry only: no strength or print certification.
"""
import json,math,sys,time
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase201_l_bracket import blank,holes,preflight,frame,audit,T,MIN,EPS
from phase202_rounded_bracket import edge_samples
from phase167_protected_local_bevel import apply,signature
from phase195_tapered_spacer import drill,write_obj
from phase196_spacer_verification import Rays,ray_controls
from phase160_operation_contracts import measure
from phase171_planar_topology_variants import arrays
from phase163_hole_contracts import make
ROOT=Path(__file__).resolve().parent
W=.04
def rib_union(m,half):
    # Overlap the two flanges by .15; exposed right triangle has legs .5.
    v=[(x,y,z) for y in (-half,half) for x,z in ((.35,.35),(1.15,.35),(.35,1.15))]
    f=[(0,1,2),(5,4,3)]+[((i+1)%3,i,i+3,(i+1)%3+3) for i in range(3)]
    co,cm=make('p203_gusset',v,f)
    ob=bpy.data.objects.new('p203_blank',m);bpy.context.scene.collection.objects.link(ob)
    try:
        mod=ob.modifiers.new('gusset','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=co
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        out=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
        out.update();return out
    finally:
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.objects.remove(co,do_unlink=True);bpy.data.meshes.remove(cm)
def rib_samples(m):
    rays=Rays(m)
    return [rays.cast((x,s*.7,z),(0,-s,0),1.4)
            for x,z in ((.65,.65),(.75,.60),(.60,.75)) for s in (-1,1)]
def run(hs,half,probe,path):
    m=blank();before=signature(*arrays(m));current=m;stages=[]
    if path.exists():path.unlink()
    p=preflight(hs)
    # Bounding box of exposed rib, with conservative allowance for bevel.
    clearance=min(math.hypot(max(0,h['u']-1.),max(0,abs(h['y'])-half))-h['r']-W for h in hs)
    def finish(status,**kw):
        return dict(status=status,source_unchanged=signature(*arrays(m))==before,
                    exported=path.exists(),stages=stages,clearance=clearance,**kw)
    try:
        if not p['passed'] or min(p['margins'])-2*W<MIN or not .08<=half<=.4 or clearance<MIN:
            return finish('preflight_rejected')
        current=m.copy() if probe=='skip_rib' else rib_union(m,half)
        a=measure(current,'cube');q=a['metrics'];samples=rib_samples(current)
        expected=3.5+.125*2*half
        checks=dict(clean=a['clean'],closed=q['boundary_edges']==0 and q['euler']==2,
                    volume=abs(a['volume']-expected)<=EPS,
                    bounds=bool(np.max(np.abs(np.asarray(a['bounds'])-[[0,-1,0],[2,1,2]]))<=EPS),
                    rib=all(x is not None and abs(x-(.7-half))<=EPS for x in samples))
        stages.append(dict(step='union',checks=checks,volume=a['volume'],expected=expected,samples=samples))
        if not all(checks.values()):return finish('rib_rejected')
        original=measure(current,'cube');raw=edge_samples(current)
        count=apply(current,'all',W) if probe!='skip_rounding' else 0
        rounded=measure(current,'cube');q=rounded['metrics'];edges=edge_samples(current);rib=rib_samples(current)
        checks=dict(clean=rounded['clean'],closed=q['boundary_edges']==0 and q['euler']==2,
            bounds=bool(np.max(np.abs(np.asarray(rounded['bounds'])-original['bounds']))<=EPS),
            changed=count>0 and rounded['oblique_faces']>0 and abs(rounded['volume']-original['volume'])>EPS
                and abs(rounded['volume']-original['volume'])<.05*original['volume'],
            edges=all(x is not None and y is not None and y-x>W*.1 for x,y in zip(raw,edges)),
            rib=all(x is not None and abs(x-(.7-half))<=W+EPS for x in rib))
        stages.append(dict(step='rounding',checks=checks,volume=rounded['volume'],edges=count))
        if not all(checks.values()):return finish('rounding_rejected')
        for i,h in enumerate(hs):
            c,M=frame(h);new=drill(current,c,M,.6,h['r']*(.8 if probe=='wrong_radius' and i==0 else 1))
            bpy.data.meshes.remove(current);current=new
            z=measure(current,'cube');stages.append(dict(step='drill',clean=z['clean'],euler=z['metrics']['euler']))
        a=audit(current,hs);a['expected_volume']+=rounded['volume']-3.5
        a['checks']['volume']=abs(a['volume']-a['expected_volume'])<=EPS
        def same(x,y):return all(i is not None and j is not None and abs(i-j)<=EPS for i,j in zip(x,y))
        a['checks']['rounding_retained']=same(edges,edge_samples(current))
        a['checks']['rib_retained']=same(rib,rib_samples(current))
        a['passed']=all(a['checks'].values()) and all(s['clean'] for s in stages[2:])
        if a['passed'] and probe=='normal':write_obj(current,path)
        return finish('complete' if a['passed'] else 'audit_rejected',audit=a)
    finally:
        if current!=m:bpy.data.meshes.remove(current)
        bpy.data.meshes.remove(m)
def main():
    assert bpy.app.version_string=='4.4.3';assert ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    bad=holes();bad[0]['u']=.65
    cases=[('ribbed',holes(),.14,'normal','complete'),
           ('oversize_rib',holes(),.35,'normal','preflight_rejected'),
           ('bad_hole',bad,.14,'normal','preflight_rejected'),
           ('skip_rib',holes(),.14,'skip_rib','rib_rejected'),
           ('skip_rounding',holes(),.14,'skip_rounding','rounding_rejected'),
           ('wrong_radius',holes(),.14,'wrong_radius','audit_rejected')]
    rows=[]
    for name,hs,half,probe,expected in cases:
        r=run(hs,half,probe,dest/f'phase203_{name}.obj')
        row=dict(name=name,half_width=half,expected=expected,matched=r['status']==expected,**r)
        rows.append(row);print('PHASE203_ROW',json.dumps(row,allow_nan=False),flush=True)
    gate=len(rows)==6 and all(r['matched'] and r['source_unchanged'] and r['exported']==(r['expected']=='complete')
        and (r['expected']!='preflight_rejected' or not r['stages']) for r in rows)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,rows=rows,elapsed=time.perf_counter()-start)
    (dest/'phase203_ribbed_bracket.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE203_SUMMARY',json.dumps(dict(cases=len(rows),matched=sum(r['matched'] for r in rows),
        parts=sum(r['exported'] for r in rows),gate=gate,elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
