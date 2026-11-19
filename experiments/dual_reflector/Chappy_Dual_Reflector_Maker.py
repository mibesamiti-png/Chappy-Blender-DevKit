# SPDX-License-Identifier: MIT
# Chappy Dual Reflector Maker — manual voice acoustic reflector prototype
# One-file Blender addon for Blender 4.3+ (intended for 4.4/5.x)
bl_info = {
    "name": "Chappy Dual Reflector Maker",
    "author": "OpenAI / Chappy",
    "version": (1, 0, 1),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Chappy > Dual Reflector",
    "description": "Parametric hand-voice two-reflector megaphone: ellipsoid/paraboloid, ray preview, STL exports",
    "category": "Add Mesh",
}

import bpy
import math
import os
import re
import struct
from mathutils import Vector
from bpy.props import (
    BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty,
    StringProperty,
)

MAIN_COLLECTION = "Chappy_DualReflector_R1"
REFERENCE_COLLECTION = "Chappy_DualReflector_Reference"
MM = 0.001
TAU = 2.0 * math.pi


def mm(v):
    return float(v) * MM


def _unit2(x, z):
    length = math.hypot(x, z)
    return (x / length, z / length) if length > 1.0e-9 else (0.0, 1.0)


def _reflect2(direction, normal):
    nx, nz = _unit2(*normal)
    vx, vz = direction
    dot = vx * nx + vz * nz
    return (vx - 2.0 * dot * nx, vz - 2.0 * dot * nz)


def _geom(p):
    """Geometry and validation in millimetres. All dimensions are nominal research values."""
    D = float(p.diameter)
    length = float(p.length)
    wall = float(p.wall)
    r_out = D / 2.0
    r_primary = r_out - wall
    r_mouth = float(p.mouth_d) / 2.0
    r_exit = float(p.exit_d) / 2.0
    r_secondary = float(p.secondary_d) / 2.0
    secondary_depth = float(p.secondary_depth)
    mode = p.mode

    if r_primary <= max(r_exit + 4.0, r_mouth + 5.0):
        raise ValueError("外径を大きくするか、口径・出口径を小さくしてください")
    if r_exit < r_secondary + 1.0:
        raise ValueError("出口径は小反射板の直径より2mm以上大きくしてください")
    if length < D * 0.55:
        raise ValueError("本体全長が短すぎます。直径の55%以上にしてください")
    if r_mouth + wall >= r_primary:
        raise ValueError("口径が大きすぎます")
    if secondary_depth >= r_secondary * 0.8:
        raise ValueError("小反射板の深さが大きすぎます")

    sec_f = r_secondary * r_secondary / (4.0 * secondary_depth)
    if mode == 'ELLIPSE':
        mouth_z = 0.0
        common_focus = float(p.focus_z)
        if not 10.0 < common_focus < length - 8.0:
            raise ValueError("共通焦点は入口より10mm以上前、前端より8mm以上後ろにしてください")
        center = (mouth_z + common_focus) * 0.5
        a = length - center
        c = (common_focus - mouth_z) * 0.5
        b2 = a*a - c*c
        if b2 <= r_primary*r_primary + 1.0:
            raise ValueError("楕円面の幅が足りません。全長または焦点位置を調整してください")
        b = math.sqrt(b2)
        def primary_z(r):
            return center + a * math.sqrt(max(0.0, 1.0 - r*r/(b*b)))
        def primary_normal(x, z):
            return (x/(b*b), (z-center)/(a*a))
        p_f = None
    else:
        primary_depth = float(p.primary_depth)
        if primary_depth <= 0.5:
            raise ValueError("大反射板の深さが浅すぎます")
        p_f = r_primary*r_primary/(4.0*primary_depth)
        common_focus = length - p_f
        if common_focus < 12.0 or common_focus > length-5.0:
            raise ValueError("大反射板の焦点が本体内に収まるように深さを調整してください")
        def primary_z(r):
            return length - r*r/(4.0*p_f)
        def primary_normal(x, z):
            return (x/(2.0*p_f), 1.0)
        center = a = b = None

    z_rim = primary_z(r_primary)
    sec_vertex = common_focus - sec_f + float(p.secondary_offset)
    sec_rim_z = sec_vertex + secondary_depth
    if sec_vertex < 12.0 or sec_rim_z > z_rim - 4.0:
        raise ValueError("小反射板が入口／外側の反射面に近すぎます。位置・深さを調整してください")
    inner_horn_at_support = r_mouth + (r_primary-r_mouth) * (sec_rim_z/z_rim)
    if inner_horn_at_support <= r_secondary + 5.0:
        raise ValueError("小反射板と本体の間に支持アームを設置できません")

    return {
        'diameter': D, 'length': length, 'wall': wall,
        'r_out': r_out, 'r_primary': r_primary, 'r_mouth': r_mouth,
        'r_exit': r_exit, 'r_secondary': r_secondary,
        'z_rim': z_rim, 'primary_z': primary_z,
        'primary_normal': primary_normal, 'common_focus': common_focus,
        'secondary_f': sec_f, 'secondary_vertex': sec_vertex,
        'secondary_depth': secondary_depth, 'secondary_rim_z': sec_rim_z,
        'support_r': inner_horn_at_support, 'mode': mode,
        'ellipse_center': center, 'ellipse_a': a, 'ellipse_b': b,
        'primary_f': p_f,
    }


