"""Horizontal airknife placement, using the released nozzle without reshaping."""
import bpy, json, math, ast, sys, hashlib, itertools
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
PREV=ROOT.parent/'整機整合_三路51mm_150x16_20261116'
SOURCE=PREV/'完整模型_中央弧線_三路51mm_150x16.blend'
DEST=ROOT/'完整模型_吹嘴水平朝圓弧_150x16.blend'
# Reuse the checked part transforms, mesh helpers and connection definitions.
lib={'__file__':str(PREV/'integrate_latest.py'),'__name__':'assembly_geometry_helpers'}
syntax=ast.parse((PREV/'integrate_latest.py').read_text(encoding='utf-8-sig'))
helpers=[n for n in syntax.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign))]
exec(compile(ast.Module(body=helpers,type_ignores=[]),'assembly_geometry_helpers','exec'),lib)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
bpy.context.preferences.filepaths.save_version=0
baseline={o.name:lib['fingerprint'](o) for o in scene.objects if o.type=='MESH' and not o.name.startswith(('小型集風罩_','外購導風管_'))}
source_hash=lib['digest'](SOURCE)
shell=lib['tree'](bpy.data.objects['Cube'])


def mesh_digest(ob):
    data={'v':[list(v.co) for v in ob.data.vertices],'p':[list(p.vertices) for p in ob.data.polygons]}
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


def route(start,direction,end,flow):
    # Keep insertion and 20 mm external straight sections clear of each socket lip.
    first=start+4.5*direction
    last=end-4.5*flow
    vertical=Vector((0,0,1))
    tangent=vertical.cross(flow).normalized()
    candidates=[]
    for arc_radius in [4.5,5,6,7.5]:
        for angle_deg in [0,-20,20,-40,40,-60,60]:
            angle=math.radians(angle_deg)
            approach=vertical*math.cos(angle)+tangent*math.sin(angle)
            center=last-arc_radius*approach
            turn_start=center-arc_radius*flow
            distance=(turn_start-first).length
            arc=[center-arc_radius*math.cos(math.pi*i/120)*flow+
                 arc_radius*math.sin(math.pi*i/120)*approach for i in range(61)]
            for a in [.15,.25,.35,.5,.7]:
                for b in [.15,.25,.35,.5,.7]:
                    p1=first+direction*(distance*a)
                    p2=turn_start-approach*(distance*b)
                    curve=[lib['bezier'](first,p1,p2,turn_start,i/120) for i in range(121)]
                    radius=min(lib['curve_radius'](first,p1,p2,turn_start),arc_radius)
                    points=[start,first]+curve[1:]+arc[1:]+[end]
                    clearance=min(shell.find_nearest(p)[3] for p in points[::4])
                    length=sum((q-p).length for p,q in zip(points,points[1:]))
                    score=1000*max(0,4-radius)+1000*max(0,2.83-clearance)+length
                    candidates.append((score,points,radius,clearance))
    _,points,radius,clearance=min(candidates,key=lambda x:x[0])
    return points,radius,clearance

report={'source':str(SOURCE),'source_sha256':source_hash,'source_unit_scale':scene.unit_settings.scale_length,
        'configuration':'two blowers, six horizontal airknives, symmetric middle line of umbrella arc',
        'back_protrusion_authorized':True,'target_standoff_mm':50,'nozzle_size_mm':[150,16],
        'nozzle_geometry_reused':True,'flow_simulation_status':'pending for this installed geometry',
        'outlets':[],'hoses':[],'preserved_mesh_hashes':baseline}
