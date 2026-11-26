"""Phase 207: bounded foot-path synthesis and four-leg geared demonstrator.
Fixed four-bar topology, searched six dimensions; not arbitrary mechanism
invention, ground dynamics, continuous collision, or a physical walking proof.
The two chassis rails are externally fixed relative to each other.
"""
import json,math,time,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
TAU=2*math.pi
def rng(seed):
    while True:
        seed=(1664525*seed+1013904223)&0xffffffff
        yield seed/4294967296
def points(z,theta):
    r,d,l,m,u,v=z
    theta=np.asarray(theta);B=np.stack((r*np.cos(theta),r*np.sin(theta)),axis=-1)
    D=np.array([d,0.]);delta=D-B;s=np.linalg.norm(delta,axis=-1)
    a=(l*l-m*m+s*s)/(2*s);h2=l*l-a*a
    if np.any(h2<=0):return None
    e=delta/s[...,None];perp=np.stack((e[...,1],-e[...,0]),axis=-1)
    C=B+a[...,None]*e+np.sqrt(h2)[...,None]*perp
    e=(C-B)/l;F=B+u*e+v*np.stack((-e[...,1],e[...,0]),axis=-1)
    return B,C,F
def evaluate(z,N,refine):
    r,d,l,m,u,v=z
    if not (.30<=r<=.90 and 1.1<=d<=2.0 and .8<=l<=3.8 and .8<=m<=3.8 and 0<=u<=4.5 and abs(v)<=2.8):return None
    if d-r<=abs(l-m)+.08 or d+r>=l+m-.08:return None
    p=points(z,np.arange(N)*TAU/N)
    if p is None:return None
    B,C,F=p
    # Neighboring legs share a plane, with 4.8 units between crank axes.
    # Conservative XY envelope incl. both link and foot outline.
    if max(F[:,0].max(),C[:,0].max(),d)-min(F[:,0].min(),B[:,0].min(),0.)>4.8-.54:return None
    i=(np.arange(N)[:,None]+np.arange(N//2+1)[None,:])%N
    X=F[i,0];Y=F[i,1];dx=X[:,-1]-X[:,0];stroke=np.abs(dx)
    reverse=np.maximum(0.,-np.sign(dx)[:,None]*np.diff(X,axis=1)).sum(axis=1)
    low=Y.min(axis=1);high=Y.max(axis=1);flat=high-low;lift=F[:,1].max()-high
    ok=(stroke>=(1.5 if refine else .7))&(lift>=(.35 if refine else .25))&(reverse<=.04)&(low-F[:,1].min()<=.05)&(high<=-.35)
    if not ok.any():return None
    score=flat/np.maximum(stroke,1e-12)+reverse/np.maximum(stroke,1e-12)+(.015 if refine else .025)/np.maximum(lift,1e-12)
    s=int(np.argmin(np.where(ok,score,np.inf)))
    return dict(dimensions=list(z),phase=s*TAU/N,stroke=float(stroke[s]),flat=float(flat[s]),lift=float(lift[s]),reverse=float(reverse[s]),score=float(score[s]),direction=int(np.sign(dx[s])))
def search():
    random=rng(207);best=None;count=0
    for _ in range(16000):
        z=[.35+next(random)*.35,1.1+next(random)*1.3,1.+next(random)*1.8,1.+next(random)*1.8,-1.+next(random)*4.5,-2.+next(random)*3.]
        q=evaluate(z,72,False)
        if q is not None:
            count+=1
            if best is None or q['score']<best['score']:best=q
    assert best is not None
    best=evaluate(best['dimensions'],120,True);assert best is not None
    random=rng(208);improved=0
    for i in range(3500):
        scale=.15 if i<1000 else .06 if i<2200 else .018
        q=evaluate([x+(next(random)-.5)*scale for x in best['dimensions']],120,True)
        if q is not None and q['score']<best['score']:best=q;improved+=1
    best.update(coarse_candidates=16000,coarse_feasible=count,refinement_candidates=3500,refinement_improvements=improved)
    return best
def motion(z,t):
    B,C,F=points(z,float(t));return B,C,F
def dense(best):
    z=best['dimensions'];r,d,l,m,u,v=z
    T=best['phase']+np.arange(361)*TAU/360
    B,C,F=points(z,T);stance=F[:181];s=float(abs(stance[-1,0]-stance[0,0]));flat=float(np.ptp(stance[:,1]));lift=float(F[:,1].max()-stance[:,1].max())
    reverse=float(np.maximum(0.,-best['direction']*np.diff(stance[:,0])).sum())
    err=max(float(np.max(abs(np.linalg.norm(B,axis=1)-r))),float(np.max(abs(np.linalg.norm(C-B,axis=1)-l))),float(np.max(abs(np.linalg.norm(C-[d,0],axis=1)-m))))
    return dict(stroke=s,flat=flat,lift=lift,reverse=reverse,flat_ratio=flat/s,closure_error=err,passed=s>=1.5 and flat/s<=.12 and lift>=.35 and reverse<=.05 and err<1e-9,foot_path=F.tolist())
def main():
    import bpy
    from phase204_four_bar import make_link_attempt,make_pin,prism,tree,LINK_R,HOLE_R,THICK,EPS
    from phase206_hybrid_machine import capsule,square,cut,closed,area_circle,bore_check,key_check,gear,shaft,retry,collision
    from phase195_tapered_spacer import drill,basis,write_obj
    from phase196_spacer_verification import ray_controls
    from phase160_operation_contracts import measure
    assert bpy.app.version_string=='4.4.3' and ray_controls()
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    best=search();D=dense(best);print('PHASE207_SEARCH',json.dumps({**best,**{k:v for k,v in D.items() if k!='foot_path'}}),flush=True)
    assert D['passed']
    z=best['dimensions'];r,d,l,m,u,v=z;parts={};audits={}
    def add(n,result):
        parts[n],audits[n]=result
        print('PHASE207_PART',json.dumps(dict(name=n,passed=audits[n]['passed'])),flush=True)
    def round_drills(name,outline,holes,shift,reverse=False,key=False):
        M=prism(name,[(x-shift,y) for x,y in outline],-THICK/2,THICK/2)
        base=measure(M,'cube');stages=[]
        for x,y in (list(reversed(holes)) if reverse else holes):
            out=drill(M,np.array([x-shift,y,0.]),basis((0,0,1)),.4,HOLE_R)
            bpy.data.meshes.remove(M);M=out;stages.append(measure(M,'cube'))
        if key:
            out=cut(M,prism('key',[(x-shift,y) for x,y in square(.094)],-.3,.3));bpy.data.meshes.remove(M);M=out;stages.append(measure(M,'cube'))
        for w in M.vertices:w.co.x+=shift
        M.update();a=closed(M,len(holes)+int(key),base['volume']-(len(holes)*area_circle(HOLE_R)+int(key)*4*.094**2)*THICK)
        a['stages_clean']=base['clean'] and all(s['clean'] for s in stages)
        a['bores']=all(bore_check(M,x,y) for x,y in holes)
        a['key']=not key or key_check(M)
        a['passed'] &= a['stages_clean'] and a['bores'] and a['key'];return M,a
    def hull(pts):
        def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
        def half(p):
            H=[]
            for q in p:
                while len(H)>1 and cross(H[-2],H[-1],q)<=1e-12:H.pop()
                H.append(q)
            return H
        p=sorted(set(pts));return half(p)[:-1]+half(p[::-1])[:-1]
    foot=hull([(x+LINK_R*math.cos(i*TAU/32),y+LINK_R*math.sin(i*TAU/32)) for x,y in ((0.,0.),(l,0.),(u,v)) for i in range(32)])
    # Two side chassis rails carry three gear shafts and two fixed rocker pivots.
    holes=[(x,0.) for x in (-2.4,-2.4+d,0.,2.4,2.4+d)]
    for side in (-1,1):
        tag='L' if side<0 else 'R'
        add('rail_'+tag,retry('rail_'+tag,[lambda s=s,o=o:round_drills('rail',capsule(-2.4,2.4+d),holes,s,o) for s,o in ((.3,False),(0.,True),(.7,True))]))
        for end in ('F','B'):
            k=tag+end
            add(k+'_crank',retry(k+'_crank',[lambda s=s:round_drills('crank',capsule(0.,r),[(r,0.)],s,key=True) for s in (r/2,0.,.13)]))
            add(k+'_rocker',retry(k+'_rocker',[lambda mode=mode:make_link_attempt('rocker',m,mode) for mode in ('centered','baseline','reversed')]))
            add(k+'_foot',retry(k+'_foot',[lambda s=s,o=o:round_drills('foot',foot,[(0.,0.),(l,0.)],s,o) for s,o in ((l/2,False),(0.,True),(.37,True))]))
            for j in ('B','C','D'):add(k+'_pin_'+j,make_pin('pin',.68))
    for j in range(3):
        add('gear_'+str(j),gear(24));add('shaft_'+str(j),shaft('shaft',0.,2.5 if j!=1 else 1.86))
    def tr(t):
        out={}
        for j,x in enumerate((-2.4,0.,2.4)):
            a=t if j!=1 else math.pi/24-t
            out['gear_'+str(j)]=(x,0.,0.,a)
            out['shaft_'+str(j)]=(x,0.,-1.25 if j!=1 else -.93,a)
        for side in (-1,1):
            tag='L' if side<0 else 'R';out['rail_'+tag]=(0.,0.,side*.75,0.)
            for end,x in (('F',-2.4),('B',2.4)):
                k=tag+end;angle=t+(math.pi if (side<0) == (end=='F') else 0.)
                B,C,F=motion(z,angle)
                def place(p,a,h):return (float(p[0]+x),float(p[1]),side*h,float(a))
                def pin(p,h1,h2):return (float(p[0]+x),float(p[1]),min(side*h1,side*h2)-.18,0.)
                out[k+'_crank']=place((0.,0.),angle,1.07)
                out[k+'_rocker']=place((d,0.),math.atan2(C[1],C[0]-d),1.07)
                out[k+'_foot']=place(B,math.atan2(C[1]-B[1],C[0]-B[0]),1.39)
                out[k+'_pin_B']=pin(B,1.07,1.39);out[k+'_pin_C']=pin(C,1.07,1.39);out[k+'_pin_D']=pin((d,0.),.75,1.07)
        return out
    angles=[best['phase']+i*TAU/360 for i in range(361)]
    hits=[]
    for i,t in enumerate(angles):
        h=collision(parts,tr(t));hits.append(dict(angle=i,pairs=h))
    test=tr(angles[0]);bad=dict(test);x,y,h,a=bad['gear_1'];bad['gear_1']=(x,y,h,a+math.pi/24)
    wrong=collision(parts,bad)
    controls=dict(impossible_lengths=points((.7,2.,.2,.2,1.,0.),[0.]) is None,wrong_gear_phase=any(all(n.startswith('gear_') for n in p) for p in wrong))
    gate=D['passed'] and all(a['passed'] for a in audits.values()) and not any(h['pairs'] for h in hits) and all(controls.values())
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,search=best,dense=D,parts=audits,mesh_collisions=hits,controls=controls,physical_walk_certified=False,continuous_certified=False,externally_fixed_rails=True,elapsed=time.perf_counter()-start)
    (dest/'phase207_walking_machine.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE207_SUMMARY',json.dumps(dict(gate=gate,parts=sum(a['passed'] for a in audits.values()),part_count=len(parts),poses=len(hits),collision_poses=sum(bool(h['pairs']) for h in hits),collision_examples=[h for h in hits if h['pairs']][:3],controls=controls,elapsed=out['elapsed'])),flush=True)
    if gate:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        root=bpy.data.objects.new('upright assembly',None);bpy.context.collection.objects.link(root);root.rotation_euler.x=math.pi/2
        obs={};last={}
        for n,M in parts.items():
            ob=bpy.data.objects.new(n,M);bpy.context.collection.objects.link(ob);ob.parent=root;obs[n]=ob
            ob.color=(.8,.55,.16,1) if n.startswith('gear') else (.25,.65,.45,1) if n.endswith('_foot') else (.3,.4,.58,1)
        for i,t in enumerate(angles):
            for n,(x,y,h,a) in tr(t).items():
                if n in last:a=last[n]+math.atan2(math.sin(a-last[n]),math.cos(a-last[n]))
                last[n]=a;ob=obs[n];ob.location=(x,y,h);ob.rotation_euler.z=a
                ob.keyframe_insert(data_path='location',frame=i+1);ob.keyframe_insert(data_path='rotation_euler',frame=i+1)
        for ob in obs.values():
            for fc in ob.animation_data.action.fcurves:
                for k in fc.keyframe_points:k.interpolation='LINEAR'
        scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=361;scene.render.fps=30;scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase207_walking_machine.blend'))
        for n,M in parts.items():write_obj(M,dest/f'phase207_{n}.obj')
    assert gate
if __name__=='__main__':main()
