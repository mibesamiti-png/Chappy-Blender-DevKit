"""Blender background comparison; --preflight runs without Blender. Native execution not yet verified.
blender -b --factory-startup --python-exit-code 1 --python phase112_native_benchmark.py -- --fixtures phase111_fixtures.json --out phase112_native_results.json
"""
import argparse, json, math, sys, time
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parent

def metrics(V,F,protected=None,source_faces=None):
    V=np.asarray(V,float);F=[tuple(map(int,f)) for f in F];edges=defaultdict(list);norm=[];val=defaultdict(set);zero=0
    if not np.isfinite(V).all() or any(len(f)<3 or min(f)<0 or max(f)>=len(V) or len(set(f))!=len(f) for f in F):raise ValueError('invalid mesh')
    for i,f in enumerate(F):
        P=V[list(f)];P=P-P[0];n=np.cross(P,np.roll(P,-1,axis=0)).sum(0);l=np.linalg.norm(n);zero+=int(l<=1e-12);norm.append(n/max(l,1e-30))
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))].append((i,a,b));val[a].add(b);val[b].add(a)
    counts=Counter(map(len,F));boundary=[e for e,fs in edges.items() if len(fs)==1];adj=defaultdict(set)
    for a,b in boundary:adj[a].add(b);adj[b].add(a)
    def comps(adj):
        unseen=set(adj);n=0
        while unseen:
            n+=1;todo=[unseen.pop()]
            while todo:
                for x in adj[todo.pop()] & unseen:unseen.remove(x);todo.append(x)
        return n
    def pkey(p):return tuple(np.round(p,5))
    def fkey(P):return tuple(sorted(pkey(p) for p in P))
    old=set() if source_faces is None else {fkey(np.asarray(protected)[f]) for f in source_faces};unchanged=[fkey(V[list(f)]) in old for f in F];local=[];all_angles=[];orientation=0
    for fs in edges.values():
        if len(fs)!=2:continue
        (i,a,b),(j,c,d)=fs;orientation+=int(a==c and b==d);angle=math.degrees(math.acos(float(np.clip(np.dot(norm[i],norm[j]),-1,1))));all_angles.append(angle)
        if not (unchanged[i] and unchanged[j]):local.append(angle)
    # Source preservation by nearest coordinate, not index. Tolerance in fixture model units.
    missing=None
    if protected is not None:
        P=np.asarray(protected);missing=int(sum(np.min(np.linalg.norm(V-p,axis=1))>1e-5 for p in P))
    # A manifold vertex link must be a single path (boundary) or cycle (interior).
    links=defaultdict(list)
    for f in F:
        for j,v in enumerate(f):links[v].append((f[j-1],f[(j+1)%len(f)]))
    bad_links=0
    for v,es in links.items():
        la=defaultdict(set)
        for a,b in es:la[a].add(b);la[b].add(a)
        deg=sorted(map(len,la.values()));bad_links+=int(comps(la)!=1 or (deg.count(1)!= (2 if v in adj else 0)) or any(d not in (1,2) for d in deg) or len(es)!=len({tuple(sorted(e)) for e in es}))
    return dict(vertices=len(V),faces=len(F),triangles=counts[3],quads=counts[4],ngons=sum(n for k,n in counts.items() if k>4),boundary_edges=len(boundary),boundary_loops=comps(adj),bad_boundary_vertices=sum(len(s)!=2 for s in adj.values()),nonmanifold_edges=sum(len(fs)>2 for fs in edges.values()),orientation_errors=orientation,zero_area_faces=zero,duplicate_faces=len(F)-len({tuple(sorted(f)) for f in F}),unused_vertices=len(V)-len(val),components=comps(val),bad_vertex_links=bad_links,euler=len(V)-len(edges)+len(F),max_valence=max(map(len,val.values()),default=0),local_max_dihedral=max(local,default=0.),global_max_dihedral=max(all_angles,default=0.),missing_protected_vertices=missing,unchanged_source_faces=sum(unchanged),expected_source_faces=len(old))

