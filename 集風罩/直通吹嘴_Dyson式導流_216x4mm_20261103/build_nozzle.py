"""Build a new, printable, patent-inspired rectangular-blower nozzle.

The existing project files are read-only. Dimensions not specified in the patent
are design choices for this prototype, not measurements of a Dyson product.
Run with Blender in background mode. Numeric coordinates are millimetres.
"""
from pathlib import Path
from array import array
from collections import Counter
import bpy, bmesh, math, json, hashlib, struct
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = HERE.parent / '直通長型風刀測試版/直通風刀_216x4mm.blend'
NAME = '直通吹嘴_216x4mm_中央鴨嘴導流_單件'
STL = HERE / (NAME + '_mm.stl')
BLEND = HERE / (NAME + '.blend')
REPORT = HERE / '尺寸與列印幾何檢查.json'
H, W, GAP = 240.0, 216.0, 4.0
CORE_START_TAPER, CORE_END = 24.0, 140.0
CORE_RX, CORE_RY, CORE_TIP = 18.0, 21.0, 0.8
VANE_Y_END, VANE_X_END = 180.0, 170.0
VANE_THICKNESS, TRAILING_THICKNESS = 2.0, 0.8
WALL_OVERLAP = 0.8
DEPTH_B = 145.8048780487805
DEPTH_C = DEPTH_B - 88 + GAP
HOLES = [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),
         (-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t*t*t*(10+t*(-15+6*t))

def ease(t):
    t = max(0.0, min(1.0,t)); b = 0.2
    if t <= b:
        u=t/b; return b*(u**3-0.5*u**4)/(1-b)
    if t >= 1-b:
        u=(1-t)/b; return 1-b*(u**3-0.5*u**4)/(1-b)
    return (t-b/2)/(1-b)

def section(z):
    t=ease((z-12)/216)
    return 82+134*t, 88-DEPTH_B*t+DEPTH_C*t*t, 3*(1-t)

def radii(z):
    s=smooth((z-CORE_START_TAPER)/(CORE_END-CORE_START_TAPER))
    return CORE_RX+(CORE_TIP-CORE_RX)*s, CORE_RY+(CORE_TIP-CORE_RY)*s

def thickness(z,end):
    if z>end: return 0.0
    return VANE_THICKNESS+(TRAILING_THICKNESS-VANE_THICKNESS)*smooth((z-end+12)/12)

def create_loft(name, rings, materials, mat_index):
    n=len(rings[0]); verts=[tuple(p) for ring in rings for p in ring]
    faces=[]
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*n+i; b=j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    for mat in materials: mesh.materials.append(mat)
    for poly in mesh.polygons:poly.material_index=mat_index
    return obj

def material(name,color):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    node=mat.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*color,1)
    node.inputs['Roughness'].default_value=0.38
    return mat

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def boolean(target,tool,operation='UNION'):
    activate(target);mod=target.modifiers.new('一體實體合併','BOOLEAN');mod.operation=operation;mod.solver='MANIFOLD';mod.object=tool
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
    check=bmesh.new();check.from_mesh(target.data)
    print('BOOLEAN_EDGE_CHECK',sum(not e.is_manifold for e in check.edges),'faces',len(check.faces),flush=True)
    check.free()

def bounds(obj):
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
    return {'min':lo,'max':hi,'size':[hi[k]-lo[k] for k in range(3)]}

def solid_check(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    before=sum(not e.is_manifold for e in bm.edges)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True)
    todo=set(bm.verts);components=0
    while todo:
        components+=1;stack=[todo.pop()]
        while stack:
            for edge in stack.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in todo:todo.remove(vertex);stack.append(vertex)
    assert bad==0 and components==1 and volume>1000,(bad,components,volume,'before_cleanup',before)
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return {'nonmanifold_edges':bad,'material_components':components,'volume_mm3':volume,
            'vertices':len(obj.data.vertices),'triangles':len(obj.data.polygons)}

def geohash(obj):
    coords=array('f',[0])*(len(obj.data.vertices)*3);obj.data.vertices.foreach_get('co',coords)
    loops=array('i',[0])*len(obj.data.loops);obj.data.loops.foreach_get('vertex_index',loops)
    return hashlib.sha256(coords.tobytes()+loops.tobytes()).hexdigest()

def tree_for(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True)

def export_stl(obj):
    obj.data.calc_loop_triangles()
    with STL.open('wb') as f:
        f.write(b'Rectangular blower nozzle, duckbill core, mm, prototype'.ljust(80,b' '))
        f.write(struct.pack('<I',len(obj.data.loop_triangles)))
        for triangle in obj.data.loop_triangles:
            a,b,c=[obj.matrix_world@obj.data.vertices[i].co for i in triangle.vertices]
            n=(b-a).cross(c-a).normalized();f.write(struct.pack('<12fH',*n,*a,*b,*c,0))

