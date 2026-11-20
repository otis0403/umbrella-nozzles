import bpy,json,math,ast,itertools,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
CASE=ROOT.parent
PREV=CASE/'整機整合_水平吹向圓弧_20261116'
SOURCE=PREV/'完整模型_吹嘴水平朝圓弧_150x16.blend'
DEST=ROOT/'完整模型_垂直上管_後殼加深800mm.blend'
ELBOW=ROOT/'print/STL/elbow_90deg_R90_ID51_socket55p4_spigot55_mm.stl'
helpers_path=CASE/'整機整合_三路51mm_150x16_20261116/integrate_latest.py'
lib={'__file__':str(helpers_path),'__name__':'geometry_helpers'}
syntax=ast.parse(helpers_path.read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in syntax.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign))],type_ignores=[]),'geometry_helpers','exec'),lib)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
source_hash=lib['digest'](SOURCE)


def mesh_hash(ob):
    data={'v':[list(v.co) for v in ob.data.vertices],'p':[list(p.vertices) for p in ob.data.polygons]}
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


moving_names={'鼓風機_150FLJ330W_整體網格','鼓風機_150FLJ330W_左側_整體網格','三路分流接頭_右側','三路分流接頭_左側'}
preserved={o.name:lib['fingerprint'](o) for o in scene.objects if o.type=='MESH' and o.name not in moving_names|{'Cube'} and not o.name.startswith(('小型集風罩_','外購導風管_'))}
shape_hashes={o.name:mesh_hash(o) for o in scene.objects if o.name in moving_names or o.name.startswith('小型集風罩_')}
report={'source':str(SOURCE),'source_sha256':source_hash,'configuration':'vertical upper hoses, curved lower split section, horizontal airknives with R90 elbows',
        'shell_size_mm':[1400,800,1250],'rear_extension_mm':300,'front_plane_y_mm':250,'rear_plane_y_mm':-550,
        'nozzle_size_mm':[150,16],'elbow_R_mm':90,'elbow_quantity':6,'outlets':[],'hoses':[],
        'preserved_mesh_hashes':preserved,'original_part_geometry_hashes':shape_hashes,'CFD_status':'pending for this geometry'}
# Extend only the four rear enclosure boundary vertices.
cube=bpy.data.objects['Cube'];inverse=cube.matrix_world.inverted()
vertices_before=[v.co.copy() for v in cube.data.vertices]
rear=[]
for v in cube.data.vertices:
    p=cube.matrix_world@v.co
    if abs(p.y+25)<.001:
        rear.append(v.index);p.y=-55;v.co=inverse@p
assert len(rear)==4
assert all((cube.data.vertices[i].co-p).length<1e-7 for i,p in enumerate(vertices_before) if i not in rear)
cube.data.update();bpy.context.view_layer.update()
shell=lib['tree'](cube)
report['rear_boundary_vertices_moved']=rear
report['arc_and_other_shell_vertices_identical']=True
# Move each blower and its attached splitter together into the added rear volume.
for side,fan_name,sign in [('右側','鼓風機_150FLJ330W_整體網格',-1),('左側','鼓風機_150FLJ330W_左側_整體網格',1)]:
    fan=bpy.data.objects[fan_name];split=bpy.data.objects['三路分流接頭_'+side]
    relative=fan.matrix_world.inverted()@split.matrix_world
    for ob in [fan,split]:
        matrix=ob.matrix_world.copy();matrix.translation+=Vector((9*sign,-25,0));ob.matrix_world=matrix
    actual=fan.matrix_world.inverted()@split.matrix_world
    error=max(abs(actual[i][j]-relative[i][j]) for i in range(4) for j in range(4))
    report.setdefault('flange_relative_transform_errors',[]).append({'side':side,'maximum_matrix_error':error})
    assert error<.001
report['blower_and_splitter_translation_mm']={'right':[-90,-250,0],'left':[90,-250,0]}

