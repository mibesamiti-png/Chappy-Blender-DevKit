"""Applied04: synthetic visual flashlight. Millimetres, 24 sides.
Owner authorized autonomous target selection. No functional/print certification.
Frozen base budget <=600 vertices, evaluated triangles <=2500, three closed
oriented parts, native roundtrip and independent CGAL self-intersection gate.
Decorative switch intersects body intentionally. Lens seating is visual only.
"""
import math
N=24
PROFILE=[(-60,10.8,'metal'),(-59,12.0,'metal'),(-53,12.0,'dark'),(-52,12.6,'dark'),(-44,12.6,'grip'),(-43,11.8,'grip'),(-40,11.8,'grip'),(-39,12.6,'grip'),(-31,12.6,'grip'),(-30,11.8,'grip'),(-27,11.8,'grip'),(-26,12.6,'grip'),(-18,12.6,'dark'),(-17,12.5,'dark'),(25,12.5,'dark'),(33,17.5,'metal'),(36,18.5,'dark'),(55,18.5,'dark'),(59,18.5,'metal'),(60,17.5,'metal'),(60,15.5,'metal'),(56,15.5,'dark')]
COLORS={'dark':(43,52,58,255),'metal':(130,147,154,255),'grip':(27,34,39,255),'lens':(122,185,202,255),'switch':(225,120,44,255)}
def ring_mesh(profile,n=N):
    v=[(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for z,r,_ in profile for i in range(n)]
    f=[tuple(reversed(range(n)))];m=[profile[0][2]]
    for j in range(len(profile)-1):
        for i in range(n):
            k=(i+1)%n;f.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i));m.append(profile[j][2])
    f.append(tuple(range((len(profile)-1)*n,len(profile)*n)));m.append(profile[-1][2])
    return v,f,m
def switch_mesh():
    yz=[(-2.2,8),(2.2,8),(3.2,9),(3.2,18),(2.2,19),(-2.2,19),(-3.2,18),(-3.2,9)]
    v=[(x,y,z) for x in (11.8,14.2) for y,z in yz];n=len(yz)
    f=[tuple(reversed(range(n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+[tuple(range(n,2*n))]
    return v,f,['switch']*len(f)
def parts():
    return {'Body':ring_mesh(PROFILE),'Lens':ring_mesh([(56.3,15.25,'lens'),(58,15.25,'lens')]),'Switch':switch_mesh()}
def triangulate(f):
    return [(f[0],f[i],f[i+1]) for i in range(1,len(f)-1)]