def net_area(z):
    w,d,r=section(z);ty=thickness(z,VANE_Y_END);tx=thickness(z,VANE_X_END)
    area=w*d-(4-math.pi)*r*r
    cross=w*ty+d*tx-tx*ty
    extra=0.0
    if z<=CORE_END:
        rx,ry=radii(z);a=tx/2;b=ty/2
        if a<rx and b<ry:
            top=ry*math.sqrt(max(0,1-(a/rx)**2))
            def primitive(y):
                t=max(0,min(1,y/ry))
                return rx*ry/2*(math.asin(t)+t*math.sqrt(max(0,1-t*t)))
            if top>b:extra=4*(primitive(top)-primitive(b)-a*(top-b))
    return {'z_mm':z,'outer_clear_area_mm2':area,'internal_material_mm2':cross+extra,'net_air_area_mm2':area-cross-extra}

source_hash=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=0.001;scene.unit_settings.length_unit='MILLIMETERS'
meshes=[o for o in scene.objects if o.type=='MESH'];assert len(meshes)==1
body=meshes[0];activate(body);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
body.name=NAME;body.data.name=NAME+'_Mesh'
base_volume=solid_check(body)['volume_mm3']
mats=[material('外殼_深灰',(.055,.07,.085)),material('中央鴨嘴核心_橘',(.9,.24,.035)),material('十字導流片_藍灰',(.13,.3,.38))]
body.data.materials.clear()
for mat in mats:body.data.materials.append(mat)
for poly in body.data.polygons:poly.material_index=0

# A grounded central fairing feeds the surrounding passages. Both crossed guide
# plates start at the flange plane, so there are no floating internal islands.
zs=[0,3,12,24]+[24+(CORE_END-24)*j/128 for j in range(1,129)]
rings=[]
for z in zs:
    rx,ry=radii(z)
    rings.append([(rx*math.cos(2*math.pi*j/128),ry*math.sin(2*math.pi*j/128),z) for j in range(128)])
core=create_loft('中央鴨嘴形導流核心',rings,mats,1)
solid_check(core)
print('CORE_CREATED',flush=True)
boolean(body,core)
print('CORE_UNIONED',flush=True)

for plane,end in [('Y',VANE_Y_END),('X',VANE_X_END)]:
    rings=[]
    zs=sorted(set([0.0,3.0,12.0]+[end*j/180 for j in range(1,181)]+[end-12,end]))
    for z in zs:
        w,d,_=section(z);t=thickness(z,end)
        if plane=='Y':
            a=w/2+WALL_OVERLAP;b=t/2
        else:
            a=t/2;b=d/2+WALL_OVERLAP
        rings.append([(-a,-b,z),(a,-b,z),(a,b,z),(-a,b,z)])
    vane=create_loft('十字導流片_'+plane,rings,mats,2)
    solid_check(vane);boolean(body,vane)
    print('VANE_UNIONED',plane,flush=True)

stats=solid_check(body);bb=bounds(body)
assert all(abs(a-b)<0.002 for a,b in zip(bb['size'],[220,120,240])),bb
assert stats['volume_mm3']>base_volume
activate(body)
body['進風接口外框_mm']=[82,88];body['出口淨尺寸_mm']=[216,4]
body['最大外形_mm']=[220,120,240];body['原法蘭_mm']=[118,120,3]
body['構造']='中央鴨嘴形核心與正交薄導流片一體固定；直通長縫出口'
body['參考']='US20170006991A1, figures 6 and 7; dimensions adapted, not a measured replica'
body['列印']='毫米100%，法蘭朝下；內部核心與導流片由平台起印'
body['限制']='幾何驗證原型；未做CFD、實印、風速或回流測試'
body['入口說明']='82x88為矩形接口外框；核心與導流片占用部分面積，詳見幾何報告'
for polygon in body.data.polygons:polygon.use_smooth=True
if hasattr(body.data,'set_sharp_from_angle'):body.data.set_sharp_from_angle(angle=math.radians(35))
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            view=area.spaces.active;view.region_3d.view_location=(0,0,120);view.region_3d.view_distance=480
            view.region_3d.view_rotation=Vector((1.3,-1.8,.8)).to_track_quat('Z','Y');view.shading.type='MATERIAL';view.clip_end=10000
expected=geohash(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
export_stl(body)
bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False,use_scripts=False)
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');assert geohash(body)==expected
tree=tree_for(body)