def _revolve_profile(profile, sides=128):
    """Watertight surface of revolution of closed 2D (r,z) polygon, mm units."""
    profile = list(profile)
    if len(profile) < 3:
        raise ValueError("Profile needs >=3 points")
    # Clockwise profile in (r,z) convention gives outward-facing facets.
    signed_area2 = sum(
        profile[i][0]*profile[(i+1)%len(profile)][1]
        - profile[(i+1)%len(profile)][0]*profile[i][1]
        for i in range(len(profile))
    )
    if signed_area2 > 0.0:
        profile.reverse()
    vertices = []
    rings = []
    for r,z in profile:
        if r < -1.0e-7:
            raise ValueError("Negative radial coordinate")
        if abs(r) < 1.0e-7:
            idx = len(vertices)
            vertices.append((0.0,0.0,z))
            rings.append([idx]*sides)
        else:
            ring = []
            for j in range(sides):
                angle = TAU*j/sides
                ring.append(len(vertices))
                vertices.append((r*math.cos(angle),r*math.sin(angle),z))
            rings.append(ring)
    faces = []
    for i in range(len(profile)):
        j2 = (i+1)%len(profile)
        a = rings[i]
        b = rings[j2]
        a_axis = profile[i][0] < 1e-7
        b_axis = profile[j2][0] < 1e-7
        if a_axis and b_axis:
            continue
        for j in range(sides):
            nxt = (j+1)%sides
            if a_axis:
                faces.append((a[j],b[j],b[nxt]))
            elif b_axis:
                faces.append((a[j],b[j],a[nxt]))
            else:
                faces.append((a[j],b[j],b[nxt],a[nxt]))
    return vertices, faces


def _horn_geom(g, sides):
    rin = g['r_mouth']
    rout = g['r_primary']
    zmax = g['z_rim']
    wall = g['wall']
    # Smooth funnel with a continuous inner and outer surface; open at both ends.
    profile = []
    for i in range(31):
        t = i/30.0
        profile.append((rin+(rout-rin)*t, zmax*t))
    profile.extend([
        (g['r_out'], zmax),
        (rin+wall, 0.0),
    ])
    return _revolve_profile(profile, sides)


def _primary_geom(g, sides):
    r0 = g['r_exit']
    r1 = g['r_primary']
    wall = g['wall']
    z_fn = g['primary_z']
    profile = []
    for i in range(81):
        r = r0+(r1-r0)*(i/80.0)
        profile.append((r,z_fn(r)))
    # Flat 2-mm rim gluing/seating against the main horn rim.
    profile += [(g['r_out'],g['z_rim']), (g['r_out'],g['z_rim']+wall)]
    for i in range(80,-1,-1):
        r = r0+(r1-r0)*(i/80.0)
        profile.append((r,z_fn(r)+wall))
    return _revolve_profile(profile, sides)


def _secondary_geom(g, sides):
    radius = g['r_secondary']
    depth = g['secondary_depth']
    vertex = g['secondary_vertex']
    thickness = min(g['wall'], 1.6)
    profile = []
    for i in range(33):
        r = radius*i/32.0
        profile.append((r,vertex+depth*(r/radius)**2))
    for i in range(32,-1,-1):
        r = radius*i/32.0
        profile.append((r,vertex+depth*(r/radius)**2-thickness))
    return _revolve_profile(profile, sides)