elbow_data=lib['import_mesh'](ELBOW)
elbow_data.materials.clear();elbow_data.materials.append(lib['material']('R90水平轉向接頭',(.09,.31,.36)))
elbows={}
for side,sign in [('右側',-1),('左側',1)]:
    for index in [1,2,3]:
        ob=bpy.data.objects[f'小型集風罩_{side}_{index}']
        mouth=ob.matrix_world@Vector((0,0,188))
        flow=ob.matrix_world.to_3x3().col[2].normalized()
        if index==3:
            radius=Vector((mouth.x,mouth.y-60,0)).length
            angle=math.radians(37)
            mouth=Vector((sign*radius*math.sin(angle),60-radius*math.cos(angle),mouth.z))
            flow=Vector((-sign*math.sin(angle),math.cos(angle),0))
        width=Vector((-flow.y,flow.x,0));short=width.cross(flow).normalized()
        matrix=Matrix.Identity(4)
        for col,axis in enumerate([short,width,flow]):
            for row in range(3):matrix[row][col]=axis[row]*.1
        matrix.translation=mouth-18.8*flow;ob.matrix_world=matrix
        elbow=bpy.data.objects.new(f'上端R90彎頭_{side}_{index}',elbow_data)
        scene.collection.objects.link(elbow)
        matrix=Matrix.Identity(4)
        for col,axis in enumerate([flow.cross(Vector((0,0,1))),flow,Vector((0,0,1))]):
            for row in range(3):matrix[row][col]=axis[row]*.1
        matrix.translation=ob.matrix_world.translation-9.5*flow-Vector((0,0,12.5))
        elbow.matrix_world=matrix;elbows[(side,index)]=elbow
        elbow['source_STL']=str(ELBOW);elbow['flow_ID_mm']=51.;elbow['bend_radius_mm']=90.
        ray_offset=0.0
        hit=shell.ray_cast(mouth,flow,100)
        if hit[0] is None:
            for ray_offset in [.0001,-.0001,.001,-.001]:
                hit=shell.ray_cast(mouth+Vector((0,0,ray_offset)),flow,100)
                if hit[0] is not None and 4<hit[3]<6:break
        assert hit[0] is not None and 4<hit[3]<6,(ob.name,list(mouth),list(hit[0]) if hit[0] else None,hit[3])
        report['outlets'].append({'name':ob.name,'mouth_mm':list(mouth*10),'flow_axis':list(flow),
            'arc_standoff_mm':hit[3]*10,'ray_seam_offset_mm':ray_offset*10,'outer_pair_angle_degrees':37 if index==3 else None,
            'elbow':elbow.name,'vertical_hose_inlet_mm':list(10*elbow.matrix_world.translation)})
bpy.context.view_layer.update()


def lower_route(start,direction,end):
    first=start+4.5*direction
    up=Vector((0,0,1))
    options=[]
    for join_height in [38,40,42,44,46,48]:
        join=Vector((end.x,end.y,join_height))
        distance=(join-first).length
        for a in [.2,.3,.4,.5,.6,.8,1.0]:
            for b in [.2,.3,.4,.5,.6,.8,1.0]:
                p1=first+direction*(distance*a);p2=join-up*(distance*b)
                curve=[lib['bezier'](first,p1,p2,join,i/160) for i in range(161)]
                radius=lib['curve_radius'](first,p1,p2,join)
                monotonic=min((q.z-p.z) for p,q in zip(curve,curve[1:]))>=-.001
                points=[start,first]+curve[1:]+[end]
                clearance=min(shell.find_nearest(p)[3] for p in points[::4])
                length=sum((q-p).length for p,q in zip(points,points[1:]))
                score=10000*(not monotonic)+1000*max(0,4-radius)+1000*max(0,2.83-clearance)+length+.2*(join_height-38)
                options.append((score,points,radius,clearance,join_height))
    _,points,radius,clearance,join_height=min(options,key=lambda x:x[0])
    return points,radius,clearance,join_height


right_paths={}
for side in ['右側','左側']:
    split=bpy.data.objects['三路分流接頭_'+side]
    ends=[elbows[(side,i)].matrix_world@Vector((0,0,25)) for i in [1,2,3]]
    ports=[]
    for k in range(3):
        E,D=lib['port'](k);ports.append((split.matrix_world@E,(split.matrix_world.to_3x3()@D).normalized()))
    match=min(itertools.permutations(range(3)),key=lambda order:sum((ports[k][0]-ends[order[k]]).length**2 for k in range(3)))
    for k,index0 in enumerate(match):
        index=index0+1;start,direction=ports[k];end=ends[index0]
        if side=='右側':
            points,radius,clearance,join=lower_route(start,direction,end)
            right_paths[index]=(points,radius,clearance,join)
        else:
            right,radius,clearance,join=right_paths[index]
            points=[Vector((-p.x,p.y,p.z)) for p in right]
            assert (points[0]-start).length<.001 and (points[-1]-end).length<.001
            points[0]=start;points[-1]=end;points[-2].x=end.x;points[-2].y=end.y
        assert radius>=4,(side,index,radius)
        name=f'外購導風管_{side}_{index}'
        original=bpy.data.objects[name];material=original.data.materials[0]
        bpy.data.objects.remove(original,do_unlink=True)
        hose=lib['tube'](name,points,material)
        hose['upper_main_segment']='vertical'
        hose['upper_main_start_height_mm']=join*10
        axis=(points[-1]-points[-2]).normalized()
        assert abs(axis.x)<1e-6 and abs(axis.y)<1e-6 and axis.z>0
        report['hoses'].append({'name':name,'elbow':elbows[(side,index)].name,'port_index':k,
            'centerline_length_mm':hose['hose_centerline_length_mm'],'lower_minimum_bend_radius_mm':radius*10,
            'vertical_main_start_height_mm':join*10,'vertical_main_end_height_mm':end.z*10,
            'vertical_main_length_mm':(end.z-join)*10,'vertical_main_axis':list(axis),
            'hose_insertion_each_end_mm':25,'lower_external_straight_mm':20})