def grid(case):
    # 3 widths x 3 segment counts x 3 profiles; baseline .5 is not privileged by selector.
    return [dict(offset=case['offset_proxy']*w,width_ratio=w,segments=s,profile=p) for w in (.25,.5,.9) for s in (1,3,6) for p in (.3,.5,.7) if s!=1 or p==.5]

def preflight(d):
    rows=[]
    for c in d['cases']:
        if not c['eligible']:continue
        a=metrics(c['sharp']['vertices'],c['sharp']['faces'],c['protected'],c['source_faces']);b=metrics(c['custom']['vertices'],c['custom']['faces'],c['protected'],c['source_faces']);edges={tuple(sorted((x,y))) for f in c['sharp']['faces'] for x,y in zip(f,f[1:]+f[:1])};assert all(tuple(e) in edges for e in c['sharp']['edges'])
        for m in (a,b):
            assert m['missing_protected_vertices']==0 and m['unchanged_source_faces']==m['expected_source_faces'] and m['components']==1 and not any(m[k] for k in ('bad_boundary_vertices','nonmanifold_edges','orientation_errors','zero_area_faces','duplicate_faces','unused_vertices','bad_vertex_links'))
        assert a['boundary_loops']==b['boundary_loops'] and a['euler']==b['euler']
        rows.append(dict(name=c['name'],sharp=a,custom=b,native_candidates_planned=len(grid(c))))
    # Mixed-face, bow-tie vertex, winding and open-boundary checks independent of Blender.
    m=metrics([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[2,0,0]],[[0,1,2,3],[2,1,4]]);assert (m['triangles'],m['quads'],m['bad_vertex_links'],m['orientation_errors'])==(1,1,0,0)
    b=metrics([[0,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]],[[0,1,2],[0,3,4]]);assert b['bad_vertex_links']==1 and b['bad_boundary_vertices']==1
    w=metrics([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[2,0,0]],[[0,1,2,3],[1,2,4]]);assert w['orientation_errors']==1
    return dict(native_executed=False,rows=rows,controls_passed=3,native_candidates_planned=sum(r['native_candidates_planned'] for r in rows))

def face_signature(V,F):
    # Ignore vertex indices and face ordering, preserve cyclic edge connectivity.
    points=[tuple(np.round(v,5)) for v in V]
    def cycle(f):
        q=tuple(points[i] for i in f);r=q[::-1]
        return min(*(q[i:]+q[:i] for i in range(len(q))),*(r[i:]+r[:i] for i in range(len(r))))
    return tuple(sorted(cycle(f) for f in F))


def topology_ok(m,ref):
    keys=('bad_boundary_vertices','nonmanifold_edges','orientation_errors','zero_area_faces','duplicate_faces','unused_vertices','bad_vertex_links')
    return not any(m[k] for k in keys) and m['components']==1 and m['boundary_loops']==ref['boundary_loops'] and m['euler']==ref['euler']


def audited_ok(m,ref):
    return topology_ok(m,ref) and not any(m['audit'][k] for k in ('nonincident_bvh_overlap','degenerate_triangles'))


def screen_result(m,subs,ref,unchanged):
    reasons=[]
    if unchanged:reasons.append('no_effect_at_1e-5')
    if not audited_ok(m,ref):reasons.append('base_mesh_audit')
    if m['missing_protected_vertices']!=0:reasons.append('protected_vertex_loss')
    if m['unchanged_source_faces']!=m['expected_source_faces']:reasons.append('source_face_change')
    if len(subs)!=2 or not all(audited_ok(s,ref) for s in subs):reasons.append('subdivision_audit')
    return reasons


