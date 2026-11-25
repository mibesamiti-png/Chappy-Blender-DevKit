"""R15 diagnostic: isolate periodic U wrap, with strict boundary rejection.
No changes to original mesh, source UV, V coordinates, or product code.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
try:
    from cycles.r14.audit import uv_audit, incidence
except ModuleNotFoundError:
    from audit import uv_audit, incidence  # archived local reproduction

TOL=1e-5
MAX_SPAN=.5


def lift_face(uv, pins=()):
    """Return deterministic minimum-span lift, or None if short span impossible.
    The original local U span must be <=1 (the supported one-period input).
    Only integer U shifts, and all specified corner indices remain exact.
    """
    uv=np.asarray(uv,dtype=float)
    pins=set(pins)
    if uv.shape!=(3,2) or not np.isfinite(uv).all() or np.ptp(uv[:,0])>1+TOL:
        raise ValueError('unsupported one-period triangle')
    if any(i not in (0,1,2) for i in pins): raise ValueError('invalid pin')
    anchor=min(pins) if pins else 0
    options=[(0,) if i==anchor or i in pins else (-1,0,1) for i in range(3)]
    best=None
    for shift in itertools.product(*options):
        span=float(np.ptp(uv[:,0]+shift))
        if span>MAX_SPAN+TOL: continue
        key=(round(span,12),sum(abs(x) for x in shift),shift)
        if best is None or key<best[0]: best=(key,shift)
    if best is None: return None
    out=uv.copy(); out[:,0]+=best[1]
    return out


def boundary_pins(row):
    faces=np.asarray(row['strip_faces'],int); uv=np.asarray(row['bridge_corner_uvs'],float)
    # R11 create_source iterates boundary_edges in triangle insertion order.
    # Reconstruct directed edge order, not a sorted-by-index list.
    directed={}
    for i,t in enumerate(faces):
        for j in range(3):
            a,b=int(t[j]),int(t[(j+1)%3]); key=tuple(sorted((a,b)))
            directed.setdefault(key,[]).append((i,j,(j+1)%3))
    edges=[e[0] for e in directed.values() if len(e)==1]
    samples=np.asarray(row['boundary_pair_uv_samples'],float)
    if samples.shape!=(2*len(edges),2,2) or len(edges)!=row['expected_shared_edges']:
        raise ValueError('missing exact boundary correspondence')
    pins={}; wide=[]
    for idx,(face,j,k) in enumerate(edges):
        original=samples[2*idx:2*idx+2,0,:]
        recorded=samples[2*idx:2*idx+2,1,:]
        if np.max(np.abs(uv[face,[j,k]]-recorded))>TOL:
            raise ValueError('boundary evidence mismatch')
        for corner,point in zip((j,k),original):
            if (face,corner) in pins and np.max(np.abs(pins[(face,corner)]-point))>TOL: raise ValueError('conflicting original UV pins')
            pins[(face,corner)]=point
        if abs(original[1,0]-original[0,0])>MAX_SPAN+3*TOL:
            wide.append(dict(face=face,corners=[j,k],source_u_span=float(abs(original[1,0]-original[0,0]))))
    return pins,wide


def metrics(row,uv):
    result=uv_audit(row['strip_vertices'],row['strip_faces'],uv)
    result.pop('signed_areas')
    edges=incidence(np.asarray(row['strip_faces'],int)); f=np.asarray(row['strip_faces'],int); v=np.asarray(row['strip_vertices'],float)
    seams=0; length=0.
    for (a,b),ref in edges.items():
        if len(ref)!=2: continue
        p,q=ref; d=dict(zip(f[p],uv[p])); e=dict(zip(f[q],uv[q]))
        if max(np.max(np.abs(d[k]-e[k])) for k in (a,b))>TOL:
            seams+=1; length+=float(np.linalg.norm(v[a]-v[b]))
    result.update(seam_edges=seams,seam_length=length)
    return result


def lift_all(uv,pins):
    out=np.empty_like(uv); impossible=[]
    for i,t in enumerate(uv):
        locked=[k for k in range(3) if (i,k) in pins]
        result=lift_face(t,locked)
        if result is None: impossible.append(i); out[i]=t
        else: out[i]=result
    shift=out[:,:,0]-uv[:,:,0]
    if not np.allclose(shift,np.round(shift),atol=1e-10,rtol=0) or not np.array_equal(out[:,:,1],uv[:,:,1]): raise AssertionError('lift invariant')
    return out,impossible


def audit_row(row):
    uv=np.asarray(row['bridge_corner_uvs'],float)
    pins,wide=boundary_pins(row)
    baseline=metrics(row,uv)
    free,free_impossible=lift_all(uv,{})
    diagnostic=metrics(row,free)
    free_gap=max(float(np.max(np.abs(free[i,k]-point))) for (i,k),point in pins.items())
    initial_gap=max(float(np.max(np.abs(uv[i,k]-point))) for (i,k),point in pins.items())
    if initial_gap>TOL:
        return dict(case=row['case'],arm=row['arm'],uv_mode=row['uv_mode'],baseline=baseline,free_periodic=diagnostic,free_impossible_faces=len(free_impossible),free_max_boundary_gap=free_gap,strict=None,strict_impossible_faces=None,strict_max_boundary_gap=None,wide_source_edges=wide,decision='rejected_input_boundary_already_mismatched')
    locked,locked_impossible=lift_all(uv,pins)
    locked_gap=max(float(np.max(np.abs(locked[i,k]-point))) for (i,k),point in pins.items())
    if locked_gap>TOL: raise AssertionError('strict boundary mutation')
    strict_metrics=metrics(row,locked)
    if wide and not locked_impossible: raise AssertionError('wide source edge cannot have short-span lift')
    if locked_impossible:
        decision='rejected_short_span_incompatible_with_exact_boundary' if wide else 'rejected_no_local_short_lift'
    elif strict_metrics['degenerate_uv'] or strict_metrics['mixed_winding_islands'] or strict_metrics['overlap_pairs']:
        decision='rejected_remaining_uv_faults'
    else:
        decision='diagnostic_candidate_only'
    return dict(case=row['case'],arm=row['arm'],uv_mode=row['uv_mode'],baseline=baseline,free_periodic=diagnostic,free_impossible_faces=len(free_impossible),free_max_boundary_gap=free_gap,strict= strict_metrics,strict_impossible_faces=len(locked_impossible),strict_max_boundary_gap=locked_gap,wide_source_edges=wide,decision=decision)


def controls():
    clean=np.array([[.1,0],[.3,0],[.1,1]])
    assert np.array_equal(lift_face(clean),clean)
    wrapped=np.array([[.95,0],[.05,0],[.95,1]])
    got=lift_face(wrapped,(0,2)); assert np.ptp(got[:,0])<.101 and got[0,0]==.95 and got[2,0]==.95 and abs(got[1,0]-1.05)<1e-12
    assert lift_face(wrapped,(0,1)) is None
    assert lift_face(np.array([[0,0],[.333,0],[.667,1]])) is None
    already=np.array([[.95,0],[1.05,0],[.95,1]])
    assert np.array_equal(lift_face(already,(0,1,2)),already)
    assert np.array_equal(lift_face(wrapped+np.array([3,0]),(0,2)),got+np.array([3,0]))
    # Actual planar fold due solely to wrapping; a boundary-compatible lift fixes it.
    verts=[[0,0,0],[1,0,0],[0,1,0],[1,1,0]]; faces=[[0,1,2],[1,3,2]]
    folded=np.array([[[.9,0],[.1,0],[.9,1]],[[.1,0],[.1,1],[.9,1]]])
    target=folded.copy(); target[:,:,0]=np.where(target[:,:,0]<.5,target[:,:,0]+1,target[:,:,0])
    assert uv_audit(verts,faces,target)['overlap_pairs']==0
    assert uv_audit(verts,faces,target)['positive_uv']==2
    assert uv_audit(verts,faces,folded)['negative_uv']==2
    return ['clean','repairable_one_period','pinned_wide_edge_rejection','no_short_arc','already_lifted_pins','integer_translation','planar_orientation_control']


def audit(raw):
    if raw.get('cycle') not in ('R12','R13') or not raw.get('synthetic_only') or raw.get('approved') or len(raw['cases'])!=24: raise ValueError('invalid historical source')
    if len({(r['case'],r['arm']) for r in raw['cases']})!=24: raise ValueError('duplicate outputs')
    if any(r['status']!='generated' for r in raw['cases']): raise ValueError('missing generated data')
    return [audit_row(r) for r in raw['cases']]


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    inp=Path(a.input); raw=json.loads(inp.read_text()); c=controls(); rows=audit(raw)
    with Path(a.output).open('x') as out: json.dump(dict(cycle='R15',approved=False,diagnostic_only=True,source_cycle=raw['cycle'],input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),controls_passed=c,rows=rows),out,indent=2,allow_nan=False)
    print('R15_AUDIT',raw['cycle'],len(rows),len(c))
