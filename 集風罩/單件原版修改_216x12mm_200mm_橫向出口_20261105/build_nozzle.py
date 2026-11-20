"""216 x 12 mm one-piece nozzle, outlet long axis turned relative to fixed flange.

Generate the new parametric shell; use existing proven helpers read-only.
Original 200 mm single-part CAD is the flange/neck compatibility reference.
"""
from pathlib import Path
from array import array
from collections import Counter
import ast,sys,math,json,hashlib,struct,bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;sys.path.insert(0,str(HERE))
from geometry import H,NECK,TRANSITION,LIP,WALL,HOLES,section,local_to_global,core_radii_uv,thickness,net_area,ease
PREVIOUS=HERE.parent/'單件原版修改_216x4mm_200mm_尖鼻核心_20261104'
SOURCE=PREVIOUS/'直通吹嘴_216x4mm_200mm_尖鼻核心_單件.blend'
SOURCE_STL=PREVIOUS/'直通吹嘴_216x4mm_200mm_尖鼻核心_單件_mm.stl'
HELPERS=HERE.parent/'直通吹嘴_Dyson式導流_216x4mm_20261103/build_nozzle.py'
SHELL_HELPERS=HERE.parent/'直通長型風刀測試版/build_straight_nozzles.py'
NAME='直通吹嘴_216x12mm_200mm_橫向出口_單件'
STL=HERE/(NAME+'_mm.stl');BLEND=HERE/(NAME+'.blend');N=256
selected={'sha','create_loft','activate','boolean','bounds','solid_check','geohash','tree_for','export_stl'}
nodes=ast.parse(HELPERS.read_text(encoding='utf-8')).body
exec(compile(ast.Module(body=[n for n in nodes if isinstance(n,ast.FunctionDef) and n.name in selected],type_ignores=[]),str(HELPERS),'exec'),globals())
nodes=ast.parse(SHELL_HELPERS.read_text(encoding='utf-8')).body
exec(compile(ast.Module(body=[n for n in nodes if isinstance(n,ast.FunctionDef) and n.name in {'rect','mesh','solid_surface'}],type_ignores=[]),str(SHELL_HELPERS),'exec'),globals())
protected={str(p):sha(p) for p in [SOURCE,SOURCE_STL,HELPERS,SHELL_HELPERS,PREVIOUS/'geometry.py']}
previous_report=json.loads((PREVIOUS/'尺寸與修改檢查.json').read_text(encoding='utf-8'))
assert sha(SOURCE)==previous_report['blend_sha256'] and sha(SOURCE_STL)==previous_report['stl_sha256']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
with bpy.data.libraries.load(str(SOURCE),link=False) as (available,loaded):loaded.objects=list(available.objects)
refs=[]
for o in loaded.objects:
    if o is not None and o.type=='MESH':scene.collection.objects.link(o);refs.append(o)
assert len(refs)==1
reference=refs[0];activate(reference);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
reference_tree=tree_for(reference)
bpy.data.objects.remove(reference,do_unlink=True)

def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(n.outputs[0],out.inputs[0]);n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.38
    return m
mats=[material('外殼_石墨灰',(.065,.09,.115)),material('尖鼻核心_預覽橘',(.95,.27,.035)),material('十字支撐_預覽藍',(.10,.34,.45))]

# Begin the tube inside the 3 mm flange for a real overlap, avoiding coincident
# bottom CSG faces. Material below that level is supplied by the flange.
zs=[2.5,3.,12.]+[12+176*j/120 for j in range(1,121)]+[200.]
outer=[];inner=[]
for z in zs:
    w,d,r=section(z)
    inner.append([Vector(local_to_global(p.x,p.y,z)) for p in rect(w,d,r)])
    outer.append([Vector(local_to_global(p.x,p.y,z)) for p in rect(w+4,d+4,r+2)])
body=solid_surface(outer,inner,mats[0]);body.name=NAME
for m in mats[1:]:body.data.materials.append(m)
flange=create_loft('原方向法蘭',[[tuple(p+Vector((0,0,z))) for p in rect(118,120,4,cx=2)] for z in [0,3]],mats,0)
boolean(body,flange)
inlet=create_loft('原方向82x88入口',[[tuple(p+Vector((0,0,z))) for p in rect(82,88,3)] for z in [-1,4]],mats,0)
boolean(body,inlet,'DIFFERENCE')
for h in HOLES:
    radius=h['diameter_mm']/2
    rings=[[(h['x_mm']+radius*math.cos(2*math.pi*j/64),h['y_mm']+radius*math.sin(2*math.pi*j/64),z) for j in range(64)] for z in [-1,4]]
    boolean(body,create_loft('原固定孔',rings,mats,0),'DIFFERENCE')
shell_stats=solid_check(body)
print('ROTATED_OUTLET_SHELL_AND_FIXED_FLANGE_BUILT',flush=True)