def native_run(d,out):
    import bpy,bmesh
    from mathutils.bvhtree import BVHTree
    def make_mesh(V,F):
        m=bpy.data.meshes.new('GL111');m.from_pydata(V,[],F);m.update();return m
    def audit(m):
        m.calc_loop_triangles();tri=[tuple(t.vertices) for t in m.loop_triangles];verts=[v.co.copy() for v in m.vertices];tree=BVHTree.FromPolygons(verts,tri,all_triangles=True,epsilon=0.0);pairs=set()
        for i,j in tree.overlap(tree):
            if i<j and not set(tri[i])&set(tri[j]):pairs.add((i,j))
        return dict(nonincident_bvh_overlap=len(pairs),degenerate_triangles=sum(t.area<=1e-12 for t in m.loop_triangles),triangles_checked=len(tri))
    def inspect(m,c=None):
        V=[tuple(v.co) for v in m.vertices];F=[tuple(p.vertices) for p in m.polygons];r=metrics(V,F,None if c is None else c['protected'],None if c is None else c['source_faces']);r['audit']=audit(m);return r
    def subdivision(m,level):
        ob=bpy.data.objects.new('GL111_subdiv',m);bpy.context.scene.collection.objects.link(ob)
        try:
            mod=ob.modifiers.new('GL111','SUBSURF');mod.levels=level;mod.render_levels=level;ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
            try:return inspect(mesh)
            finally:ev.to_mesh_clear()
        finally:bpy.data.objects.remove(ob,do_unlink=True)
    results=dict(native_executed=True,blender_version=bpy.app.version_string,complete=False,rows=[])
    for c in d['cases']:
        if not c['eligible']:continue
        base=c['sharp'];base_signature=face_signature(base['vertices'],base['faces']);cm=make_mesh(c['custom']['vertices'],c['custom']['faces']);ref=inspect(cm,c);ref['subdivision']=[subdivision(cm,l) for l in (1,2)];bpy.data.meshes.remove(cm);rows=[]
        for cfg in grid(c):
            m=make_mesh(base['vertices'],base['faces']);bm=bmesh.new();r=dict(config=cfg,status='error');start=time.perf_counter()
            try:
                bm.from_mesh(m);bm.verts.ensure_lookup_table();bm.verts.index_update();wanted=set(map(tuple,base['edges']));geom=[e for e in bm.edges if tuple(sorted(v.index for v in e.verts)) in wanted];assert len(geom)==len(wanted) and all(e.is_manifold for e in geom)
                bmesh.ops.bevel(bm,geom=geom,offset=cfg['offset'],offset_type='OFFSET',segments=cfg['segments'],profile=cfg['profile'],affect='EDGES',clamp_overlap=True,loop_slide=True,miter_outer='SHARP',miter_inner='SHARP');bm.normal_update();bm.to_mesh(m);m.update();x=inspect(m,c);subs=[subdivision(m,l) for l in (1,2)];unchanged=face_signature([tuple(v.co) for v in m.vertices],[tuple(f.vertices) for f in m.polygons])==base_signature;reasons=screen_result(x,subs,ref,unchanged);r.update(status='measured',metrics=x,screened=not reasons,screen_reasons=reasons,subdivision=subs)
            except Exception as e:r['error']=repr(e)
            finally:bm.free();bpy.data.meshes.remove(m);r['elapsed']=time.perf_counter()-start
            rows.append(r)
        results['rows'].append(dict(name=c['name'],custom=ref,custom_screened=not screen_result(ref,ref['subdivision'],ref,False),candidates=rows));out.write_text(json.dumps(results,indent=2,allow_nan=False));print(c['name'],len(rows),sum(r.get('screened',False) for r in rows),flush=True)
    results['complete']=True;out.write_text(json.dumps(results,indent=2,allow_nan=False))

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:];p=argparse.ArgumentParser();p.add_argument('--fixtures',type=Path,default=ROOT/'phase111_fixtures.json');p.add_argument('--out',type=Path,default=ROOT/'phase112_native_results.json');p.add_argument('--preflight',action='store_true');a=p.parse_args(args);d=json.loads(a.fixtures.read_text());t=time.perf_counter()
    if a.preflight:
        r=preflight(d);r['elapsed']=time.perf_counter()-t;a.out.write_text(json.dumps(r,indent=2,allow_nan=False));print(len(r['rows']),r['controls_passed'],r['native_candidates_planned'],r['elapsed'])
    else:native_run(d,a.out)
if __name__=='__main__':main()
