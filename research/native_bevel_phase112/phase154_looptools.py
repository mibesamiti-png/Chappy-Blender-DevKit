"""Phase 154: actual LoopTools Space/Relax vs polyline surrogate on fixed synthetic collars."""
import os,sys,json,time,hashlib,importlib.util
from pathlib import Path
import numpy as np
import bpy,bmesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase143_native_recheck import arrays,inspect,quad,domain,unpack
from phase112_native_benchmark import metrics,topology_ok
from phase120_native_sections import planes,evaluate
ROOT=Path(__file__).resolve().parent
RINGS={
'offset_single':(167,[17,85,18,110,26,130,25,104],[40,151,41,156,42,160,43,164]),
'low_wide':(177,[8,54,9,59,10,86,18,108,17,103,16,100],[40,153,41,158,42,162,43,166,44,170,45,174]),
'corner_two':(177,[9,59,10,63,11,90,19,111,18,107,17,84],[40,153,41,158,42,162,43,166,44,170,45,174])}
def load_extension():
    # A real addon preference entry must exist before register() updates its panels.
    # Import via Blender's addon lifecycle, not a synthetic module name.
    import addon_utils
    root=Path(os.environ['LOOPTOOLS_DIR']).resolve()
    assert root.name.isidentifier() and (root/'__init__.py').is_file()
    sys.path.insert(0,str(root.parent))
    name=root.name
    module=addon_utils.enable(name,default_set=True,persistent=False)
    assert module is not None and Path(module.__file__).resolve()==root/'__init__.py'
    assert name in bpy.context.preferences.addons
    assert hasattr(bpy.ops.mesh,'looptools_space') and hasattr(bpy.ops.mesh,'looptools_relax')
    return module
def unload_extension(module):
    import addon_utils
    errors=[]
    addon_utils.disable(module.__name__,default_set=True,handle_error=lambda exc:errors.append(repr(exc)))
    assert not errors,errors
    assert module.__name__ not in bpy.context.preferences.addons
def select_path(mesh,path,closed):
    bm=bmesh.from_edit_mesh(mesh);bm.verts.ensure_lookup_table()
    for f in bm.faces:f.select_set(False)
    for e in bm.edges:e.select_set(False)
    for v in bm.verts:v.select_set(False)
    pairs=list(zip(path,path[1:]))+([(path[-1],path[0])] if closed else [])
    for a,b in pairs:
        e=bm.edges.get((bm.verts[a],bm.verts[b]));assert e is not None
        e.select_set(True)
    assert sum(e.select for e in bm.edges)==len(pairs)
    bmesh.update_edit_mesh(mesh,loop_triangles=False,destructive=False)
def actual(mesh,paths,closed,op,interpolation,influence=100,iterations=1):
    bpy.context.scene.tool_settings.mesh_select_mode=(False,True,False)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        for path in paths:
            select_path(mesh,path,closed)
            if op=='space':
                r=bpy.ops.mesh.looptools_space(input='selected',interpolation=interpolation,influence=influence,lock_x=False,lock_y=False,lock_z=False)
            else:
                r=bpy.ops.mesh.looptools_relax(input='selected',interpolation=interpolation,iterations=str(iterations),regular=True)
            assert 'FINISHED' in r,r
    finally:bpy.ops.object.mode_set(mode='OBJECT')
