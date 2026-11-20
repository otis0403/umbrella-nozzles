"""Create a separate compact rectangular prototype. Source models are read-only.

Geometry helpers are parsed from the previous generator without executing its
top-level code. Exported STL files and the assembly blend are self-contained.
"""
from pathlib import Path
from array import array
from collections import Counter
import bpy,bmesh,math,json,hashlib,struct,ast,sys
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path.insert(0,str(HERE))
from flow_geometry import section,core_radii,vane_thickness,net_area,smooth
H=200.
SOURCE=HERE.parent/'直通長型風刀測試版/直通風刀_216x4mm.blend'
HELPERS=HERE.parent/'直通吹嘴_Dyson式導流_216x4mm_20261103/build_nozzle.py'
selected={'sha','create_loft','activate','boolean','bounds','solid_check','geohash','tree_for','export_stl'}
nodes=ast.parse(HELPERS.read_text(encoding='utf-8')).body
exec(compile(ast.Module(body=[n for n in nodes if isinstance(n,ast.FunctionDef) and n.name in selected],type_ignores=[]),str(HELPERS),'exec'),globals())
source_sha=sha(SOURCE);helpers_sha=sha(HELPERS)

def material(name,color):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    node=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out=next((n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node.outputs[0],out.inputs[0])
    node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=.38
    return mat

def make_box(name,low,high):
    return create_loft(name,[[(-300,-300,low),(300,-300,low),(300,300,low),(-300,300,low)],
        [(-300,-300,high),(300,-300,high),(300,300,high),(-300,300,high)]],mats,0)

def split_box(side):
    yl,yh=(-200,0) if side==-1 else (0,200)
    return create_loft('合殼切分',[[(-200,yl,z),(200,yl,z),(200,yh,z),(-200,yh,z)] for z in [-1,H+1]],mats,0)

def export_part(obj,name,side):
    # Keep the saved assembly in its design coordinates; rotate only the STL.
    # An exact axis permutation avoids float32 rotation/translation rounding
    # that can collapse tiny, valid CSG facets in a binary STL.
    coords=[Vector((v.co.x,-side*v.co.z,side*v.co.y)) for v in obj.data.vertices]
    lo=[min(p[k] for p in coords) for k in range(3)];hi=[max(p[k] for p in coords) for k in range(3)]
    obj.data.calc_loop_triangles();path=HERE/(name+'_mm.stl')
    with path.open('wb') as f:
        f.write(b'Compact rectangular guided nozzle 216x4, split face down, mm'.ljust(80,b' '))
        f.write(struct.pack('<I',len(obj.data.loop_triangles)))
        for t in obj.data.loop_triangles:
            a,b,c=[coords[i] for i in t.vertices];n=(b-a).cross(c-a).normalized()
            f.write(struct.pack('<12fH',*n,*a,*b,*c,0))
    return {'file':path.name,'sha256':sha(path),'print_size_mm':[hi[k]-lo[k] for k in range(3)],'rotation_X_degrees':side*90,'minimum_print_Z_mm':0}

bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
body=next(o for o in scene.objects if o.type=='MESH')
for o in list(scene.objects):
    if o!=body:bpy.data.objects.remove(o,do_unlink=True)
activate(body);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for v in body.data.vertices:
    z=v.co.z
    if z>228:v.co.z=H-12+(z-228)
    elif z>12:v.co.z=12+(z-12)*(H-24)/216
body.data.update();body.name='方形緊湊_組裝母體'
mats=[material('方形外殼_石墨灰',(.075,.105,.13)),material('導流鼻_預覽橘',(.95,.27,.035)),material('導流片_預覽藍',(.12,.35,.45))]
body.data.materials.clear()
for mat in mats:body.data.materials.append(mat)
for p in body.data.polygons:p.material_index=0
solid_check(body)

rings=[]
for z in sorted(set([12.,58.,110.,126.]+[12+114*j/160 for j in range(161)])):
    rx,ry=core_radii(z)
    rings.append([(rx*math.cos(2*math.pi*k/128),ry*math.sin(2*math.pi*k/128),z) for k in range(128)])
core=create_loft('中央尖鼻與收尖核心',rings,mats,1)
boolean(body,core)
for axis,end in [('Y',144.),('X',134.)]:
    rings=[]
    for z in sorted(set([12.,22.,end-12,end]+[12+(end-12)*j/120 for j in range(121)])):
        w,d,r=section(z);t=vane_thickness(z,end)
        if axis=='Y':a=w/2+.8;b=t/2
        else:a=t/2;b=d/2+.8
        rings.append([(-a,-b,z),(a,-b,z),(a,b,z),(-a,b,z)])
    boolean(body,create_loft('十字薄導流片_'+axis,rings,mats,2))

# Tapered ear roots follow the outside wall instead of intruding into the duct.
ears=[]
for zc in [45.,118.]:
    for side in [-1,1]:
        rings=[]
        for j in range(9):
            z=zc-6+12*j/8;w,d,r=section(z);ox=w/2+2
            low,high=ox-.8,ox+14
            if side==-1:low,high=-high,-low
            rings.append([(low,-7,z),(high,-7,z),(high,7,z),(low,7,z)])
        boolean(body,create_loft('合殼螺絲耳',rings,mats,0))
        xc=side*(section(zc)[0]/2+2+7)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=1.7,depth=20,location=(xc,0,zc),rotation=(math.pi/2,0,0))
        boolean(body,bpy.context.object,'DIFFERENCE')
        ears.append({'x_mm':xc,'z_mm':zc,'hole_diameter_mm':3.4,'axis':'Y'})