gap_samples=[]
for j in range(61):
    x=-107.5+215*j/60;p=Vector((x,0,239.5))
    hits=[tree.ray_cast(p,Vector((0,s,0)),10) for s in [-1,1]]
    assert all(h[0] is not None for h in hits)
    gap=sum(h[3] for h in hits);assert abs(gap-GAP)<0.006,(x,gap)
    assert tree.ray_cast(p,Vector((0,0,1)),2)[0] is None
    gap_samples.append(gap)
end_hits=[tree.ray_cast(Vector((0,0,239.5)),Vector((s,0,0)),120) for s in [-1,1]]
assert all(h[0] is not None for h in end_hits)
net_width=sum(h[3] for h in end_hits);assert abs(net_width-W)<0.006

hole_results=[]
for dy,dz in HOLES:
    p=Vector((2+dz,dy,-1));assert tree.ray_cast(p,Vector((0,0,1)),5)[0] is None
    radius=3.2 if abs(dy)==51 and abs(dz)==50 else 2.2
    hits=[tree.ray_cast(Vector((2+dz,dy,1.5)),Vector((s,0,0)),10) for s in [-1,1]]
    diameter=sum(h[3] for h in hits);assert abs(diameter-2*radius)<0.03
    hole_results.append({'x_mm':2+dz,'y_mm':dy,'diameter_mm':diameter,'through':True})

# Check all four surrounding inlet passages through the entire nozzle. Rays are
# geometric clearance tests, not calculated streamlines or performance results.
path_count=0
for sx in [-1,1]:
    for sy in [-1,1]:
        points=[]
        for j in range(481):
            z=-0.5+(H+1)*j/480;zz=max(0,min(H,z));w,d,_=section(zz)
            x=sx*0.74*w/2;y=sy*0.74*d/2
            points.append(Vector((x,y,z)))
        for a,b in zip(points,points[1:]):
            delta=b-a
            assert tree.ray_cast(a,delta.normalized(),delta.length*0.9999)[0] is None,(sx,sy,list(a),list(b))
        path_count+=1

area_samples=[net_area(j/2) for j in range(481)]
minimum=min(area_samples,key=lambda r:r['net_air_area_mm2'])
assert minimum['net_air_area_mm2']>W*GAP-1.0,minimum

# Collect downward-facing surface statistics above the flange. Tiny fillets and
# local flat features are reported rather than represented as a support guarantee.
overhang_area=0.0;overhang_faces=0
for poly in body.data.polygons:
    if poly.center.z>3.05 and poly.normal.z < -math.sin(math.radians(45.1)):
        overhang_area+=poly.area;overhang_faces+=1

assert sha(SOURCE)==source_hash
report={'date':'2026-11-03','file':str(STL),'blend':str(BLEND),'units':'mm','bounds_mm':bb,
        'mesh':stats,'source_file':str(SOURCE),'source_sha256':source_hash,'source_unchanged':True,
        'saved_blend_reopened_and_same_geometry':True,'net_outlet_mm':[net_width,GAP],
        'outlet_gap_sample_range_mm':[min(gap_samples),max(gap_samples)],'outlet_sample_count':len(gap_samples),
        'all_sampled_upward_exit_paths_clear':True,'all_four_surrounding_full_paths_clear':True,
        'geometric_path_count':path_count,'mounting_holes':hole_results,'central_inlet_core_present':True,
        'rectangular_interface_envelope_mm':[82,88],'inlet_air_area_mm2_estimate':net_area(0)['net_air_area_mm2'],
        'inlet_free_area_fraction_estimate':net_area(0)['net_air_area_mm2']/net_area(0)['outer_clear_area_mm2'],
        'sampled_minimum_air_area_mm2_estimate':minimum,'cross_sections':area_samples,
        'core_parameters_mm':{'base_width':36,'base_depth':42,'taper_starts':24,'end':140,'tip_diameter':1.6},
        'crossed_vanes_mm':{'nominal_thickness':2,'trailing_thickness':.8,'wide_plate_end':180,'depth_plate_end':170},
        'all_internal_material_starts_at_build_plate':True,'nominal_housing_wall_mm':2,
        'downward_faces_over_45deg_above_flange':overhang_faces,'corresponding_area_mm2':overhang_area,
        'reference':'https://patents.google.com/patent/US20170006991A1/en',
        'reference_scope':'central tapered duckbill and crossed guide vanes; dimensions and rectangular coupling are this prototype',
        'CFD_executed':False,'physical_print_validated':False,'performance_validated':False,
        'stl_sha256':sha(STL),'blend_sha256':sha(BLEND)}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BUILD_AND_GEOMETRY_CHECKS_COMPLETE',json.dumps({k:report[k] for k in ['bounds_mm','mesh','outlet_gap_sample_range_mm','inlet_air_area_mm2_estimate','downward_faces_over_45deg_above_flange','corresponding_area_mm2']},ensure_ascii=False),flush=True)