nozzles=[]
geometry_before={}
for ob in list(scene.objects):
    if not ob.name.startswith('小型集風罩_'):
        continue
    geometry_before[ob.name]=mesh_digest(ob)
    old_mouth=ob.matrix_world@Vector((0,0,188))
    tangent=ob.matrix_world.to_3x3().col[1].normalized()
    flow=tangent.cross(Vector((0,0,1))).normalized()
    short=tangent.cross(flow).normalized()
    mouth=old_mouth+3*flow
    transform=Matrix.Identity(4)
    for col,axis in enumerate([short,tangent,flow]):
        for row in range(3):
            transform[row][col]=axis[row]*.1
    transform.translation=mouth-18.8*flow
    ob.matrix_world=transform
    ob['installed_direction']='horizontal flow towards umbrella curved surface'
    ob['installed_nozzle_body_plane']='parallel to floor'
    ob['installed_target_standoff_mm']=50.0
    assert mesh_digest(ob)==geometry_before[ob.name]
    target=shell.ray_cast(mouth,flow,100)
    assert target[0] is not None and 4<target[3]<6,(ob.name,target)
    slot_rays=[]
    for j in range(61):
        p=ob.matrix_world@Vector((0,-74+148*j/60,188))
        hit=shell.ray_cast(p,flow,100)
        assert hit[0] is not None and hit[3]>0
        slot_rays.append(hit[3]*10)
    report['outlets'].append({'name':ob.name,'mouth_center_mm':list(10*mouth),'flow_axis':list(flow),
        'long_slot_axis':list(tangent),'short_axis':list(short),'target_point_mm':list(10*target[0]),
        'axis_to_floor_angle_degrees':math.degrees(math.asin(abs(flow.z))),
        'nozzle_body_to_floor_angle_degrees':math.degrees(math.acos(min(1,abs(short.z)))),
        'center_standoff_mm':target[3]*10,'slot_to_arc_gap_range_mm':[min(slot_rays),max(slot_rays)],
        'slot_ray_samples':61,'mesh_hash':geometry_before[ob.name]})
    nozzles.append(ob)
bpy.context.view_layer.update()

for side in ['右側','左側']:
    split=bpy.data.objects['三路分流接頭_'+side]
    group=[bpy.data.objects[f'小型集風罩_{side}_{i}'] for i in [1,2,3]]
    ports=[]
    for k in range(3):
        E,D=lib['port'](k)
        ports.append((split.matrix_world@E,(split.matrix_world.to_3x3()@D).normalized()))
    match=min(itertools.permutations(range(3)),key=lambda order:sum((ports[k][0]-group[order[k]].matrix_world.translation).length**2 for k in range(3)))
    for k,index in enumerate(match):
        nozzle=group[index]
        flow=nozzle.matrix_world.to_3x3().col[2].normalized()
        end=nozzle.matrix_world@Vector((0,0,25))
        start,direction=ports[k]
        points,radius,clearance=route(start,direction,end,flow)
        name=f'外購導風管_{side}_{index+1}'
        original=bpy.data.objects[name]
        mat=original.data.materials[0]
        bpy.data.objects.remove(original,do_unlink=True)
        hose=lib['tube'](name,points,mat)
        report['hoses'].append({'name':name,'nozzle':nozzle.name,'port_index':k,
            'centerline_length_mm':hose['hose_centerline_length_mm'],'minimum_centerline_bend_radius_mm':radius*10,
            'centerline_shell_clearance_mm':clearance*10,'insertion_each_end_mm':25,'straight_hose_outside_each_joint_mm':20})
        assert radius>=4,(name,radius)
bpy.context.view_layer.update()

# Check all non-mating mesh pairs before publishing the assembly.
meshes=[o for o in scene.objects if o.type=='MESH']
boxes={o.name:lib['bounds'](o) for o in meshes}
new_parts=[o for o in meshes if o.name.startswith(('小型集風罩_','外購導風管_'))]
cache={}
collisions=[]
checked=0
for a,b in itertools.combinations(meshes,2):
    if a not in new_parts and b not in new_parts:
        continue
    hose=a if a.name.startswith('外購導風管_') else b if b.name.startswith('外購導風管_') else None
    if hose is not None:
        other=b if hose==a else a
        link=next(h for h in report['hoses'] if h['name']==hose.name)
        side='右側' if '右側' in hose.name else '左側'
        if other.name in [link['nozzle'],'三路分流接頭_'+side]:
            continue
    A,B=boxes[a.name],boxes[b.name]
    if not all(A[0][i]<B[1][i]-.0001 and B[0][i]<A[1][i]-.0001 for i in range(3)):
        continue
    for ob in [a,b]:
        if ob.name not in cache:
            cache[ob.name]=lib['tree'](ob)
    hits=cache[a.name].overlap(cache[b.name])
    checked+=1
    if hits:
        collisions.append({'parts':[a.name,b.name],'triangle_pairs':len(hits)})
