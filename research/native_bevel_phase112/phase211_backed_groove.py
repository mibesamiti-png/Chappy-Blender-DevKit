"""Phase211-C2: one connected solid for both groove walls and backplate.
Mirror backing away from each slider. Same radial profiles as C1.
Ideal shaft bearing and coupling remain, no material-strength certification.
"""
import numpy as np
from phase206_hybrid_machine import mesh,closed,polygon_area,BORE,key_check
from phase211_groove_profile import wall
from phase210_inverse_cam import profile
FLOOR=.16
BACK=.36
TOP=.12
def backed_mesh(kind,base,duty,rot,back_side):
    outer,inner,q=wall(kind,base,duty)
    assert q['passed']
    outer=outer@rot.T;inner=inner@rot.T
    core=profile(kind,base,duty=duty)@rot.T
    bore=core*BORE/np.max(np.abs(core),axis=1)[:,None]
    rings=[(bore,-BACK),(outer,-BACK),(outer,TOP),(inner,TOP),
           (inner,-FLOOR),(core,-FLOOR),(core,TOP),(bore,TOP)]
    # Native cross-section is backed on negative Z. Reverse winding when mirrored.
    sign=-back_side
    n=len(core)
    v=[(float(x),float(y),sign*z) for a,z in rings for x,y in a]
    f=[]
    for r in range(len(rings)):
        s=(r+1)%len(rings)
        for i in range(n):
            j=(i+1)%n
            face=(r*n+i,r*n+j,s*n+j,s*n+i)
            f.append(face if sign>0 else face[::-1])
    area=lambda a:polygon_area([tuple(v) for v in a])
    expected=(area(outer)-area(bore))*(BACK-FLOOR)+(area(core)-area(bore)+area(outer)-area(inner))*(TOP+FLOOR)
    m=mesh(kind+' one-piece backed groove',v,f)
    a=closed(m,1,expected)
    a['key']=key_check(m);a['passed']=a['passed'] and a['key']
    return m,a,core,inner
