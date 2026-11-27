"""Phase212-J: fixed four-slot Geneva solid geometry, sampled audit.
Wheel slots are rounded-end open cuts; dwell recesses are circular.
Driver has a sector relief and a central hub. Lock coverage is measured,
not assumed continuous. No dynamic contact or manufacturing validation.
"""
import math
from phase212_geneva import Geneva
from phase212_radial_cam import _edges,_nearest_and_inside

def rotate(p,a):
    x,y=p;c=math.cos(a);s=math.sin(a)
    return x*c-y*s,x*s+y*c

def profiles(g,relief_degrees=35):
    if g.slots!=4 or g.center_distance!=10 or g.phase_offset!=0 or g.pin_radius!=.3 or g.clearance!=.05:
        raise ValueError("fixed four-slot fixture only")
    if relief_degrees not in (25,30,35,40,45,50,55,60,65,70,75,80,90):
        raise ValueError('predeclared relief angle required')
    C=g.center_distance;R=7.4;L=3.45;D=3.4;w=g.pin_radius+g.clearance
    inner=C-g.crank_radius
    ds=math.asin(w/R)
    dr=math.acos((R*R+C*C-L*L)/(2*R*C))
    x=R*math.cos(dr);y=R*math.sin(dr)
    gamma=math.atan2(y,C-x)
    wheel=[]
    # Alternate dwell recesses and open slots, CCW outer boundary.
    features=[]
    for j in range(4):
        a=j*math.pi/2
        recess=[(C+L*math.cos(-math.pi+gamma-2*gamma*i/64),
                 L*math.sin(-math.pi+gamma-2*gamma*i/64)) for i in range(65)]
        features.append((a,dr,recess))
        a+=math.pi/4
        slot=[(R*math.cos(ds),-w)]+[(inner+w*math.cos(-math.pi/2-math.pi*i/32),
             w*math.sin(-math.pi/2-math.pi*i/32)) for i in range(33)]+[(R*math.cos(ds),w)]
        features.append((a,ds,slot))
    for j,(a,d,points) in enumerate(features):
        wheel.extend(rotate(p,a) for p in points)
        b,e,_=features[(j+1)%len(features)]
        if j==len(features)-1:b+=math.tau
        for i in range(1,32):
            t=a+d+(b-e-a-d)*i/32
            wheel.append((R*math.cos(t),R*math.sin(t)))
    # Driver relief centered on local -X, where pin points at phase .5.
    # Radius transitions happen outside the conservative swept overlap cone.
    driver=[]
    for i in range(360):
        a=math.tau*i/360
        d=abs(math.atan2(math.sin(a-math.pi),math.cos(a-math.pi)))
        q=max(0.,min(1.,(d-math.radians(relief_degrees))/math.radians(5)))
        r=1.2+(D-1.2)*q
        driver.append((r*math.cos(a),r*math.sin(a)))
    return tuple(wheel),tuple(driver),dict(wheel_radius=R,locking_radius=D,recess_radius=L,slot_half_width=w,relief_degrees=relief_degrees)

def pin_clearance(g,wheel,u):
    p=rotate(g.pin(u),-g.sample(u)[0])
    d,inside=_nearest_and_inside(p,_edges(wheel))
    return (-d if inside else d)-g.pin_radius