report['checked_overlapping_pairs']=checked
report['non_mating_intersections']=collisions
report['assembly_bounds_mm']=[[10*min(boxes[o.name][0][i] for o in meshes) for i in range(3)],
                              [10*max(boxes[o.name][1][i] for o in meshes) for i in range(3)]]
report['maximum_back_protrusion_mm']=max(0,-250-report['assembly_bounds_mm'][0][1])
report['preserved_meshes_verified']=all(lib['fingerprint'](bpy.data.objects[n])==h for n,h in baseline.items())
report['source_file_hash_verified']=lib['digest'](SOURCE)==source_hash
(ROOT/'horizontal_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HORIZONTAL_ASSEMBLY_CHECKS',json.dumps({k:v for k,v in report.items() if k!='preserved_mesh_hashes'},ensure_ascii=False),flush=True)
assert not collisions,'Horizontal placement interference requires correction'
assert report['preserved_meshes_verified'] and report['source_file_hash_verified']

# Save a usable native rear view and render the actual CAD.
for ob in list(bpy.data.objects):
    if ob.name.startswith('整機預覽燈'):
        bpy.data.objects.remove(ob,do_unlink=True)
scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.render.resolution_x=1500
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
for loc,power,size in [((-100,-160,220),1500000,150),((120,-100,160),1000000,120),((0,80,200),1200000,100)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    ob=bpy.context.object;ob.name='整機預覽燈'
    ob.data.energy=power;ob.data.size=size;lib['aim'](ob,(0,-10,60))
cam=bpy.data.objects['Camera'];scene.camera=cam
cam.data.type='ORTHO';cam.data.clip_start=.05;cam.data.clip_end=10000
cam.location=(-180,-260,170);cam.data.ortho_scale=255
lib['aim'](cam,(0,-10,62))
scene.render.filepath=str(ROOT/'01_整機_吹嘴水平朝圓弧.png')
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
bpy.ops.render.render(write_still=True)

# The top-view guides exist only in the preview render.
bpy.data.objects['Cube'].hide_render=True
arrow_mat=lib['material']('預覽_水平氣流方向',(.9,.25,.03))
arc_mat=lib['material']('預覽_圓弧目標線',(.9,.88,.75))
curve=bpy.data.curves.new('圓弧表面中線','CURVE');curve.dimensions='3D';curve.bevel_depth=.18;curve.bevel_resolution=3
spline=curve.splines.new('POLY');points=[]
height=report['outlets'][0]['mouth_center_mm'][2]/10
for i in range(101):
    angle=math.radians(-44+88*i/100)
    direction=Vector((math.sin(angle),math.cos(angle),0))
    origin=Vector((-90*math.sin(angle),60-90*math.cos(angle),height))
    hit=shell.ray_cast(origin,direction,40)
    if hit[0] is not None:
        points.append(hit[0])
spline.points.add(len(points)-1)
for p,q in zip(spline.points,points):
    p.co=(*q,1)
arc=bpy.data.objects.new('預覽_圓弧表面中線',curve);scene.collection.objects.link(arc);arc.data.materials.append(arc_mat)
for row in report['outlets']:
    start=Vector(row['mouth_center_mm'])/10
    flow=Vector(row['flow_axis'])
    end=Vector(row['target_point_mm'])/10
    a=start+.6*flow;b=end-.8*flow
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=.12,depth=(b-a).length,location=(a+b)/2)
    ob=bpy.context.object;ob.rotation_euler=flow.to_track_quat('Z','Y').to_euler();ob.data.materials.append(arrow_mat)
    bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.5,radius2=0,depth=1.2,location=b)
    ob=bpy.context.object;ob.rotation_euler=flow.to_track_quat('Z','Y').to_euler();ob.data.materials.append(arrow_mat)
cam.location=(0,-7,250);cam.data.ortho_scale=175;lib['aim'](cam,(0,-7,height))
scene.render.filepath=str(ROOT/'02_俯視_水平吹向圓弧.png')
bpy.ops.render.render(write_still=True)

