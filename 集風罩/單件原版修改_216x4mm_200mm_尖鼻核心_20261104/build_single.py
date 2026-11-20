"""Revise the uploaded design using its matching original parametric shell.

Verify that shell against the uploaded STL, then rebuild its inner features.
The new support vanes start at Z=0, and the small nose grows inside their
intersection, keeping one printable body. All source files remain read-only.
"""
from pathlib import Path
from array import array
from collections import Counter
import ast,sys,math,json,struct,hashlib,bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
sys.path.insert(0,str(HERE))
from geometry import H,smooth,section,core_radii,thickness,net_area
UPLOAD=Path(r'C:\Users\otiso\Downloads\直通吹嘴_216x4mm_中央鴨嘴導流_單件_mm.stl')
SHELL_SOURCE=HERE.parent/'直通長型風刀測試版/直通風刀_216x4mm.blend'
HELPERS=HERE.parent/'直通吹嘴_Dyson式導流_216x4mm_20261103/build_nozzle.py'
NAME='直通吹嘴_216x4mm_200mm_尖鼻核心_單件'
STL=HERE/(NAME+'_mm.stl');BLEND=HERE/(NAME+'.blend')
selected={'sha','create_loft','activate','boolean','bounds','solid_check','geohash','tree_for','export_stl'}
nodes=ast.parse(HELPERS.read_text(encoding='utf-8')).body
exec(compile(ast.Module(body=[n for n in nodes if isinstance(n,ast.FunctionDef) and n.name in selected],type_ignores=[]),str(HELPERS),'exec'),globals())
source_sha=sha(UPLOAD);shell_sha=sha(SHELL_SOURCE);helper_sha=sha(HELPERS)
assert source_sha=='2032a4a96ff48400c4d8e199edcd7ce9230432787faa8cc881786c829bbfd02a'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'

# Import exact binary STL coordinates, welding only identical coordinates.
blob=UPLOAD.read_bytes();nt=struct.unpack_from('<I',blob,80)[0];assert len(blob)==84+nt*50
verts=[];ids={};faces=[]
for row in struct.iter_unpack('<12fH',blob[84:]):
    face=[]
    for k in [3,6,9]:
        p=tuple(row[k:k+3])
        if p not in ids:ids[p]=len(verts);verts.append(p)
        face.append(ids[p])
    faces.append(face)
