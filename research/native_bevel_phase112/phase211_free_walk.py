"""Phase211-E1: fixed spatial feet, then an unanchored chassis on a floor.
Ideal long-offset cross-slide couplings; actual cam/roller and pad/floor
collision meshes. Model units, no material or manufacturing certification.
"""
import json,math,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from mathutils import Vector
from phase211_four_leg_drive import setup,START,DUTY,FRAMES,PHASES
from phase211_support_design import FEET
from phase210_inverse_cam import law
from phase210_xy_cam import az,wrap
FLOOR_Y=-11.55
def run(name,free,enabled,friction,dest):
    sc,shaft,legs=setup(False,enabled,True,True,free,friction)
    chassis=bpy.data.objects['chassis reference']
    active=[o for o in sc.objects if o.rigid_body and o.rigid_body.type=='ACTIVE']
    assert len(active)==21+int(free)
    pads=[L['out'] for L in legs];others=[o for o in active if o not in pads]
    local={o.name:np.array([tuple(v.co) for v in o.data.vertices]) for o in active}
    mass=sum(o.rigid_body.mass for o in active)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/('phase211_walk_'+name+'.blend')))
    rows=[];travel=0.;last=None
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        mats={o.name:o.evaluated_get(dg).matrix_world.copy() for o in active}
        C=mats[chassis.name] if free else chassis.evaluated_get(dg).matrix_world.copy()
        inv=C.inverted();S=inv@mats[shaft.name];angle=az(S)
        if last is not None:travel+=wrap(angle-last)
        last=angle
        def bottom(o):
            M=mats[o.name];v=local[o.name]
            return float(np.min(v@np.array(tuple(M[1])[:3])+M[1][3]))
        com=sum((mats[o.name].translation*o.rigid_body.mass for o in active),Vector((0.,0.,0.)))/mass
        row=dict(frame=f,travel=travel,x=float(C.translation.x),y=float(C.translation.y),z=float(C.translation.z-6.5),
            tilt=math.degrees(math.acos(max(-1.,min(1.,float(C.to_3x3().col[1].normalized().y))))),
            shaft_drift=(S.translation-Vector((0.,6.,0.))).length,
            com_proxy_x=float(com.x),nonpad_floor_gap=min(bottom(o)-FLOOR_Y for o in others))
        support=0
        for j,L in enumerate(legs):
            phase=(START-travel+L['offset'])%math.tau
            P=inv@mats[L['out'].name];p=P.translation
            expected=Vector((float(FEET[j,0])+float(law(phase,'stride',DUTY))-1.2,
                -5.4+float(law(phase,'lift',DUTY)),float(FEET[j,1])))
            gap=bottom(L['out'])-FLOOR_Y
            support+=int(-.04<=gap<=.04)
            row.update({f'L{j}_error':(p-expected).length,f'L{j}_gap':gap,
                f'L{j}_x':float(p.x),f'L{j}_y':float(p.y),f'L{j}_z':float(p.z)})
        row['support_proxy']=support;rows.append(row)
    end=rows[-1];dx=end['x']-rows[0]['x'];dz=end['z']-rows[0]['z']
    err=max(r[f'L{j}_error'] for r in rows for j in range(4))
    tilt=max(r['tilt'] for r in rows);gap=min(r[f'L{j}_gap'] for r in rows for j in range(4))
    nonpad=min(r['nonpad_floor_gap'] for r in rows);supports=[r['support_proxy'] for r in rows]
    com_dx=end['com_proxy_x']-rows[0]['com_proxy_x']
    checks=dict(shaft_drift=max(r['shaft_drift'] for r in rows)<=.015,foot_tracking=err<=.04)
    if enabled:checks['full_cycle']=travel<=-math.tau
    else:checks['no_sustained_drive']=abs(travel)<=.4
    if free:
        checks.update(upright=tilt<=15.,no_nonpad_floor_contact=nonpad>=.02,pad_penetration=gap>=-.04)
        if enabled and friction>0:
            checks.update(forward=dx<=-.5,lateral=abs(dz)<=.5,
                supported=sum(n>=2 for n in supports)/len(supports)>=.95)
        elif enabled:
            # Origin-weighted COM proxy is only an approximate drift check;
            # not a claim of exact mass-centroid conservation.
            checks.update(no_net_propulsion=abs(dx)<=.5 and abs(com_dx)<=.5)
        else:checks.update(no_large_displacement=abs(dx)<=.5 and abs(dz)<=.5)
    out=dict(name=name,free=free,enabled=enabled,friction=friction,travel=travel,forward_dx=dx,lateral_dz=dz,
        max_tilt=tilt,max_foot_error=err,min_pad_gap=gap,min_nonpad_gap=nonpad,
        support_two_fraction=sum(n>=2 for n in supports)/len(supports),
        support_three_fraction=sum(n>=3 for n in supports)/len(supports),
        com_proxy_dx=com_dx,checks=checks,passed=all(checks.values()),rows=rows)
    print('PHASE211E1_CASE',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
    return out
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results'/'phase211_free_walk';dest.mkdir(parents=True,exist_ok=True)
    cases=[run('fixed_spatial',False,True,.8,dest)]
    if cases[0]['passed']:
        cases.append(run('free_engaged',True,True,.8,dest))
        if cases[-1]['passed']:
            cases.extend(run(n,True,e,f,dest) for n,e,f in [('frictionless',True,0.),('motor_off',False,.8)])
    out=dict(complete=True,native_executed=True,approved=False,walk_fixture_gate=len(cases)==4 and all(c['passed'] for c in cases),
        cases=cases,phases=PHASES,duty=DUTY,feet=FEET.tolist(),floor_y=FLOOR_Y,foot_radius=.4,
        chassis_mass=20.,ideal_offset_couplers=True,ideal_rigid_camshaft=True,support_is_geometric_proxy=True,
        com_is_origin_weighted_proxy=True,physical_manufacturing_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_free_walk.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211E1_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