def _reference_geom(g, sides):
    rin = g['r_mouth']
    rout = g['r_primary']
    end = g['length']
    wall = g['wall']
    profile = [(rin+(rout-rin)*i/30.0, end*i/30.0) for i in range(31)]
    profile += [(g['r_out'],end),(rin+wall,0.0)]
    return _revolve_profile(profile, sides)


def _rod_geom(start, end, radius=1.5, sides=12):
    """Single round support rod, independent watertight part."""
    a = Vector(start)
    b = Vector(end)
    direct = b-a
    if direct.length < .001:
        raise ValueError("Support length too short")
    unit = direct.normalized()
    basis = unit.cross(Vector((0,0,1)))
    if basis.length < 0.01:
        basis = unit.cross(Vector((0,1,0)))
    basis.normalize()
    ortho = unit.cross(basis).normalized()
    verts=[]
    for pos in (a,b):
        for i in range(sides):
            theta=TAU*i/sides
            q=pos + radius*(basis*math.cos(theta)+ortho*math.sin(theta))
            verts.append(tuple(q))
    faces=[]
    for i in range(sides):
        j=(i+1)%sides
        faces.append((i,j,sides+j,sides+i))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(sides+i for i in range(sides)))
    return verts,faces


def _secondary_hit(point, direction, g):
    x,z=point
    dx,dz=direction
    sf=g['secondary_f']
    sv=g['secondary_vertex']
    A = dx*dx/(4.0*sf)
    B = x*dx/(2.0*sf)-dz
    C = x*x/(4.0*sf)+sv-z
    if abs(A) < 1e-12:
        roots = [-C/B] if abs(B)>1e-12 else []
    else:
        delta = B*B-4.0*A*C
        roots = [] if delta < 0 else [(-B-math.sqrt(delta))/(2*A),(-B+math.sqrt(delta))/(2*A)]
    hits=[]
    for t in roots:
        r = x+t*dx
        z_hit = z+t*dz
        if t > 1e-6 and abs(r) <= g['r_secondary']+1e-6:
            hits.append((t,r,z_hit))
    return min(hits) if hits else None


def _ray_path(g, radius, side, source):
    """2D *geometric* ray path, NOT acoustic diffraction or measured response."""
    px=radius*side
    pz=g['primary_z'](radius)
    if source=='MOUTH':
        start=(0.0,0.0)
        direction=_unit2(px,pz)
    else:
        start=(px,0.0)
        direction=(0.0,1.0)
    incoming=[start,(px,pz)]
    # The secondary reflector can shadow a diverging voice ray *before*
    # that ray reaches the large reflector. Mark it explicitly.
    first_hit=_secondary_hit(start,direction,g)
    if first_hit is not None:
        t_first,x_first,z_first=first_hit
        dist_to_primary=math.hypot(px-start[0],pz-start[1])
        if t_first < dist_to_primary-1.0e-5:
            return [start,(x_first,z_first)],'SHADOWED'
    reflected=_reflect2(direction,g['primary_normal'](px,pz))
    hit=_secondary_hit((px,pz),reflected,g)
    if hit is None:
        # visualise a short continuation rather than making up a second reflection
        endpoint=(px+reflected[0]*38.0,pz+reflected[1]*38.0)
        return incoming+[endpoint], 'MISS'
    t,xs,zs=hit
    after=_reflect2(reflected,(-xs/(2.0*g['secondary_f']),1.0))
    exit_z = g['primary_z'](g['r_exit'])
    if after[1] <= 1e-7:
        end=(xs+after[0]*22.0,zs+after[1]*22.0)
        return incoming+[(xs,zs),end],'BLOCKED'
    t_exit=(exit_z-zs)/after[1]
    x_exit=xs+after[0]*t_exit
    if t_exit <= 0 or abs(x_exit)>g['r_exit']:
        end=(xs+after[0]*min(35.0,max(t_exit,5.0)),zs+after[1]*min(35.0,max(t_exit,5.0)))
        return incoming+[(xs,zs),end],'BLOCKED'
    t_end=(g['length']+35.0-zs)/after[1]
    end=(xs+after[0]*t_end,zs+after[1]*t_end)
    return incoming+[(xs,zs),(x_exit,exit_z),end],('ALIGNED' if abs(after[0])<0.09 else 'SPREAD')