mesh=bpy.data.meshes.new(NAME+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
body=bpy.data.objects.new(NAME,mesh);scene.collection.objects.link(body)
original_stats=solid_check(body);original_bounds=bounds(body)
original_tree=tree_for(body)

with bpy.data.libraries.load(str(SHELL_SOURCE),link=False) as (available,loaded):loaded.objects=list(available.objects)
refs=[]
for obj in loaded.objects:
    if obj is not None and obj.type=='MESH':scene.collection.objects.link(obj);refs.append(obj)
assert len(refs)==1
reference=refs[0];activate(reference);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
reference_stats=solid_check(reference)
reference_tree=tree_for(reference)
reference_errors=[]
for z in [1.5,6,12,24,48,72,96,120,144,168,192,216,230,239.5]:
    for axis in [0,1]:
        for s in [-1,1]:
            p=[0.,0.,z];p[axis]=s*250;direction=[0.,0.,0.];direction[axis]=-s
            a=reference_tree.ray_cast(Vector(p),Vector(direction),300)
            b=original_tree.ray_cast(Vector(p),Vector(direction),300)
            assert a[0] is not None and b[0] is not None
            error=abs(a[0][axis]-b[0][axis]);assert error<.005
            reference_errors.append(error)
# STL is a merged triangle body, so use the matching original CAD shell for
# the feature edit. This avoids coplanar Boolean slivers; exterior is audited
# against the uploaded STL both before and after the length change.
bpy.data.objects.remove(body,do_unlink=True)
body=reference;body.name=NAME
print('UPLOADED_EXTERIOR_MATCHES_ORIGINAL_CAD_SHELL',flush=True)

# Keep the original 12 mm inlet neck, 3 mm flange and 12 mm outlet lip;
# compress only the 216 mm transition to 176 mm.
for v in body.data.vertices:
    z=v.co.z
    if z>228:v.co.z=188+(z-228)
    elif z>12:v.co.z=12+(z-12)*176/216
body.data.update();solid_check(body)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(n.outputs[0],out.inputs[0]);n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.38
    return m
mats=[material('外殼_石墨灰',(.065,.09,.115)),material('尖鼻核心_預覽橘',(.95,.27,.035)),material('十字支撐導流片_預覽藍',(.10,.34,.45))]
body.data.materials.clear()
for m in mats:body.data.materials.append(m)
for p in body.data.polygons:p.material_index=0

# Grounded support vanes precede the nose. No floating internal insert.
for axis,end in [('Y',144.),('X',134.)]:
    rings=[]
    for z in sorted(set([0.,3.,12.,end-12,end]+[end*j/140 for j in range(141)])):
        w,d,r=section(z);t=thickness(z,end)
        if axis=='Y':a=w/2+.8;b=t/2
        else:a=t/2;b=d/2+.8
        rings.append([(-a,-b,z),(a,-b,z),(a,b,z),(-a,b,z)])
    boolean(body,create_loft('底面起印的十字支撐_'+axis,rings,mats,2))
    solid_check(body)
rings=[]
for z in sorted(set([12.,58.,110.,126.]+[12+114*j/152 for j in range(153)])):
    rx,ry=core_radii(z)
    rings.append([(rx*math.cos(2*math.pi*j/128),ry*math.sin(2*math.pi*j/128),z) for j in range(128)])
boolean(body,create_loft('尖鼻迎風與鴨嘴收尖核心',rings,mats,1))
stats=solid_check(body);bb=bounds(body)
assert all(abs(a-b)<.002 for a,b in zip(bb['size'],[220,120,200])),bb
tree=tree_for(body)

external=[]
for z in [1.5,6,12,18,30,45,58,80,100,126,144,160,180,190,199.5]:
    zo=z if z<=12 else (228+z-188 if z>=188 else 12+(z-12)*216/176)
    for axis in [0,1]:
        for s in [-1,1]:
            p=[0.,0.,z];p[axis]=s*250;direction=[0.,0.,0.];direction[axis]=-s
            po=list(p);po[2]=zo
            a=tree.ray_cast(Vector(p),Vector(direction),300);b=original_tree.ray_cast(Vector(po),Vector(direction),300)
            assert a[0] is not None and b[0] is not None
            error=abs(a[0][axis]-b[0][axis]);assert error<.005,(z,axis,s,error)
            external.append(error)
gaps=[]
for j in range(61):
    x=-107.5+215*j/60;p=Vector((x,0,199.5))
    hits=[tree.ray_cast(p,Vector((0,s,0)),10) for s in [-1,1]]
    assert all(h[0] is not None for h in hits)
    gap=sum(h[3] for h in hits);assert abs(gap-4)<.006,(x,gap)
    gaps.append(gap);assert tree.ray_cast(p,Vector((0,0,1)),2)[0] is None
width=sum(tree.ray_cast(Vector((0,0,199.5)),Vector((s,0,0)),120)[3] for s in [-1,1]);assert abs(width-216)<.006
holes=[(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]
hole_results=[]
for dy,dz in holes:
    x,y=2+dz,dy;assert tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),5)[0] is None
    diameter=sum(tree.ray_cast(Vector((x,y,1.5)),Vector((s,0,0)),10)[3] for s in [-1,1])
    assert abs(diameter-(6.4 if abs(dy)==51 and abs(dz)==50 else 4.4))<.03
    hole_results.append({'x_mm':x,'y_mm':y,'diameter_mm':diameter})
for sx in [-1,1]:
    for sy in [-1,1]:
        points=[]
        for j in range(1001):
            z=H*j/1000;w,d,r=section(z);points.append(Vector((sx*.3*w,sy*.3*d,z)))
        for a,b in zip(points,points[1:]):
            delta=b-a;assert tree.ray_cast(a,delta.normalized(),delta.length)[0] is None,('path blocked',a,b)
        assert tree.ray_cast(points[-1],Vector((0,0,1)),2)[0] is None

samples=[net_area(H*j/2000) for j in range(2001)]
minimum=min(samples,key=lambda x:x['net_air_area_mm2']);assert minimum['net_air_area_mm2']>=864-1e-7
core_clearance=min(p['depth_mm']/2-p['core_ry_mm'] for p in samples if p['core_rx_mm']>0);assert core_clearance>2
old_area=5836.681860774906
inlet_area=samples[0]['net_air_area_mm2'];gross_inlet=82*88-(4-math.pi)*9
overhang=[]
for p in body.data.polygons:
    if p.center.z>3.05 and p.normal.z<0 and p.area>1e-7:
        angle=math.degrees(math.asin(min(1,-p.normal.z)))
        if angle>45.1:overhang.append({'angle':angle,'area_mm2':p.area})