whole_stats=solid_check(body);whole_bounds=bounds(body)
assert all(abs(a-b)<.002 for a,b in zip(whole_bounds['size'],[220,120,200])),whole_bounds
tree=tree_for(body)

gaps=[]
for j in range(61):
    x=-107.5+215*j/60;p=Vector((x,0,H-.5))
    hits=[tree.ray_cast(p,Vector((0,s,0)),10) for s in [-1,1]]
    assert all(h[0] is not None for h in hits)
    gap=sum(h[3] for h in hits);assert abs(gap-4)<.006,(x,gap)
    assert tree.ray_cast(p,Vector((0,0,1)),2)[0] is None
    gaps.append(gap)
width_hits=[tree.ray_cast(Vector((0,0,H-.5)),Vector((s,0,0)),120) for s in [-1,1]]
assert abs(sum(h[3] for h in width_hits)-216)<.006
assert tree.ray_cast(Vector((0,0,-1)),Vector((0,0,1)),12)[0] is None
hole_results=[]
holes=[(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]
for dy,dz in holes:
    x,y=2+dz,dy
    assert tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),5)[0] is None
    hits=[tree.ray_cast(Vector((x,y,1.5)),Vector((s,0,0)),10) for s in [-1,1]]
    diameter=sum(h[3] for h in hits);expected=6.4 if abs(dy)==51 and abs(dz)==50 else 4.4
    assert abs(diameter-expected)<.03
    hole_results.append({'x_mm':x,'y_mm':y,'diameter_mm':diameter})
for sx in [-1,1]:
    for sy in [-1,1]:
        points=[]
        for j in range(1001):
            z=H*j/1000;w,d,r=section(z);points.append(Vector((sx*.3*w,sy*.3*d,z)))
        for a,b in zip(points,points[1:]):
            delta=b-a
            assert tree.ray_cast(a,delta.normalized(),delta.length)[0] is None,('path blocked',a,b)
        assert tree.ray_cast(points[-1],Vector((0,0,1)),2)[0] is None
print('OUTLET_INLET_AND_FOUR_PATHS_VERIFIED',flush=True)

parts=[];records=[]
for side,name in [(-1,'01_方形緊湊吹嘴_A半_切面朝下'),(1,'02_方形緊湊吹嘴_B半_切面朝下')]:
    obj=body.copy();obj.data=body.data.copy();scene.collection.objects.link(obj);obj.name=name
    boolean(obj,split_box(side),'INTERSECT');stats=solid_check(obj)
    rec=export_part(obj,name,side);rec['mesh']=stats;rec['assembly_bounds_mm']=bounds(obj);records.append(rec);parts.append(obj)
    obj['列印單位']='mm 100%';obj['STL姿態']='已旋轉為合殼面朝下'
    obj['出口淨尺寸_mm']=[216,4];obj['組裝尺寸_mm']=[220,120,200]
    obj['內部']='尖鼻、收尖核心與十字薄片，入口保持開放，最後56 mm無分隔'
    obj['性能']='未做CFD、風速或實印驗證'
    obj.data.materials.clear();obj.data.materials.append(mats[0])
    for p in obj.data.polygons:p.material_index=0;p.use_smooth=True
    if hasattr(obj.data,'set_sharp_from_angle'):obj.data.set_sharp_from_angle(angle=math.radians(35))
bpy.data.objects.remove(body,do_unlink=True)
activate(parts[0])
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            v=area.spaces.active;v.region_3d.view_location=(0,0,100);v.region_3d.view_distance=420
            v.region_3d.view_rotation=Vector((1.3,-1.8,.8)).to_track_quat('Z','Y');v.clip_end=10000
blend=HERE/'方形緊湊導流_216x4mm_200mm_組裝.blend'
hashes=[geohash(o) for o in parts]
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.wm.open_mainfile(filepath=str(blend),load_ui=False,use_scripts=False)
reopened=sorted((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:o.name)
assert len(reopened)==2 and [geohash(o) for o in reopened]==hashes
assert sha(SOURCE)==source_sha and sha(HELPERS)==helpers_sha
report={'date':'2026-11-03','units':'mm','assembly_bounds_mm':whole_bounds,'whole_assembly_mesh':whole_stats,
    'parts':records,'outlet_mm':[216,4],'outlet_gap_sample_range_mm':[min(gaps),max(gaps)],'outlet_gap_sample_count':61,
    'input_mm':[82,88],'input_center_clear_through_neck':True,'four_surrounding_geometric_paths_clear':True,
    'original_flange_holes':hole_results,'assembly_fasteners':ears,'saved_blend_reopened_same_geometry':True,
    'core_parameters_mm':{'start':12,'peak':58,'max_diameter':36,'end_x':126,'end_y':110},
    'vanes':{'start_Z_mm':12,'end_Z_mm':[144,134],'thickness_mm':2,'leading_and_trailing_thickness_mm':.8},
    'source_file':str(SOURCE),'source_sha256':source_sha,'helpers_sha256':helpers_sha,'sources_unchanged':True,
    'blend_file':blend.name,'blend_sha256':sha(blend),'CFD_or_flow_validated':False,'physical_print_tested':False}
(HERE/'模型幾何檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('COMPACT_MODEL_BUILT',json.dumps({'bounds':whole_bounds,'print_sizes':[r['print_size_mm'] for r in records]}),flush=True)