bpy.context.view_layer.update()
# Full assembly non-mating intersection checks.
meshes=[o for o in scene.objects if o.type=='MESH']
boxes={o.name:lib['bounds'](o) for o in meshes}
cache={};collisions=[];checked=0
for a,b in itertools.combinations(meshes,2):
    hose=a if a.name.startswith('外購導風管_') else b if b.name.startswith('外購導風管_') else None
    if hose:
        other=b if hose==a else a
        link=next(h for h in report['hoses'] if h['name']==hose.name)
        side='右側' if '右側' in hose.name else '左側'
        if other.name in [link['elbow'],'三路分流接頭_'+side]:continue
    elbow=a if a.name.startswith('上端R90彎頭_') else b if b.name.startswith('上端R90彎頭_') else None
    if elbow:
        other=b if elbow==a else a
        row=next(r for r in report['outlets'] if r['elbow']==elbow.name)
        if other.name==row['name']:continue
    if a.name in preserved and b.name in preserved:continue
    A,B=boxes[a.name],boxes[b.name]
    if not all(A[0][i]<B[1][i]-.0001 and B[0][i]<A[1][i]-.0001 for i in range(3)):continue
    for ob in [a,b]:
        if ob.name not in cache:cache[ob.name]=lib['tree'](ob)
    hits=cache[a.name].overlap(cache[b.name]);checked+=1
    if hits:collisions.append({'parts':[a.name,b.name],'triangle_pairs':len(hits)})
report['checked_overlapping_mesh_pairs']=checked
report['non_mating_intersections']=collisions
report['assembly_bounds_mm']=[[10*min(boxes[o.name][0][i] for o in meshes) for i in range(3)],
                              [10*max(boxes[o.name][1][i] for o in meshes) for i in range(3)]]