def _material(name, color):
    mat=bpy.data.materials.get(name)
    if mat is None:
        mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,1.0)
    return mat


def _assert_replaceable_collection(name):
    """Never delete user content solely because a collection shares our name."""
    c = bpy.data.collections.get(name)
    if c is None:
        return
    if len(c.children):
        raise RuntimeError('同名コレクション内に手動の子コレクションがあります: ' + name)
    if any(not (obj.get('chappy_generated') or obj.get('chappy_ray_preview'))
           for obj in c.objects):
        raise RuntimeError('同名コレクション内に手動のオブジェクトがあります: ' + name)
    # Supports collections created by v1.0.0, which marked each object but not the collection.
    if not c.get('chappy_dual_generated') and len(c.objects) == 0:
        raise RuntimeError('同名の未管理コレクションがあります: ' + name)


def _remove_collection(name):
    _assert_replaceable_collection(name)
    c = bpy.data.collections.get(name)
    if c is None:
        return
    for obj in list(c.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(c)


def _new_collection(name):
    c = bpy.data.collections.new(name)
    c['chappy_dual_generated'] = True
    bpy.context.scene.collection.children.link(c)
    return c


def _mesh_object(name, verts_faces, c, material, props=None):
    verts,faces=verts_faces
    mesh=bpy.data.meshes.new(name+'_Mesh')
    mesh.from_pydata([tuple(mm(v) for v in vertex) for vertex in verts],[],faces)
    mesh.validate(verbose=False)
    mesh.update()
    ob=bpy.data.objects.new(name,mesh)
    c.objects.link(ob)
    ob.data.materials.append(material)
    ob['chappy_generated']=True
    if props:
        for key,val in props.items():
            ob[key]=val
    for polygon in mesh.polygons:
        polygon.use_smooth = len(polygon.vertices)>=4
    return ob


def _ray_curve(name, coords, c, mat):
    cu=bpy.data.curves.new(name,'CURVE')
    cu.dimensions='3D'
    cu.resolution_u=1
    cu.bevel_depth=mm(0.43)
    cu.resolution_u=1
    cu.bevel_resolution=2
    spl=cu.splines.new('POLY')
    spl.points.add(len(coords)-1)
    for i,(x,z) in enumerate(coords):
        spl.points[i].co=(mm(x),0.0,mm(z),1.0)
    ob=bpy.data.objects.new(name,cu)
    c.objects.link(ob)
    ob.data.materials.append(mat)
    ob['chappy_ray_preview']=True
    ob.hide_render=True
    return ob


def _create_rays(p,g,c):
    materials={
        'ALIGNED':_material('Chappy-Ray-Ideal',(0.18,0.92,0.46)),
        'SPREAD':_material('Chappy-Ray-Spreading',(0.98,0.71,0.13)),
        'MISS':_material('Chappy-Ray-Miss',(0.95,0.19,0.15)),
        'BLOCKED':_material('Chappy-Ray-Blocked',(0.85,0.32,0.74)),
        'SHADOWED':_material('Chappy-Ray-Shadowed',(0.63,0.31,0.87)),
    }
    counts={key:0 for key in materials}
    n=int(p.ray_count)
    lo=g['r_exit']+1.0
    hi=g['r_primary']-1.5
    for i in range(n):
        rad=lo+(hi-lo)*(i+0.5)/n
        for side in (-1,1):
            coords,status=_ray_path(g,rad,side,p.ray_source)
            counts[status]+=1
            _ray_curve('Ray_%02d_%s_%s'%(i,'L' if side<0 else 'R',status),coords,c,materials[status])
    return counts


def _generate(p):
    g=_geom(p)
    sides=int(p.resolution)
    # Check both collections before removing either, avoiding partial destruction.
    _assert_replaceable_collection(MAIN_COLLECTION)
    _assert_replaceable_collection(REFERENCE_COLLECTION)
    _remove_collection(MAIN_COLLECTION)
    _remove_collection(REFERENCE_COLLECTION)
    c=_new_collection(MAIN_COLLECTION)
    c['research_note']='Ray diagrams are geometric only. Diffraction/resonance not simulated; no guaranteed directivity.'
    c['design']='ellipsoid + paraboloid' if p.mode=='ELLIPSE' else 'paraboloid + paraboloid'
    c['units']='geometry vertices in metres; export STL in millimetres'
    shellmat=_material('Chappy-Shell-PETG',(0.29,0.60,0.84))
    dishmat=_material('Chappy-Primary',(0.25,0.42,0.63))
    smallmat=_material('Chappy-Secondary',(0.98,0.63,0.24))
    supportmat=_material('Chappy-Struts',(0.45,0.45,0.53))

    horn=_mesh_object('01_Mouth_Horn',_horn_geom(g,sides),c,shellmat)
    _mesh_object('02_Main_Reflector_Central_Exit',_primary_geom(g,sides),c,dishmat)
    _mesh_object('03_Secondary_Reflector',_secondary_geom(g,sides),c,smallmat)
    r1=g['r_secondary']-0.2
    r2=g['support_r']+0.1
    z=g['secondary_rim_z']-0.7
    for i in range(3):
        theta=TAU*i/3.0
        direction=(math.cos(theta), math.sin(theta))
        a=(r1*direction[0],r1*direction[1],z)
        b=(r2*direction[0],r2*direction[1],z)
        _mesh_object('04_Support_%d'%(i+1),_rod_geom(a,b,float(p.support_thickness)/2.0),c,supportmat)
    counts={}
    if p.show_rays:
        counts=_create_rays(p,g,c)
    if p.show_reference:
        cr=_new_collection(REFERENCE_COLLECTION)
        ref=_mesh_object('Reference_Open_Megaphone',_reference_geom(g,sides),cr,_material('Chappy-Reference',(0.54,0.68,0.60)))
        ref.location.x=mm(g['diameter']+45.0)
        cr['description']='Reference open horn: same max diameter and overall length.'

    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    horn.select_set(True)
    bpy.context.view_layer.objects.active=horn
    p.last_summary=(
        '大反射板端 %.1fmm / 共通焦点 %.1fmm / 小反射板頂点 %.1fmm'
        %(g['z_rim'],g['common_focus'],g['secondary_vertex'])
    )
    if counts:
        p.last_summary+=' / 音線：'+str(counts['ALIGNED'])+'/'+str(sum(counts.values()))+' 本が5°以内'
    return g


def _stl_binary(filepath, ob):
    """Export one mesh object in millimetres, centered on XY and placed on z=0 for FDM."""
    depsgraph=bpy.context.evaluated_depsgraph_get()
    ob_ev=ob.evaluated_get(depsgraph)
    mesh=ob_ev.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix=ob.matrix_world
        vertices=[tuple((matrix@v.co)*1000.0) for v in mesh.vertices]
        min_x=min(v[0] for v in vertices)
        max_x=max(v[0] for v in vertices)
        min_y=min(v[1] for v in vertices)
        max_y=max(v[1] for v in vertices)
        min_z=min(v[2] for v in vertices)
        shift=((min_x+max_x)/2.0,(min_y+max_y)/2.0,min_z)
        vertices=[(v[0]-shift[0],v[1]-shift[1],v[2]-shift[2]) for v in vertices]
        count=len(mesh.loop_triangles)
        if not count or count >= 2**32:
            raise RuntimeError('No exportable triangles in '+ob.name)
        with open(filepath,'wb') as f:
            f.write(('Chappy Dual Reflector Maker - '+ob.name).encode('ascii','replace')[:80].ljust(80,b'\x00'))
            f.write(struct.pack('<I',count))
            for tri in mesh.loop_triangles:
                pa=Vector(vertices[tri.vertices[0]])
                pb=Vector(vertices[tri.vertices[1]])
                pc=Vector(vertices[tri.vertices[2]])
                normal=(pb-pa).cross(pc-pa)
                if normal.length>1e-15:
                    normal.normalize()
                else:
                    normal=Vector((0,0,0))
                f.write(struct.pack('<12fH',
                    normal.x,normal.y,normal.z,
                    pa.x,pa.y,pa.z,pb.x,pb.y,pb.z,pc.x,pc.y,pc.z,0
                ))
    finally:
        ob_ev.to_mesh_clear()


class CHAPPY_PG_dual_reflector(bpy.types.PropertyGroup):
    mode: EnumProperty(
        name='音源に合わせた大反射面',
        items=[
            ('ELLIPSE','声用：楕円面＋小パラボラ','口元の点音源を想定。楕円面の２焦点を利用'),
            ('PARABOLA','比較：二重パラボラ','平行入射音に対する幾何学的な反射'),
        ], default='ELLIPSE'
    )
    diameter: FloatProperty(name='最大外径',default=100.0,min=60.0,max=180.0,precision=1,description='mm')
    length: FloatProperty(name='全長',default=115.0,min=55.0,max=300.0,precision=1,description='mm')
    mouth_d: FloatProperty(name='口元入口径',default=32.0,min=15.0,max=65.0,precision=1,description='mm')
    exit_d: FloatProperty(name='中央出口径',default=32.0,min=15.0,max=80.0,precision=1,description='mm')
    wall: FloatProperty(name='樹脂厚',default=2.0,min=1.0,max=4.0,precision=2,description='mm')
    primary_depth: FloatProperty(name='大反射面 深さ',default=14.0,min=2.0,max=45.0,precision=1,description='二重パラボラ時のみ mm')
    focus_z: FloatProperty(name='楕円面の共通焦点',default=74.0,min=15.0,max=270.0,precision=1,description='入口面からの距離 mm')
    secondary_d: FloatProperty(name='小反射面 直径',default=24.0,min=10.0,max=60.0,precision=1,description='mm')
    secondary_depth: FloatProperty(name='小反射面 深さ',default=5.0,min=1.0,max=18.0,precision=1,description='mm')
    secondary_offset: FloatProperty(name='小反射面の前後ずらし',default=0.0,min=-15.0,max=15.0,precision=1,description='共通焦点からの軸方向調整 mm')
    support_thickness: FloatProperty(name='支柱直径',default=3.0,min=1.5,max=6.0,precision=1,description='mm')
    resolution: IntProperty(name='円周分割',default=96,min=24,max=256)
    show_rays: BoolProperty(name='反射経路プレビュー',default=True)
    ray_source: EnumProperty(name='音源モデル',items=[
        ('MOUTH','口元の点音源','口元から広がる幾何学音線'),
        ('PLANE','平行入射','パラボラに有利な理想的な平行音線'),
    ],default='MOUTH')
    ray_count: IntProperty(name='片側の音線数',default=7,min=2,max=20)
    show_reference: BoolProperty(name='普通のメガホンを並べる',default=False)
    export_dir: StringProperty(name='STL保存先',subtype='DIR_PATH',default='//Chappy_DualReflector_STL')
    include_reference: BoolProperty(name='比較用も書き出す',default=False)
    last_summary: StringProperty(name='前回の生成値',default='まだモデルを生成していません')


class CHAPPY_OT_build_dual(bpy.types.Operator):
    bl_idname='chappy.build_dual_reflector'
    bl_label='二重反射メガホンを作成 / 更新'
    bl_description='このアドオンが作成したコレクションだけを作り直します'
    bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        p=context.scene.chappy_dual_reflector
        try:
            g=_generate(p)
        except (ValueError,RuntimeError) as e:
            self.report({'ERROR'},str(e))
            return {'CANCELLED'}
        self.report({'INFO'},'生成完了：外径 %.1fmm、全長 %.1fmm'%(g['diameter'],g['length']))
        return {'FINISHED'}


class CHAPPY_OT_export_dual(bpy.types.Operator):
    bl_idname='chappy.export_dual_reflector'
    bl_label='部品ごとにSTL書き出し'
    bl_description='各部品をmm単位・底面Z=0で個別STLにします。位置合わせ座標はリセットされます'
    bl_options={'REGISTER'}
    def execute(self,context):
        p=context.scene.chappy_dual_reflector
        root=bpy.data.collections.get(MAIN_COLLECTION)
        if root is None:
            self.report({'ERROR'},'先にモデルを生成してください')
            return {'CANCELLED'}
        filepath=bpy.path.abspath(p.export_dir)
        try:
            os.makedirs(filepath,exist_ok=True)
            count=0
            collections=[root]
            if p.include_reference:
                ref=bpy.data.collections.get(REFERENCE_COLLECTION)
                if ref is not None:
                    collections.append(ref)
            for collection in collections:
                for ob in collection.all_objects:
                    if ob.type!='MESH' or not ob.get('chappy_generated'):
                        continue
                    name=re.sub(r'[^A-Za-z0-9_-]+','_',ob.name)
                    _stl_binary(os.path.join(filepath,name+'.stl'),ob)
                    count+=1
            note=os.path.join(filepath,'READ_ME_FIRST.txt')
            with open(note,'w',encoding='utf-8') as f:
                f.write('Chappy Dual Reflector Maker\n')
                f.write('Units: millimetres. Each STL is centered at XY origin and placed on Z=0.\n')
                f.write('Parts are exported separately; assemble with physical alignment and adhesive.\n')
                f.write('Model is an untested acoustic prototype; ray curves are geometric only.\n')
                f.write('WARNING: not verified for breathability, acoustic performance or safe skin contact.\n')
                f.write('Avoid high sound pressure near ears.\n')
                f.write('Mode: '+p.mode+'\n')
                f.write(p.last_summary+'\n')
            self.report({'INFO'},'%d 部品を保存: %s'%(count,filepath))
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError) as e:
            self.report({'ERROR'},'STL保存失敗: '+str(e))
            return {'CANCELLED'}