def surrogate(V,path,closed,alpha):
    ids=list(path)+([path[0]] if closed else [])
    q=V[ids];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
    assert np.all(np.diff(s)>1e-10)
    t=np.linspace(0,s[-1],len(q));a=np.stack([np.interp(t,s,q[:,i]) for i in range(3)],axis=1)
    if closed:ids=ids[:-1];a=a[:-1]
    V[ids]=(1-alpha)*V[ids]+alpha*a
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    module=load_extension()
    fixtures={r['fixture']['name']:r['fixture'] for r in json.loads((ROOT/'phase133_holdout_frozen.json').read_text())['cases']}
    data={r['name']:r for r in json.loads((ROOT/'phase141_frozen_meshes.json').read_text())['cases']}
    configs=[('keep','axial','linear',0,0)]
    for d in ('axial','circ'):
        configs += [('surrogate',d,'linear',a,1) for a in (25,50,100)]
        configs += [('space',d,i,a,1) for i in ('linear','cubic') for a in (25,50,100)]
        configs += [('relax',d,i,100,n) for i in ('linear','cubic') for n in (1,3)]
    configs += [('space_relax',d,'cubic',50,1) for d in ('axial','circ')]
    rows=[]
    try:
        for name,label in [('offset_single','offset_single'),('low_wide','low_wide'),('corner_two','corner_before'),('corner_two','corner_after')]:
            c=data[name];F=[tuple(f) for f in c['faces']];V=np.asarray(c['vertices'],dtype=np.float32).astype(float)
            if label=='corner_after':
                obj=(ROOT/'phase142_corner_two_selected.obj').read_text().splitlines()
                V=np.asarray([list(map(float,l.split()[1:])) for l in obj if l.startswith('v ')],dtype=np.float32).astype(float)
                assert F==[tuple(int(i)-1 for i in l.split()[1:]) for l in obj if l.startswith('f ')]
            nb,a,b=RINGS[name];n=len(a);steps=c['config']['steps']
            assert len(V)==nb+(steps-1)*n
            ring=np.vstack([a,np.arange(nb,len(V)).reshape(steps-1,n),b])
            sharp=fixtures[name]['sharp'];orig=evaluate(sharp['vertices'],sharp['faces'],planes(fixtures[name]))
            assert orig['complete'];base=metrics(V,F);records=[]
            for op,d,i,alpha,it in configs:
                m=bpy.data.meshes.new('p154');m.from_pydata(V.tolist(),[],F);m.update()
                ob=bpy.data.objects.new('p154',m);bpy.context.scene.collection.objects.link(ob)
                bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
                paths=ring.T.tolist() if d=='axial' else ring[1:-1].tolist();closed=d=='circ'
                r=dict(op=op,direction=d,interpolation=i,influence=alpha,iterations=it,passed=False)
                try:
                    if op=='surrogate':
                        Y=V.copy()
                        for path in paths:surrogate(Y,path,closed,alpha/100)
                        for v,p in zip(m.vertices,Y):v.co=p
                        m.update()
                    elif op in ('space','relax','space_relax'):
                        actual(m,paths,closed,'relax' if op=='relax' else 'space',i,alpha,it)
                        if op=='space_relax':actual(m,paths,closed,'relax',i,100,1)
                    X,H=arrays(m);assert H==F and X.shape==V.shape
                    fixed=float(np.linalg.norm(X[:nb]-V[:nb],axis=1).max());q=quad(X,H[c['audit_start']:])
                    A=X[np.asarray(H[c['audit_start']:])];e=np.linalg.norm(np.roll(A,-1,axis=1)-A,axis=2)
                    r.update(fixed_error=fixed,displacement=float(np.linalg.norm(X-V,axis=1).max()),quad=q,max_edge_ratio=float(np.max(e.max(1)/e.min(1))))
                    if fixed<=1e-6 and q['passed']:
                        audit=inspect(m,base,0);r['audit_pass']=audit['passed']
                        if audit['passed']:
                            Q=np.asarray(H);T0=np.concatenate([Q[:,[0,1,2]],Q[:,[0,2,3]]]);T1=np.concatenate([Q[:,[0,1,3]],Q[:,[1,2,3]]]);m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
                            checks=[domain(X,tri,sharp,unpack(c[k]),orig) for tri in (T,T0,T1) for k in ('planes','fixed_planes')]
                            r['checks']=checks
                            if all(x['complete'] for x in checks):
                                r['max_turn']=max(x['max_turn'] for x in checks);r['extent_upper']=max(x['extent_upper'] for x in checks)
                                r['passed']=r['max_turn']<=30 and r['extent_upper']<=.4
                except Exception as exc:r['error']=repr(exc)
                finally:
                    if ob.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
                records.append(r)
            best=min((r for r in records if r['passed']),key=lambda r:(r['max_edge_ratio'],r['max_turn']),default=None)
            row=dict(name=label,records=records,selected=best);rows.append(row)
            print('PHASE154_ROW',json.dumps(dict(name=label,measured=len(records),errors=sum('error'in r for r in records),baseline=records[0],best=best,passed={op:sum(r['passed'] for r in records if r['op']==op) for op in sorted({r['op'] for r in records})}),allow_nan=False),flush=True)
    finally:unload_extension(module)
    out=dict(approved=False,native_executed=True,complete=True,version=bpy.app.version_string,extension=json.loads(Path(os.environ['LOOPTOOLS_PROVENANCE']).read_text()),rows=rows,elapsed=time.perf_counter()-start)
    p=ROOT/'results';p.mkdir(exist_ok=True);(p/'phase154_looptools.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE154_SUMMARY',json.dumps(dict(cases=len(rows),candidates=sum(len(r['records']) for r in rows),errors=sum('error'in x for r in rows for x in r['records']),elapsed=out['elapsed'],extension=out['extension'])),flush=True)
    assert len(rows)==4 and all(len(r['records'])==29 for r in rows)
if __name__=='__main__':main()