for wide,end in [(True,144.),(False,134.)]:
    rings=[]
    for z in sorted(set([0.,3.,12.,end-12,end]+[end*j/140 for j in range(141)])):
        w,d,r=section(z);t=thickness(z,end)
        a,b=(w/2+.8,t/2) if wide else (t/2,d/2+.8)
        rings.append([local_to_global(u,v,z) for u,v in [(-a,-b),(a,-b),(a,b),(-a,b)]])
    boolean(body,create_loft('底面起印_長向片' if wide else '底面起印_短向片',rings,mats,2))
    solid_check(body)
rings=[]
for z in sorted(set([12.,58.,110.,126.]+[12+114*j/152 for j in range(153)])):
    ru,rv=core_radii_uv(z)
    rings.append([local_to_global(ru*math.cos(2*math.pi*j/128),rv*math.sin(2*math.pi*j/128),z) for j in range(128)])
boolean(body,create_loft('配合出口轉向的尖鼻核心',rings,mats,1))
stats=solid_check(body);bb=bounds(body)
assert all(abs(a-b)<.002 for a,b in zip(bb['size'],[118,220,200])),bb
tree=tree_for(body)

# Fixed-flange compatibility in the original X,Y frame, no rotation of holes.
flange_errors=[]
for z in [1.5,2.9]:
    for j in range(72):
        a=2*math.pi*j/72;origin=Vector((150*math.cos(a),150*math.sin(a),z));direction=Vector((-math.cos(a),-math.sin(a),0))
        new=tree.ray_cast(origin,direction,200);old=reference_tree.ray_cast(origin,direction,200)
        assert new[0] is not None and old[0] is not None
        error=(new[0]-old[0]).length;assert error<.005,(z,j,error)
        flange_errors.append(error)
hole_results=[]
for h in HOLES:
    x,y=h['x_mm'],h['y_mm'];assert tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),5)[0] is None
    diameter=sum(tree.ray_cast(Vector((x,y,1.5)),Vector((s,0,0)),10)[3] for s in [-1,1])
    olddiameter=sum(reference_tree.ray_cast(Vector((x,y,1.5)),Vector((s,0,0)),10)[3] for s in [-1,1])
    assert abs(diameter-h['diameter_mm'])<.03 and abs(diameter-olddiameter)<.003
    hole_results.append({**h,'measured_diameter_mm':diameter,'old_diameter_mm':olddiameter,'through':True})
inlet_results=[]
for origin,direction,axis,expected in [((30,5,6),(1,0,0),0,41),((-30,5,6),(-1,0,0),0,-41),((5,30,6),(0,1,0),1,44),((5,-30,6),(0,-1,0),1,-44)]:
    hit=tree.ray_cast(Vector(origin),Vector(direction),30);assert hit[0] is not None and abs(hit[0][axis]-expected)<.005
    inlet_results.append({'wall_coordinate_mm':hit[0][axis],'expected_mm':expected})
gaps=[]
for j in range(61):
    y=-107.5+215*j/60;p=Vector((0,y,199.5))
    hits=[tree.ray_cast(p,Vector((s,0,0)),15) for s in [-1,1]]
    assert all(h[0] is not None for h in hits)
    gap=sum(h[3] for h in hits);assert abs(gap-12)<.006,(y,gap)
    gaps.append(gap);assert tree.ray_cast(p,Vector((0,0,1)),2)[0] is None
width=sum(tree.ray_cast(Vector((0,0,199.5)),Vector((0,s,0)),120)[3] for s in [-1,1]);assert abs(width-216)<.006
wall_samples=[]
for y in [-100,-50,0,50,100]:
    for s in [-1,1]:
        outer_hit=tree.ray_cast(Vector((s*20,y,199.5)),Vector((-s,0,0)),20)
        inner_hit=tree.ray_cast(Vector((0,y,199.5)),Vector((s,0,0)),15)
        value=abs(outer_hit[0].x-inner_hit[0].x);assert abs(value-2)<.006
        wall_samples.append(value)
for su in [-1,1]:
    for sv in [-1,1]:
        points=[]
        for j in range(1001):
            z=H*j/1000;w,d,r=section(z);points.append(Vector(local_to_global(su*.3*w,sv*.3*d,z)))
        for a,b in zip(points,points[1:]):
            delta=b-a;assert tree.ray_cast(a,delta.normalized(),delta.length)[0] is None,('path blocked',a,b)
        assert tree.ray_cast(points[-1],Vector((0,0,1)),2)[0] is None

samples=[net_area(j/50) for j in range(10001)]
minimum=min(samples,key=lambda s:s['net_air_area_mm2']);assert minimum['net_air_area_mm2']>=2592-1e-7
max_gross_increase=max(b['gross_area_mm2']-a['gross_area_mm2'] for a,b in zip(samples,samples[1:]));assert max_gross_increase<1e-7
clearance=min(s['v_depth_mm']/2-s['core_v_radius_mm'] for s in samples if s['core_u_radius_mm']>0);assert clearance>2
overhang=[]
for p in body.data.polygons:
    if p.center.z>3.05 and p.normal.z<0 and p.area>1e-7:
        angle=math.degrees(math.asin(min(1,-p.normal.z)))
        if angle>45.1:overhang.append({'angle_deg':angle,'area_mm2':p.area})