class CHAPPY_PT_dual_reflector(bpy.types.Panel):
    bl_label='Dual Reflector Maker'
    bl_idname='CHAPPY_PT_dual_reflector'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='Chappy'
    def draw(self,context):
        p=context.scene.chappy_dual_reflector
        layout=self.layout
        layout.prop(p,'mode')
        col=layout.column(align=True)
        col.label(text='1. 全体寸法（mm）',icon='MESH_CONE')
        col.prop(p,'diameter')
        col.prop(p,'length')
        col.prop(p,'mouth_d')
        col.prop(p,'exit_d')
        col.prop(p,'wall')
        col.separator()
        col.label(text='2. 反射面の形状',icon='MOD_CURVE')
        if p.mode=='ELLIPSE':
            col.prop(p,'focus_z')
        else:
            col.prop(p,'primary_depth')
        col.prop(p,'secondary_d')
        col.prop(p,'secondary_depth')
        col.prop(p,'secondary_offset')
        col.prop(p,'support_thickness')
        col.separator()
        col.label(text='3. 音線と比較',icon='SHADING_RENDERED')
        col.prop(p,'show_rays')
        if p.show_rays:
            col.prop(p,'ray_source')
            col.prop(p,'ray_count')
        col.prop(p,'show_reference')
        col.prop(p,'resolution')
        try:
            g=_geom(p)
            info=layout.box()
            info.label(text='参考：大反射面端 %.1f mm'%g['z_rim'])
            info.label(text='共通焦点 %.1f mm'%g['common_focus'])
            info.label(text='小反射板頂点 %.1f mm'%g['secondary_vertex'])
        except ValueError as e:
            info=layout.box()
            info.label(text='寸法が不整合：',icon='ERROR')
            info.label(text=str(e))
        layout.operator('chappy.build_dual_reflector',icon='FILE_REFRESH')
        exp=layout.box()
        exp.label(text='4. STL 書き出し',icon='EXPORT')
        exp.prop(p,'export_dir')
        exp.prop(p,'include_reference')
        exp.operator('chappy.export_dual_reflector',icon='EXPORT')
        info=layout.box()
        info.label(text='反射線＝幾何光学の目安',icon='INFO')
        info.label(text='実際の回折・共鳴は計算しません')
        info.label(text='外殻と支柱は別部品／接着固定')
        info.label(text='手動音声用・性能未測定')


_CLASSES=(
    CHAPPY_PG_dual_reflector,CHAPPY_OT_build_dual,
    CHAPPY_OT_export_dual,CHAPPY_PT_dual_reflector,
)


def register():
    for klass in _CLASSES:
        bpy.utils.register_class(klass)
    bpy.types.Scene.chappy_dual_reflector=PointerProperty(type=CHAPPY_PG_dual_reflector)


def unregister():
    if hasattr(bpy.types.Scene,'chappy_dual_reflector'):
        del bpy.types.Scene.chappy_dual_reflector
    for klass in reversed(_CLASSES):
        bpy.utils.unregister_class(klass)


if __name__=='__main__':
    register()