# Fresh native reopen, with no transient guides in the saved machine model.
bpy.ops.wm.open_mainfile(filepath=str(DEST))
assert all(lib['fingerprint'](bpy.data.objects[n])==h for n,h in baseline.items())
for row in report['outlets']:
    ob=bpy.data.objects[row['name']]
    assert mesh_digest(ob)==row['mesh_hash']
    flow=ob.matrix_world.to_3x3().col[2].normalized()
    tangent=ob.matrix_world.to_3x3().col[1].normalized()
    assert abs(flow.z)<1e-6 and abs(tangent.z)<1e-6
    actual=ob.matrix_world@Vector((0,0,188))
    assert (10*actual-Vector(row['mouth_center_mm'])).length<.01
for i in [1,2,3]:
    a=bpy.data.objects[f'小型集風罩_右側_{i}'].matrix_world@Vector((0,0,188))
    b=bpy.data.objects[f'小型集風罩_左側_{i}'].matrix_world@Vector((0,0,188))
    assert max(abs(a.x+b.x),abs(a.y-b.y),abs(a.z-b.z))*10<.01
assert lib['digest'](SOURCE)==source_hash
verification={'native_reopened':True,'all_six_flow_axes_horizontal':True,'all_six_nozzle_bodies_parallel_floor':True,
    'all_six_released_nozzle_meshes_verified':True,'left_right_symmetry_error_under_mm':.01,
    'unaltered_meshes_verified':len(baseline),'source_hash_verified':True,'output_sha256':lib['digest'](DEST)}
(ROOT/'native_reopen_checks.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf8')
lengths='、'.join(f"{h['name']} {h['centerline_length_mm']:.1f} mm" for h in report['hoses'])
notes=f'''# 吹嘴水平朝圓弧整機版

兩顆風機搭配六個150×16 mm吹嘴。吹嘴本體與長縫平行地板，出風軸線為水平方向，六個出口沿放傘弧面中央線左右對稱。出口中心高度約709.87 mm，中心線到圓弧表面距離約50 mm。

使用原188 mm長外套式吹嘴，套口內徑55.4 mm。使用者已確認背面可凸出。本版整組含軟管的最大背面凸出量約{report['maximum_back_protrusion_mm']:.1f} mm，配置時需要相應背面空間。

本版軟管兩端各套入25 mm，每個接頭外另有20 mm直段。各支中心線長度為{lengths}。這些長度是CAD走向量測，實際裁切與管夾安裝需依實物核對。軟管內徑51 mm、外徑54.6 mm為本版建模估算，55.4 mm套口仍待實物試配。

已檢查六個吹嘴的水平出風方向、與地板平行的本體方向、61個出口到圓弧射線、左右對稱、軟管轉彎半徑，以及新零件與其他裝配零件的非接合面干涉。模型已重新開啟驗證，六個吹嘴的局部網格與來源一致。

01圖顯示整機後方配置。02圖為俯視，橘色箭頭標示水平出風方向，淺色線標示圓弧目標表面的中心線。這些方向指示只用於圖片。

本次為裝配位置修正。套接實測、管夾固定及這個水平安裝配置的ANSYS風場驗證仍待完成。

## 列印零件來源

- 吹嘴共六顆，../Nozzle_FemaleSocket_51mm_150x16_20261114/print/STL/nozzle_150x16_female_ID55p4_H188_mm.stl。
- 中管口加高10 mm的三路接頭共兩顆，../整機整合_三路51mm_150x16_20261116/print/STL/splitter_center_neck_plus10_mm.stl。

場景採公分座標，Blender scale_length為0.01。列印STL採mm、100%匯入。
'''
(ROOT/'水平配置說明.md').write_text(notes,encoding='utf8')
files=[DEST.name,'01_整機_吹嘴水平朝圓弧.png','02_俯視_水平吹向圓弧.png','horizontal_checks.json','native_reopen_checks.json','水平配置說明.md']
(ROOT/'delivery_manifest.json').write_text(json.dumps({f:lib['digest'](ROOT/f) for f in files},ensure_ascii=False,indent=2),encoding='utf8')
print('HORIZONTAL_MACHINE_FINAL_VERIFIED',json.dumps(verification,ensure_ascii=False),flush=True)