report['preserved_meshes_verified']=all(lib['fingerprint'](bpy.data.objects[n])==h for n,h in preserved.items())
report['source_part_geometries_verified']=all(mesh_hash(bpy.data.objects[n])==h for n,h in shape_hashes.items())
report['source_file_sha256_verified']=lib['digest'](SOURCE)==source_hash
(ROOT/'vertical_layout_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('VERTICAL_LAYOUT_CHECKS',json.dumps({k:v for k,v in report.items() if k not in ['preserved_mesh_hashes','original_part_geometry_hashes']},ensure_ascii=False),flush=True)
assert not collisions,'Assembly interference requires correction'
assert report['preserved_meshes_verified'] and report['source_part_geometries_verified']
lo,hi=report['assembly_bounds_mm']
assert lo[0]>=-700.01 and hi[0]<=700.01 and lo[1]>=-550.01 and hi[1]<=250.01 and hi[2]<=1250.01
# Native model and two CAD renders.
for ob in list(bpy.data.objects):
    if ob.name.startswith('整機預覽燈'):bpy.data.objects.remove(ob,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1500;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
for location,power,size in [((-100,-200,240),1800000,160),((150,-160,180),1300000,130),((0,100,210),1400000,120)]:
    bpy.ops.object.light_add(type='AREA',location=location);ob=bpy.context.object;ob.name='整機預覽燈'
    ob.data.energy=power;ob.data.size=size;lib['aim'](ob,(0,-20,60))
cam=bpy.data.objects['Camera'];scene.camera=cam
cam.data.type='ORTHO';cam.data.clip_start=.05;cam.data.clip_end=10000
cam.location=(-190,-320,185);cam.data.ortho_scale=290;lib['aim'](cam,(0,-15,62))
scene.render.filepath=str(ROOT/'01_後殼加深_垂直上管整機.png')
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
bpy.ops.render.render(write_still=True)
cube.hide_render=True
cam.location=(0,-250,115);cam.data.ortho_scale=175;lib['aim'](cam,(0,-32,48))
scene.render.filepath=str(ROOT/'02_垂直主段_水平吹嘴配置.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(DEST))
assert all(lib['fingerprint'](bpy.data.objects[n])==h for n,h in preserved.items())
assert all(mesh_hash(bpy.data.objects[n])==h for n,h in shape_hashes.items())
assert lib['digest'](SOURCE)==source_hash
for row in report['outlets']:
    ob=bpy.data.objects[row['name']]
    assert abs(ob.matrix_world.to_3x3().col[2].normalized().z)<1e-6
for i in [1,2,3]:
    a=bpy.data.objects[f'小型集風罩_右側_{i}'].matrix_world@Vector((0,0,188))
    b=bpy.data.objects[f'小型集風罩_左側_{i}'].matrix_world@Vector((0,0,188))
    assert max(abs(a.x+b.x),abs(a.y-b.y),abs(a.z-b.z))*10<.01
# Independent elbow diameters from the imported/reopened mesh.
elbow=bpy.data.objects['上端R90彎頭_右側_1']
tree=BVHTree.FromPolygons([v.co for v in elbow.data.vertices],[tuple(p.vertices) for p in elbow.data.polygons],all_triangles=True)
def span(p,axis=0):return sum(tree.ray_cast(Vector(p),Vector((s,0,0) if axis==0 else (0,s,0)),50)[3] for s in [-1,1])
assert abs(span((0,0,12),1)-55.4)<.03
flow_samples=[span((0,90*(1-math.cos(a)),35+90*math.sin(a))) for a in [math.pi*j/72 for j in range(37)]]
assert max(abs(d-51) for d in flow_samples)<.03
verification={'native_reopened':True,'six_nozzles_horizontal':True,'six_upper_hose_segments_vertical':True,
    'elbow_socket_ID_mm':span((0,0,12),1),'elbow_flow_ID_range_mm':[min(flow_samples),max(flow_samples)],
    'source_geometries_verified':True,'source_file_hash_verified':True,'output_sha256':lib['digest'](DEST)}
(ROOT/'native_reopen_checks.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf8')
notes=f'''# 垂直上管與加深後殼整機版

本版採六條上方主段直立的軟管，底部分流處彎曲，頂端以R90 mm、51 mm內流道的90度接頭銜接原150×16 mm水平吹嘴。六個出口沿放傘弧面中央線左右對稱，中心高度約709.87 mm，到圓弧表面約50 mm。

## 機殼與位置

機殼寬1400 mm、深800 mm、高1250 mm。原後方邊界由Y=-250 mm延伸至-550 mm，後方增加300 mm。延伸四個後方邊界頂點，其餘外殼與圓弧頂點已比對。

左右風機與其三路接頭各向外90 mm、向後250 mm。最外側一對吹嘴沿弧面調整到左右37度位置，為直立管柱與接頭提供側向空間。兩側各三個出口維持中央線上的對稱排列。

## 垂直管路與接頭

上方六條主段為垂直直管，底部可彎曲。各支管長、主段起止高度及下段轉彎半徑詳見vertical_layout_checks.json，這些為CAD中心線量測，裁切仍待實機核對。

新增接頭六顆，中心線轉彎半徑90 mm、內流道51 mm。下端55.4 mm母套口讓51 mm內徑軟管套入25 mm，上端55.0 mm公插口插進現有吹嘴25 mm。公母套口名義直徑間隙0.4 mm，實物試配與氣密待驗證。

接頭單件包絡約60.2×150.1×152.9 mm，幾何尺寸已核對K1C範圍及5 mm brim空間。STL採mm、100%匯入，位於print/STL/elbow_90deg_R90_ID51_socket55p4_spigot55_mm.stl。實際切片、支撐配置及列印結果待確認。

## 核對與使用狀態

六個上方主段軸線為垂直、六個吹嘴出風軸線為水平。非接合面網格交叉檢查通過，所有模型包絡均在加深後機殼範圍內。模型已重新開啟，並量測新接頭套口與37個彎道截面的51 mm內徑。

01圖為加深外殼的整機背面視角。02圖呈現管路與接頭位置，外殼暫時隱藏以便核對。場景採公分座標，Blender scale_length為0.01。

本次完成CAD裝配配置。51 mm軟管外徑54.6 mm為估算，套接、管夾、固定支架、實際裁管長度與此配置的ANSYS風場驗證仍待完成。
'''
(ROOT/'垂直上管與後殼說明.md').write_text(notes,encoding='utf8')
files=[DEST.name,'01_後殼加深_垂直上管整機.png','02_垂直主段_水平吹嘴配置.png','vertical_layout_checks.json','native_reopen_checks.json','elbow_geometry_checks.json','垂直上管與後殼說明.md','print/STL/elbow_90deg_R90_ID51_socket55p4_spigot55_mm.stl']
(ROOT/'delivery_manifest.json').write_text(json.dumps({f:lib['digest'](ROOT/f) for f in files},ensure_ascii=False,indent=2),encoding='utf8')
print('VERTICAL_LAYOUT_FINAL_VERIFIED',json.dumps(verification,ensure_ascii=False),flush=True)




