# Applied03 — rear-offset pivot screen (preliminary, not a mechanical design)

Parent evidence: Applied02B, HEAD de1bbf79dec908e7190b7cb585ff5e83e34906c8. Owner requested continuation. Scope: synthetic only, no change to prior model, no product approval. This exploratory screen uses a different metric from Applied02's actual evaluated mesh contact diagnostic.

## Hypothesis
Move each hinge pivot and its moving temple rearward along +Y, without altering the temple's straight 85 mm interval. This may separate the rim from the temple, but will not necessarily resolve inter-temple collisions. The fixed pin/endpiece would need redesign if a candidate is chosen; this screen does not model those connections.

## Executed exploratory calculation
84 discrete angle states, exactly the union of (t,0),(0,t),(85,t),(t,85),(t,t), t=0..85 step 5 degrees. Independent left/right rear offsets 0..20 mm step 2 (121 combinations). Units mm. Source: applied02/region_run.py PROFILE and blender_run.py contour, pivot. For each rim quad of each 32-segment ellipse, form an axis-aligned bounding box expanded by 3.2 mm. For each consecutive pair of temple profile rings, use axis-aligned rectangular cross sections (NOT the actual tangent-aligned cross sections), transform their eight corners using the existing rigid Z rotation, and expand the resulting box by 3 mm on all axes. Count a pose if any rim/temple or temple/temple box pair overlaps. Deliberately coarse exploratory proxy, not a certified conservative bound for Blender evaluated meshes.

Actual executed JavaScript results:
| Rear offset R/L (mm) | Poses with any proxy overlap | R/rim | L/rim | R/L |
|---|---:|---:|---:|---:|
| 0/0 | 84 | 84 | 84 | 44 |
| 2/2 | 84 | 84 | 84 | 44 |
| 4/4 | 77 | 60 | 60 | 44 |
| 6/6 | 44 | 0 | 0 | 44 |
| 8/8 through 20/20 | 44 | 0 | 0 | 44 |
| 6/20 or 20/6 | 42 | 0 | 0 | 42 |

Base proxy flags 84 poses versus 48 measured actual contact poses in Applied02B, so proxy counts are NOT physical collision counts or evidence of improvement in actual meshes. The smallest symmetric sampled offset with no rim box overlap is 6 mm. It is a candidate to test, not an optimized design. Asymmetric 14 mm additional shift only reduces proxy by two poses and is not preferred on this evidence.

## Reproduction (standalone JS; exploratory calculation, not CI)
```js
const profile=[[0,0,0,1.4,1.65],[85,0,0,1.4,1.65],[91,-.5,-.4,1.6,1.85],[98,-2,-2,2.1,2.25],[110,-4.5,-7,2.2,2.3],[124,-7,-16,2.1,2.2],[132,-9,-22,1.7,1.8]];
const states=[...new Map(Array.from({length:18},(_,i)=>5*i).flatMap(t=>[[t,0],[0,t],[85,t],[t,85],[t,t]]).map(x=>[x.join(","),x])).values()];
const box=(p,pad=0)=>[0,1,2].map(i=>[Math.min(...p.map(v=>v[i]))-pad,Math.max(...p.map(v=>v[i]))+pad]);
const overlap=(a,b)=>a.every(([lo,hi],i)=>lo<=b[i][1]&&hi>=b[i][0]);
const rim=[];for(const s of [-1,1])for(let i=0;i<32;i++){let pts=[];for(const j of [i,i+1])for(const [rx,rz] of [[26.5,17.5],[30,21]]){let t=j*Math.PI/16,x=34.5+rx*Math.cos(t);pts.push([s*x,3*(x/70)**2,rz*Math.sin(t)])}rim.push(box(pts,3.2))}
function arms(s,a,dy){const c=Math.cos(a*Math.PI/180),q=Math.sin(a*Math.PI/180)*s;const rings=profile.map(([y,x,z,w,h])=>[[-w,-h],[-w,h],[w,-h],[w,h]].map(([u,v])=>[s*69+c*(s*x+u)-q*y,5+dy+q*(s*x+u)+c*y,3+z+v]));return rings.slice(0,-1).map((p,i)=>box([...p,...rings[i+1]],3.0))}
const cache=new Map();for(let d=0;d<=20;d+=2)for(let a=0;a<=85;a+=5)for(const s of [-1,1]){const b=arms(s,a,d);cache.set([s,a,d].join(),{b,r:b.some(x=>rim.some(y=>overlap(x,y)))})}
let rows=[];for(let dr=0;dr<=20;dr+=2)for(let dl=0;dl<=20;dl+=2){let n=0,rr=0,lr=0,tt=0;for(const [r,l] of states){let x=cache.get([1,r,dr].join()),y=cache.get([-1,l,dl].join());let z=x.b.some(a=>y.b.some(b=>overlap(a,b)));rr+=x.r;lr+=y.r;tt+=z;n+=x.r||y.r||z}rows.push({dr,dl,n,rr,lr,tt})}
console.log(JSON.stringify({states:states.length,base:rows[0],best:rows.sort((a,b)=>a.n-b.n||(a.dr+a.dl)-(b.dr+b.dl)).slice(0,12),symmetric:rows.filter(x=>x.dr===x.dl).sort((a,b)=>a.dr-b.dr)},null,2));
```

## Next actual-mesh test
Use frozen B evaluated arrays or native Blender, revise pin/sleeve/endpiece and compare symmetric +6 mm with unmodified B using identical 84 poses and nonexempt pairs. Keep an unchanged reference and separate new hinge interface tests, including solid containment and positive clearance, plus finer/adaptive sampling before any continuous claim. Do not claim ergonomic fit; moving both temples back changes open fit. If rear offset alone is insufficient, compare depth stagger or complementary curved tip profile against the same baseline. Aesthetic and internal core remain open. No old gate modified, no CI run of this screen, approved=false.