body.name=NAME;body.data.name=NAME+'_Mesh'
body['來源_STL']=str(UPLOAD);body['來源_SHA256']=source_sha
body['尺寸_mm']=[220,120,200];body['出口淨尺寸_mm']=[216,4]
body['構造']='單件；底面起印薄十字片；Z12起尖鼻，Z58達36x42後收尖；最後56mm無分隔'
body['列印']='mm 100%，法蘭朝下；未切片或實印'
body['限制']='無CFD、壓損、風量及回流驗證'
for p in body.data.polygons:p.use_smooth=True;p.material_index=0
if hasattr(body.data,'set_sharp_from_angle'):body.data.set_sharp_from_angle(angle=math.radians(35))
activate(body)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            v=area.spaces.active;v.region_3d.view_location=(0,0,100);v.region_3d.view_distance=420
            v.region_3d.view_rotation=Vector((1.3,-1.8,.8)).to_track_quat('Z','Y');v.clip_end=10000
expected=geohash(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));export_stl(body)
bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False,use_scripts=False)
objs=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(objs)==1 and geohash(objs[0])==expected
assert sha(UPLOAD)==source_sha and sha(SHELL_SOURCE)==shell_sha and sha(HELPERS)==helper_sha
report={'date':'2026-11-04','units':'mm','uploaded_source':str(UPLOAD),'uploaded_sha256':source_sha,'uploaded_source_unchanged':True,
    'source_bounds_mm':original_bounds,'source_mesh':original_stats,
    'shell_reconstruction':'Matching original parametric CAD shell; exterior verified against uploaded STL, then inner features rebuilt',
    'original_shell_comparison_sample_count':len(reference_errors),'original_shell_maximum_surface_error_mm':max(reference_errors),
    'shell_reference_file':str(SHELL_SOURCE),'shell_reference_sha256':shell_sha,'bounds_mm':bb,'mesh':stats,
    'external_surface_sample_count':len(external),'maximum_external_preservation_error_mm':max(external),
    'height_change_note':'Only original Z12..228 transition compressed from216 to176 mm; original3mm flange,12mm neck and12mm outlet lip kept',
    'outlet_mm':[width,4],'outlet_gap_sample_range_mm':[min(gaps),max(gaps)],'outlet_gap_sample_count':61,
    'original_mounting_holes':hole_results,'four_surrounding_geometric_paths_clear':True,
    'core':{'nose_start_Z_mm':12,'max_section_Z_mm':58,'max_section_mm':[36,42],'tip_end_Z_mm':[126,110]},
    'support_vanes':{'start_Z_mm':0,'end_Z_mm':[144,134],'bed_thickness_mm':.8,'main_thickness_mm':2,'trailing_thickness_mm':.8,'unpartitioned_outlet_length_mm':56},
    'inlet':{'interface_mm':[82,88],'gross_area_mm2':gross_inlet,'free_area_estimate_mm2':inlet_area,'free_fraction':inlet_area/gross_inlet,
        'old_free_area_estimate_mm2':old_area,'area_increase_fraction':inlet_area/old_area-1,'note':'Geometric inlet-area comparison, not an airflow increase prediction'},
    'minimum_sampled_net_area':minimum,'cross_section_samples':samples,'minimum_core_front_back_clearance_mm':core_clearance,
    'grounded_single_component':True,'above_flange_downfacing_triangles_over_45deg':len(overhang),
    'above_flange_overhang_area_mm2':sum(p['area_mm2'] for p in overhang),
    'stl_file':STL.name,'stl_sha256':sha(STL),'blend_file':BLEND.name,'blend_sha256':sha(BLEND),
    'saved_blend_reopened_same_geometry':True,'CFD':False,'physical_print_tested':False,'slicer_tested':False,'airflow_or_backflow_validated':False}
(HERE/'尺寸與修改檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SINGLE_REVISION_DONE',json.dumps({'bounds':bb,'inlet':report['inlet'],'minimum_core_clearance':core_clearance,'overhangs':len(overhang),'triangles':stats['triangles']}),flush=True)
