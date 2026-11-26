"""Phase210-A: invert prescribed periodic translation into roller cam profiles.
External radial translating roller; positive profile parameter corresponds to
negative cam rotation. Independent polygon-segment distance test, not a
physical contact-force or return mechanism demonstration.
"""
import math,json,time,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
N=720;CHECK=1440;ROLLER=.25;DUTY=.75
def law(t,kind,duty=DUTY):
    u=np.mod(np.asarray(t)/math.tau,1.)
    q=np.clip((u-duty)/(1-duty),0.,1.)
    if kind=='lift':
        return np.where(u<=duty,0.,.6*64*q**3*(1-q)**3)
    A=2.4;k=A*(1-duty)/duty
    return np.where(u<=duty,A*u/duty,A+k*q-(A+k)*(10*q**3-15*q**4+6*q**5))
def pitch(t,kind,R,duty=DUTY):
    s=R+law(t,kind,duty);h=1e-4
    v=(law(t+h,kind,duty)-law(t-h,kind,duty))/(2*h)
    a=(law(t+h,kind,duty)-2*law(t,kind,duty)+law(t-h,kind,duty))/(h*h)
    e=np.stack((np.cos(t),np.sin(t)),axis=-1)
    tangent=np.stack((-np.sin(t),np.cos(t)),axis=-1)
    speed=np.hypot(s,v)
    normal=(s[:,None]*e-v[:,None]*tangent)/speed[:,None]
    curvature=(s*s+2*v*v-s*a)/speed**3
    return s[:,None]*e,normal,e,np.degrees(np.arctan2(abs(v),s)),1-ROLLER*curvature
def profile(kind,R,naive=False,duty=DUTY):
    t=np.arange(N)*math.tau/N
    p,n,e,_,_=pitch(t,kind,R,duty)
    return p-ROLLER*(e if naive else n)
def audit(kind,R,naive=False,duty=DUTY):
    c=profile(kind,R,naive,duty);a=c;b=np.roll(c,-1,axis=0);edge=b-a
    t=(np.arange(CHECK)+.37)*math.tau/CHECK
    p,normal,e,pressure,factor=pitch(t,kind,R,duty)
    # Every test roller center against every polygon edge, not its
    # construction vertex. A distant edge can cause an envelope collision.
    errors=[];inside=0
    for i in range(0,len(p),48):
        P=p[i:i+48];delta=P[:,None,:]-a[None,:,:]
        f=np.clip(np.sum(delta*edge[None,:,:],axis=2)/np.sum(edge*edge,axis=1),0.,1.)
        dist=np.sqrt(np.sum((delta-f[:,:,None]*edge[None,:,:])**2,axis=2)).min(axis=1)
        errors.extend((dist-ROLLER).tolist())
        y=P[:,1,None];x=P[:,0,None]
        crossing=((a[:,1]>y)!=(b[:,1]>y))
        xx=a[:,0]+(y-a[:,1])*edge[:,0]/np.where(abs(edge[:,1])>1e-15,edge[:,1],1e-15)
        inside+=int(np.sum(np.sum(crossing&(x<xx),axis=1)%2))
    turn=np.arctan2(a[:,0]*b[:,1]-a[:,1]*b[:,0],np.sum(a*b,axis=1))
    stats=dict(kind=kind,pitch_base=R,naive=naive,pressure_max=float(pressure.max()),
        min_offset_factor=float(factor.min()),min_polar_step=float(turn.min()),
        winding=float(turn.sum()/math.tau),min_profile_radius=float(np.linalg.norm(c,axis=1).min()),
        min_gap=min(errors),max_gap=max(errors),inside_count=inside)
    stats['passed']=bool(stats['pressure_max']<=30 and stats['min_offset_factor']>.05
        and stats['min_polar_step']>0 and abs(stats['winding']-1)<1e-8 and inside==0
        and max(abs(stats['min_gap']),abs(stats['max_gap']))<=.002)
    return c,stats
def main():
    import bpy
    from phase206_hybrid_machine import ring,key_check,BORE
    from phase195_tapered_spacer import write_obj
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    rows=[]
    for i,(kind,R) in enumerate((('lift',2.5),('stride',7.))):
        c,a=audit(kind,R)
        # Reuse the manifold ring builder with the existing keyed shaft bore.
        inner=[tuple(v*BORE/max(abs(v))) for v in c]
        M,mesh=ring('cam_'+kind,[tuple(v) for v in c],inner)
        a['mesh_passed']=bool(mesh['passed'] and key_check(M))
        a['passed'] &= a['mesh_passed']
        ob=bpy.data.objects.new('cam_'+kind,M);bpy.context.collection.objects.link(ob)
        ob.location.x=0. if i==0 else 15.
        ob.color=(.8,.55,.15,1) if i==0 else (.25,.55,.8,1)
        write_obj(M,dest/('phase210_cam_'+kind+'.obj'))
        rows.append(a)
        print('PHASE210A_PROFILE',json.dumps(a,allow_nan=False),flush=True)
    negatives=[audit('lift',2.5,True)[1],audit('stride',7.,True)[1],audit('stride',2.)[1]]
    controls=dict(radial_subtraction_lift=not negatives[0]['passed'] and negatives[0]['min_gap']<-.002,
        radial_subtraction_stride=not negatives[1]['passed'] and negatives[1]['min_gap']<-.002,
        undersized_stride_pressure=not negatives[2]['passed'] and negatives[2]['pressure_max']>30)
    gate=all(a['passed'] for a in rows) and all(controls.values())
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,profiles=rows,
        controls=controls,negative_cases=negatives,profile_samples=N,independent_samples=CHECK,
        roller_radius=ROLLER,stance_fraction=DUTY,nominal_stride=2.4,nominal_lift=.6,
        physical_contact_certified=False,walking_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase210_inverse_cam.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE210A_SUMMARY',json.dumps(out,allow_nan=False),flush=True)
    if gate:bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase210_inverse_cam.blend'))
    assert gate
if __name__=='__main__':main()