body.name=NAME;body.data.name=NAME+'_Mesh'
body['來源版本']=str(SOURCE);body['出口方向']='入口XY82x88；出口XY12x216；長邊X轉Y，氣流+Z直通'
body['尺寸_XYZ_mm']=[118,220,200];body['出口淨尺寸_mm']=[216,12];body['原法蘭及12孔']='保持原X/Y孔位，偏置X+2mm'
body['構造']='單件；底面起印薄十字片；尖鼻核心配合長縫轉90度；最後56mm無分隔'
body['列印']='mm100%，法蘭朝下；未切片或實印';body['限制']='無CFD、壓損、風量及回流改善驗證'
for p in body.data.polygons:p.use_smooth=True;p.material_index=0
if hasattr(body.data,'set_sharp_from_angle'):body.data.set_sharp_from_angle(angle=math.radians(35))
activate(body)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            v=area.spaces.active;v.region_3d.view_location=(0,0,100);v.region_3d.view_distance=420
            v.region_3d.view_rotation=Vector((-1.8,-1.3,.8)).to_track_quat('Z','Y');v.clip_end=10000
expected=geohash(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));export_stl(body)
bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False,use_scripts=False)
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(objects)==1 and geohash(objects[0])==expected
for p,h in protected.items():assert sha(p)==h
report={'date':'2026-11-05','units':'mm','source_file':str(SOURCE),'source_sha256':sha(SOURCE),'source_stl':str(SOURCE_STL),'source_stl_sha256':sha(SOURCE_STL),
    'reported_source_test':{'version':'200mm 216x4mm pointed-core single part','observation':'User reported severe reverse flow at blower intake','new_12mm_version_tested':False},
    'bounds_mm':bb,'mesh':stats,'empty_shell_mesh':shell_stats,
    'coordinate_system':{'fixed_flange_X_width_mm':118,'fixed_flange_Y_depth_mm':120,'inlet_global_XY_mm':[82,88],'outlet_global_XY_mm':[12,216],
        'old_outlet_long_axis':'X','new_outlet_long_axis':'Y','long_axis_rotation_deg':90,'flow_axis':'+Z, unchanged','local_to_global':'X=-V,Y=U,Z=Z'},
    'flange':{'size_XYZ_mm':[118,120,3],'center_XY_mm':[2,0],'outer_corner_radius_mm':4,'reference_surface_sample_count':len(flange_errors),'maximum_reference_error_mm':max(flange_errors)},
    'mounting_holes':hole_results,'inlet_checks':inlet_results,'outlet':{'long_width_mm':width,'gap_mm':12,'area_mm2':2592,'gap_sample_count':61,'gap_sample_range_mm':[min(gaps),max(gaps)],'gap_sampling_axis':'Y','gap_measurement_axis':'X','wall_thickness_sample_range_mm':[min(wall_samples),max(wall_samples)]},
    'geometry':{'neck_mm':12,'transition_mm':176,'outlet_straight_mm':12,'profile_U':'88+128q','profile_V':'82-120q+50q^2','corner_radius':'3(1-q)',
        'core_start_Z_mm':12,'core_peak_Z_mm':58,'core_peak_global_XY_mm':[42,36],'core_end_global_XY_Z_mm':[110,126],
        'long_vane_plane':'X=0','long_vane_end_Z_mm':144,'short_vane_plane':'Y=0','short_vane_end_Z_mm':134,'vane_bed_main_tail_thickness_mm':[.8,2,.8],'unpartitioned_outlet_length_mm':56},
    'minimum_sampled_net_area':minimum,'cross_section_sample_count':len(samples),'cross_sections':samples,
    'minimum_core_short_direction_clearance_mm':clearance,'gross_area_max_increment_mm2':max_gross_increase,'four_surrounding_geometric_paths_clear':True,
    'above_flange_downfacing_triangles_over_45deg':len(overhang),'above_flange_overhang_area_mm2':sum(p['area_mm2'] for p in overhang),
    'stl_file':STL.name,'stl_sha256':sha(STL),'blend_file':BLEND.name,'blend_sha256':sha(BLEND),'saved_blend_reopened_same_geometry':True,
    'all_sources_unchanged':True,'CFD':False,'slicer_tested':False,'physically_printed':False,'backflow_improvement_validated':False,
    'comparison_note':'Both slot gap and long-axis orientation/profile changed; observed differences cannot be attributed only to gap'}
(HERE/'尺寸與方向檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('HORIZONTAL_12MM_NOZZLE_DONE',json.dumps({'bounds':bb,'triangles':stats['triangles'],'outlet':report['outlet'],'core_clearance_mm':clearance,'overhangs':len(overhang)}),flush=True)
