# Topology Intelligence — phases 32–34: native composition and boundary-corner obstruction

## Verified native evidence
- Phase32 initial native job 139057379295 / run 45571014964: Blender 4.4.3 (pinned archive verified), 144/144 valid raw Grid Fill outputs, 48 same-budget (25 vertices, 16 quads), 0/48 joint gate. Coons reference has interior target information; raw native only receives boundary. Not an equal-information comparison.
- Phase33 initial job 139059425662 / run 45571628278: projection 48/48 valid, smoothing arms 0/192 valid (190 boundary-changed, 2 Unicode decode exceptions), overall job failed. Do not discard initial failure evidence.
- Corrected source HEAD 424c244e61056f87f0a447fc442b4263c4edb208, job 139062148457 / run 45572443324: native benchmark success, all 240 valid, no exceptions, shape-only gate 182/240, joint gate 0/240. Retain stable vertex-group name across modifier application; capture and explicitly restore pinned boundary after Smooth; reported best-candidate pre-restore drift 0. Root cause of earlier exceptions not independently isolated.
- Shape gate counts (each 48): project 29, smooth1/project 32, smooth3/project 39, smooth6/project 43, smooth1/project repeated 3 times 39. Best P95 after smooth6/project: .0100064976, .0137966860, .0080043240; Coons references .0108046183, .0142800816, .0083521392. Different guide representation and selection on known cases; not general superiority. Best angle across five native arms in each case 10.1301046, 8.5223773, 10.1252472 degrees. Raw/evaluation artifact 15003216189 (retention 14 days). Logs inspected; artifact contents not independently downloaded. Other CI not asserted green.

## Phase34 mathematical diagnostic (executed in JS)
The frozen evaluator tests both diagonals of every quad and takes the smallest triangle angle. A quad at a rectangular grid corner contains consecutive boundary vertices B[i-1], B[i], B[i+1]. One triangulation includes exactly that fixed triangle, so the patch's worst angle cannot exceed its smallest angle, regardless of interior coordinates or smoothing. For four distinct corner vertices, the upper bound is the minimum of their fixed triangle angles. This is a property of the current evaluator and topology, not a claim about Blender's actual tessellation or all quad layouts.

For a 16-edge rectangular grid with side lengths s and 8-s, enumerate offsets 0..15 and s=1..7 (112 settings per shape). Also enumerate all C(16,4)=1820 distinct four-corner subsets, including ones not realizable by a rectangular grid. No geometry optimization performed. Using original analytic double-precision Phase32 boundary formula gives:

| Case | Best 4x4 upper bound (deg) | Best any rectangular grid bound | Best unrestricted four-corner bound | Measured native best (float32) |
|---|---:|---:|---:|---:|
| 0 | 10.130104898 | 12.761634070 | 12.761634070 | 10.130104594 |
| 1 | 8.522373592 | 14.989220013 | 14.989220013 | 8.522377297 |
| 2 | 10.125247249 | 12.762436322 | 12.762436322 | 10.125247238 |

All four-corner bounds below frozen 15 degree floor. The best 4x4 theoretical values agree with actual best native results to 4e-6 degrees. Thus more interior smoothing, parameter search or relocating four corners alone cannot satisfy this specific gate. The grid corner obstruction does not apply to topologies without four such corners. No threshold relaxation.

Reproduction (pure JS, independently executable):
```js
const cases=[[.19,.15,.12,.02],[.23,.12,.16,.045],[.15,.19,.09,-.035]];
const angle=(a,b,c)=>{const u=a.map((x,i)=>x-b[i]),v=c.map((x,i)=>x-b[i]);return Math.acos(Math.max(-1,Math.min(1,u.reduce((s,x,i)=>s+x*v[i],0)/Math.hypot(...u)/Math.hypot(...v))))*180/Math.PI};
for(const [w,h,b,t] of cases){
 const V=Array.from({length:16},(_,i)=>{const a=i*Math.PI/8-3*Math.PI/4,x=Math.cos(a),y=Math.sin(a);return [w*x,h*y,b*(1-.60*x*x-.85*y*y)+t*x*y+.04*x]});
 const q=V.map((p,i)=>{const a=V[(i+15)%16],c=V[(i+1)%16];return Math.min(angle(a,p,c),angle(p,a,c),angle(a,c,p))});
 let fixed=0,any=0,free=0;
 for(let s=1;s<8;s++)for(let o=0;o<16;o++){const cap=Math.min(...[o,(o+s)%16,(o+8)%16,(o+8+s)%16].map(i=>q[i]));any=Math.max(any,cap);if(s===4)fixed=Math.max(fixed,cap)}
 for(let a=0;a<16;a++)for(let b=a+1;b<16;b++)for(let c=b+1;c<16;c++)for(let d=c+1;d<16;d++)free=Math.max(free,Math.min(q[a],q[b],q[c],q[d]));
 console.log({fixed,any,free});
}
```

## Next bounded experiment
Try standard operators to create an interior collar (one quad per original boundary edge via extrusion or bridge), then Grid Fill the interior loop and Shrinkwrap the non-boundary vertices. Keep all original boundary coordinates fixed and the 15-degree floor. Distinguish original 25/16 budget from collar 41/32; additional density is a tradeoff, not a free improvement. A same-budget alternate topology is a separate research hypothesis. No collar generated/tested yet. No anatomical shoulder, general 3D, real asset, native subdivision, rigging, or adoption claim. Research only, approved=false; no private model assets, main, ABCD or DIL changes.
