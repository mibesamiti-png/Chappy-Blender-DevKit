"""Research-only shape deviation from original sharp section, not a quality or safety gate."""
import json, math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def distance_points_polyline(P,Q):
    P=np.asarray(P,float);Q=np.asarray(Q,float)
    E=np.diff(Q,axis=0);l2=(E*E).sum(1);good=l2>1e-24
    E=E[good];A=Q[:-1][good];l2=l2[good]
    if not len(E):raise ValueError('zero_length_reference')
    D=P[:,None,:]-A[None,:,:];t=np.clip((D*E).sum(-1)/l2,0,1)
    return np.linalg.norm(D-t[...,None]*E,axis=-1).min(1)

def sampled(P,n):
    P=np.asarray(P,float);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(P,axis=0),axis=1))]
    if s[-1]<=1e-12:raise ValueError('zero_length')
    u=np.linspace(0,s[-1],n)
    return np.concatenate([P,np.stack([np.interp(u,s,P[:,k]) for k in range(P.shape[1])],axis=1)])

def measure(sharp,candidate,n=513):
    A=np.asarray(sharp,float);B=np.asarray(candidate,float)
    if not np.all(np.isfinite(A)) or not np.all(np.isfinite(B)):raise ValueError('nonfinite')
    length=np.linalg.norm(np.diff(A,axis=0),axis=1).sum()
    if length<=1e-12:raise ValueError('zero_length')
    if max(np.linalg.norm(A[0]-B[0]),np.linalg.norm(A[-1]-B[-1]))>length*1e-5:raise ValueError('anchor_mismatch')
    a=distance_points_polyline(sampled(A,n),B).max();b=distance_points_polyline(sampled(B,n),A).max()
    # Sampling-based Hausdorff estimate, normalized by common sharp path length.
    # Continuous max lies within estimate + max segment sampling gap/2 (distance is 1-Lipschitz).
    lb=np.linalg.norm(np.diff(B,axis=0),axis=1).sum()
    return dict(sharp_to_candidate=float(a/length),candidate_to_sharp=float(b/length),symmetric=float(max(a,b)/length),error_bound=float(max(length,lb)/(2*(n-1)*length)),length_ratio=float(lb/length))

def controls():
    A=np.array([[0.,1,0],[0,0,0],[1,0,0]])
    cases=[]
    z=measure(A,A);assert z['symmetric']<1e-12;cases.append('identity')
    B=A[[0,2]];r=measure(A,B);assert abs(r['symmetric']-math.sqrt(.5)/2)<1e-9;cases.append('chamfer_known')
    assert abs(measure(A*9+13,B*9+13)['symmetric']-r['symmetric'])<1e-9;cases.append('scale_translation')
    t=np.linspace(0,np.pi/2,129);C=np.c_[1-np.cos(t),1-np.sin(t),np.zeros_like(t)]
    q=measure(A,C);assert abs(q['symmetric']-(math.sqrt(2)-1)/2)<1e-5;cases.append('quarter_circle')
    assert abs(measure(A[::-1],C[::-1])['symmetric']-q['symmetric'])<1e-9;cases.append('reversed')
    for k,X,Y in [('wrong_anchor',A,B+1),('zero_ref',A*0,B),('nonfinite',A,B*np.nan)]:
        try:measure(X,Y)
        except ValueError:cases.append(k)
        else:raise AssertionError(k)
    return cases

def main():
    cc=controls();data=json.loads((ROOT/'phase120_native_preflight.json').read_text());rows=[]
    for row in data['rows']:
        sharp=row['sharp']['sections'];custom=row['custom']['sections'];assert len(sharp)==len(custom)==row['sections']
        rec=[dict(section=a['section'],**measure(a['points'],b['points'])) for a,b in zip(sharp,custom) if a['section']==b['section'] and 'error' not in a and 'error' not in b]
        assert len(rec)==row['sections']
        v=np.array([s['symmetric'] for s in rec]);rows.append(dict(name=row['name'],sections=rec,max_turn=row['custom']['max_turn'],min_deviation=float(v.min()),max_deviation=float(v.max()),median_deviation=float(np.median(v)),max_error_bound=max(s['error_bound'] for s in rec)))
    out=dict(approved=False,native_executed=False,controls=cc,rows=rows);(ROOT/'phase123_section_extent.json').write_text(json.dumps(out,indent=2,allow_nan=False));print('controls',len(cc),'sections',sum(len(r['sections']) for r in rows));print('\n'.join(f"{r['name']:16s} {r['max_turn']:6.2f} {100*r['min_deviation']:6.2f} {100*r['max_deviation']:6.2f}" for r in rows));print('bound',max(r['max_error_bound'] for r in rows))
if __name__=='__main__':main()
