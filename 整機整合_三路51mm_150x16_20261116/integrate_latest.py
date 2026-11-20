"""Integrate released flow parts into a separate complete machine model."""
import bpy, json, math, hashlib, itertools, struct, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
CASE=ROOT.parent
SOURCE=CASE/'完整模型.blend'
BASE_SPLITTER=CASE/'ThreeWay150_51mm_System_20261114/print/STL/splitter_H110_neck46_mm.stl'
SPLITTER=ROOT/'print/STL/splitter_center_neck_plus10_mm.stl'
NOZZLE=CASE/'Nozzle_FemaleSocket_51mm_150x16_20261114/print/STL/nozzle_150x16_female_ID55p4_H188_mm.stl'
DEST=ROOT/'完整模型_中央弧線_三路51mm_150x16.blend'
CHECKS=ROOT/'integration_checks.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(ob):
    h=hashlib.sha256()
    h.update(json.dumps([list(r) for r in ob.matrix_world]).encode())
    if ob.type=='MESH':
        for v in ob.data.vertices:
            h.update(struct.pack('<3f',*v.co))
        for p in ob.data.polygons:
            h.update(struct.pack('<I',len(p.vertices)))
            h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
            h.update(struct.pack('<I',p.material_index))
        h.update(json.dumps([m.name if m else None for m in ob.data.materials]).encode())
    h.update(json.dumps([(m.name,m.type) for m in ob.modifiers]).encode())
    return h.hexdigest()


def tree(ob):
    ob.data.calc_loop_triangles()
    return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],
        [tuple(t.vertices) for t in ob.data.loop_triangles],all_triangles=True)


def bounds(ob):
    pts=[ob.matrix_world@v.co for v in ob.data.vertices]
    return [[min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)]]


def material(name,color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    shader=m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.43
    return m


def import_mesh(path):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.stl_import(filepath=str(path),use_scene_unit=False)
    ob=bpy.context.object
    data=ob.data
    bpy.data.objects.remove(ob,do_unlink=True)
    return data


def port(k):
    a=math.radians(25*(k-1))
    d=Vector((math.sin(a),0,math.cos(a)))
    tip=Vector((60*(k-1),0,120 if k==1 else 98))
    return tip-25*d,d


def bezier(p0,p1,p2,p3,t):
    return p0*((1-t)**3)+p1*(3*(1-t)**2*t)+p2*(3*(1-t)*t*t)+p3*(t**3)


def curve_radius(p0,p1,p2,p3):
    radii=[]
    for i in range(121):
        t=i/120
        d=(p1-p0)*(3*(1-t)**2)+(p2-p1)*(6*(1-t)*t)+(p3-p2)*(3*t*t)
        dd=(p2-2*p1+p0)*(6*(1-t))+(p3-2*p2+p1)*(6*t)
        cross=d.cross(dd).length
        if cross>1e-8:
            radii.append(d.length**3/cross)
    return min(radii) if radii else 1e6


def hose_path(start,direction,end,up,shell):
    tip=start+2.5*direction
    entry=end-2.5*up
    distance=(entry-tip).length
    options=[]
    for a in [.2,.3,.4,.5,.6]:
        for b in [.2,.3,.4,.5,.6]:
            p1=tip+direction*(distance*a)
            p2=entry-up*(distance*b)
            curve=[bezier(tip,p1,p2,entry,i/160) for i in range(161)]
            radius=curve_radius(tip,p1,p2,entry)
            clearance=min(shell.find_nearest(p)[3] for p in curve[::4])
            path=[start,tip]+curve[1:-1]+[entry,end]
            length=sum((y-x).length for x,y in zip(path,path[1:]))
            score=(max(0,4.0-radius)*1000+max(0,2.83-clearance)*1000+length)
            options.append((score,path,radius,clearance))
    _,path,radius,clearance=min(options,key=lambda v:v[0])
    return path,radius,clearance


def tube(name,points,mat):
    rings=[]
    normal=None
    for i,p in enumerate(points):
        if i==0:
            tangent=(points[1]-p).normalized()
        elif i==len(points)-1:
            tangent=(p-points[i-1]).normalized()
        else:
            tangent=(points[i+1]-points[i-1]).normalized()
        if normal is None:
            normal=tangent.cross(Vector((0,1,0))).normalized()
        else:
            normal=(normal-tangent*normal.dot(tangent)).normalized()
        binormal=tangent.cross(normal).normalized()
        rings.append((p,normal,binormal))
    sides=48
    vertices=[]
    for radius in [2.73,2.55]:
        for p,n,b in rings:
            for j in range(sides):
                a=2*math.pi*j/sides
                vertices.append(p+radius*(math.cos(a)*n+math.sin(a)*b))
    faces=[]
    count=len(rings)
    layer=count*sides
    for k in range(2):
        offset=k*layer
        for i in range(count-1):
            for j in range(sides):
                q=(offset+i*sides+j,offset+i*sides+(j+1)%sides,
                   offset+(i+1)*sides+(j+1)%sides,offset+(i+1)*sides+j)
                faces.append(q if k==0 else tuple(reversed(q)))
    for j in range(sides):
        jn=(j+1)%sides
        faces.append((j,layer+j,layer+jn,jn))
        a=(count-1)*sides
        faces.append((a+j,a+jn,layer+a+jn,layer+a+j))
    mesh=bpy.data.meshes.new(name+'_ID51_OD54p6')
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    ob=bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob['hose_inside_diameter_mm']=51.0
    ob['hose_estimated_outside_diameter_mm']=54.6
    ob['routing_model']='smooth tube; corrugation and hose clamps omitted'
    ob['hose_centerline_length_mm']=10*sum((b-a).length for a,b in zip(points,points[1:]))
    return ob


def aim(ob,target):
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()


def render_views():
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED'
    scene.render.threads=4
    scene.render.resolution_x=1500
    scene.render.resolution_y=1100
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    scene.world=bpy.data.worlds.new('Assembly_Studio')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.74,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
    for loc,power,size in [((-100,-160,220),1500000,150),((120,-100,160),1000000,120),((0,80,200),1200000,100)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        light=bpy.context.object
        light.name='整機預覽燈'
        light.data.energy=power
        light.data.size=size
        aim(light,(0,0,60))
    cam=bpy.data.objects.get('Camera')
    scene.camera=cam
    cam.data.type='ORTHO'
    cam.data.clip_start=.05
    cam.data.clip_end=10000
    cam.location=(-170,-230,160)
    cam.data.ortho_scale=240
    aim(cam,(0,-1.5,62))
    scene.render.filepath=str(ROOT/'01_整機背面_最新三路配置.png')
    # Store a usable native camera without overwriting the source file.
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
    bpy.ops.render.render(write_still=True)
    cam.location=(0,-175,120)
    cam.data.ortho_scale=170
    aim(cam,(0,-6,42))
    bpy.data.objects['Cube'].hide_render=True
    scene.render.filepath=str(ROOT/'02_中央弧線_六吹口定位.png')
    bpy.ops.render.render(write_still=True)


def build():
    inputs={str(p):digest(p) for p in [SOURCE,BASE_SPLITTER,SPLITTER,NOZZLE]}
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    assert abs(scene.unit_settings.scale_length-.01)<1e-8
    unit_before=(scene.unit_settings.system,scene.unit_settings.scale_length,scene.unit_settings.length_unit)
    replacing={o.name for o in scene.objects if o.name.startswith(('三路分流接頭_','小型集風罩_','外購導風管_'))}
    preserved={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name not in replacing}
    shell=tree(bpy.data.objects['Cube'])
    splitter_mesh=import_mesh(SPLITTER)
    nozzle_mesh=import_mesh(NOZZLE)
    split_mat=material('新版三路接頭',(.07,.38,.43))
    nozzle_mat=material('新版150x16吹嘴',(.08,.48,.52))
    splitter_mesh.materials.clear()
    splitter_mesh.materials.append(split_mat)
    nozzle_mesh.materials.clear()
    nozzle_mesh.materials.append(nozzle_mat)
    hose_materials=[material('軟管_'+str(i),c) for i,c in enumerate([(.29,.55,.61),(.78,.54,.32),(.28,.56,.48)])]
    report={'source_files_sha256':inputs,'unit_scale':scene.unit_settings.scale_length,
            'shell_size_mm':[1400,500,1250],'blower_count':2,'splitter_count':2,'nozzle_count':6,
            'outlet_size_mm':[150,16],'socket_ID_mm':55.4,'hose_ID_mm':51,'hose_OD_estimate_mm':54.6,
            'outlet_layout':'symmetric along the existing middle line of the umbrella arc',
            'CFD_rerun':False,'physical_fit_verified':False,'nozzles':[],'hoses':[],'interface_checks':[]}
    nozzles=[]
    original_xy={}
    for side in ['右側','左側']:
        split=bpy.data.objects['三路分流接頭_'+side]
        original_matrix=split.matrix_world.copy()
        split.data=splitter_mesh
        split['source_STL']=str(SPLITTER)
        split['specification']='H110 side body, central neck +10mm, OD50/ID46, 25mm insertion, original 12-hole flange'
        assert max(abs(split.matrix_world[i][j]-original_matrix[i][j]) for i in range(4) for j in range(4))==0
        # Interface coordinates are in original millimetre part coordinates.
        local_tree=BVHTree.FromPolygons([v.co for v in splitter_mesh.vertices],
            [tuple(p.vertices) for p in splitter_mesh.polygons],all_triangles=True)
        inlet=[]
        for axis in [Vector((1,0,0)),Vector((0,1,0))]:
            inlet.append(sum(local_tree.ray_cast(Vector((0,0,1)),s*axis,100)[3] for s in [-1,1]))
        assert abs(inlet[0]-82)<.03 and abs(inlet[1]-88)<.03
        holes=json.loads((CASE/'ThreeWay150_51mm_System_20261114/cad/geometry_checks.json').read_text())['original_holes']
        assert all(local_tree.ray_cast(Vector((h['x'],h['y'],-1)),Vector((0,0,1)),5)[0] is None for h in holes)
        report['interface_checks'].append({'side':side,'inlet_mm':inlet,'holes_clear':len(holes),'flange_transform_matches_source':True})
        for index in [1,2,3]:
            ob=bpy.data.objects[f'小型集風罩_{side}_{index}']
            old=ob.matrix_world.copy()
            up=old.to_3x3().col[2].normalized()
            width=old.to_3x3().col[0].normalized()
            short=width.cross(up).normalized()
            outlet=Vector((old.translation.x,old.translation.y,max((old@v.co).z for v in ob.data.vertices)))
            original_xy[ob.name]=list(outlet)
            transform=Matrix.Identity(4)
            for col,axis in enumerate([short,width,up]):
                for row in range(3):
                    transform[row][col]=axis[row]*.1
            transform.translation=outlet-18.8*up
            ob.data=nozzle_mesh
            ob.matrix_world=transform
            ob['source_STL']=str(NOZZLE)
            ob['outlet_mm']='150 x 16'
            ob['socket_ID_mm']=55.4
            nozzles.append(ob)
    bpy.context.view_layer.update()
    # All mouths stay in one horizontal row, with a common installation clearance.
    selected_drop=None
    for drop in [0,.05,.1,.2,.3,.5,1,1.5,2]:
        for ob in nozzles:
            ob.location.z=original_xy[ob.name][2]-18.8-drop
        bpy.context.view_layer.update()
        if all(not tree(ob).overlap(shell) for ob in nozzles):
            selected_drop=drop
            break
    report['common_outlet_lowering_mm']=None if selected_drop is None else selected_drop*10
    if selected_drop is None:
        report['nozzle_shell_intersections']={o.name:len(tree(o).overlap(shell)) for o in nozzles}
        CHECKS.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        raise RuntimeError('Nozzle clearance requires review; build stopped')
    for ob in nozzles:
        report['nozzles'].append({'name':ob.name,'outlet_center_mm':list(10*(ob.matrix_world@Vector((0,0,188)))),
            'bounds_cm':bounds(ob),'shell_triangle_intersections':len(tree(ob).overlap(shell))})
    for side in ['右側','左側']:
        split=bpy.data.objects['三路分流接頭_'+side]
        group=[bpy.data.objects[f'小型集風罩_{side}_{i}'] for i in [1,2,3]]
        ports=[]
        for k in range(3):
            E,D=port(k)
            ports.append((split.matrix_world@E,(split.matrix_world.to_3x3()@D).normalized()))
        match=min(itertools.permutations(range(3)),key=lambda order:sum((ports[k][0]-group[order[k]].matrix_world.translation).length**2 for k in range(3)))
        for k,nozzle_index in enumerate(match):
            ob=group[nozzle_index]
            start,direction=ports[k]
            up=ob.matrix_world.to_3x3().col[2].normalized()
            end=ob.matrix_world@Vector((0,0,25))
            points,radius,clearance=hose_path(start,direction,end,up,shell)
            name=f'外購導風管_{side}_{nozzle_index+1}'
            old=bpy.data.objects.get(name)
            if old:
                bpy.data.objects.remove(old,do_unlink=True)
            hose=tube(name,points,hose_materials[nozzle_index])
            intersections=len(tree(hose).overlap(shell))
            report['hoses'].append({'name':name,'port_index':k,'nozzle':ob.name,
                'centerline_length_mm':hose['hose_centerline_length_mm'],'minimum_centerline_bend_radius_mm':radius*10,
                'sampled_centerline_shell_clearance_mm':clearance*10,'shell_triangle_intersections':intersections,
                'male_overlap_mm':25,'female_insertion_mm':25,'bend_radius_over_40mm':radius>=4})
    bpy.context.view_layer.update()
    report['splitter_shell_intersections']={o.name:len(tree(o).overlap(shell)) for o in scene.objects if o.name.startswith('三路分流接頭_')}
    report['untouched_mesh_count']=len(preserved)
    report['untouched_mesh_hashes']=preserved
    assert all(fingerprint(bpy.data.objects[n])==h for n,h in preserved.items())
    report['original_shell_blowers_clamp_meshes_preserved']=True
    assert (scene.unit_settings.system,scene.unit_settings.scale_length,scene.unit_settings.length_unit)==unit_before
    report['scene_units_preserved']=True
    report['source_files_unchanged']=all(digest(Path(p))==h for p,h in inputs.items())
    report['routing_is_cut_length_instruction']=False
    CHECKS.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('INTEGRATION_GEOMETRY',json.dumps({k:v for k,v in report.items() if k not in ['untouched_mesh_hashes','source_files_sha256']},ensure_ascii=False),flush=True)
    if any(h['shell_triangle_intersections'] or not h['bend_radius_over_40mm'] for h in report['hoses']):
        raise RuntimeError('Hose routing needs review; build stopped')
    if any(report['splitter_shell_intersections'].values()):
        raise RuntimeError('Splitter shell interference; build stopped')
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
    print('ASSEMBLY_BUILD_COMPLETE',flush=True)


def verify():
    report=json.loads(CHECKS.read_text(encoding='utf8'))
    bpy.ops.wm.open_mainfile(filepath=str(DEST))
    assert all(fingerprint(bpy.data.objects[n])==h for n,h in report['untouched_mesh_hashes'].items())
    assert abs(bpy.context.scene.unit_settings.scale_length-.01)<1e-8
    assert len([o for o in bpy.context.scene.objects if o.name.startswith('小型集風罩_')])==6
    assert len([o for o in bpy.context.scene.objects if o.name.startswith('三路分流接頭_')])==2
    assert len([o for o in bpy.context.scene.objects if o.name.startswith('外購導風管_')])==6
    symmetry=[]
    for i in [1,2,3]:
        a=bpy.data.objects[f'小型集風罩_右側_{i}'].matrix_world@Vector((0,0,188))
        b=bpy.data.objects[f'小型集風罩_左側_{i}'].matrix_world@Vector((0,0,188))
        error=max(abs(a.x+b.x),abs(a.y-b.y),abs(a.z-b.z))*10
        assert error<.01
        symmetry.append(error)
    heights=[(o.matrix_world@Vector((0,0,188))).z*10 for o in bpy.context.scene.objects if o.name.startswith('小型集風罩_')]
    assert max(heights)-min(heights)<.01
    # Independently remeasure the released nozzle after native reopen.
    ob=bpy.data.objects['小型集風罩_右側_1']
    local=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)
    gaps=[]
    for j in range(61):
        p=Vector((0,-74+148*j/60,187.9))
        gaps.append(sum(local.ray_cast(p,Vector((s,0,0)),50)[3] for s in [-1,1]))
    span=sum(local.ray_cast(Vector((0,0,187.9)),Vector((0,s,0)),100)[3] for s in [-1,1])
    socket=sum(local.ray_cast(Vector((0,0,12)),Vector((0,s,0)),60)[3] for s in [-1,1])
    assert max(abs(g-16) for g in gaps)<.03 and abs(span-150)<.03 and abs(socket-55.4)<.03
    assert all(digest(Path(p))==h for p,h in report['source_files_sha256'].items())
    result={'native_file_reopened':True,'unchanged_meshes_verified':report['untouched_mesh_count'],
        'original_inputs_sha256_verified':True,'symmetry_error_mm':symmetry,'outlet_heights_mm':heights,
        'gap_range_mm':[min(gaps),max(gaps)],'gap_samples':61,'outlet_span_mm':span,'socket_ID_mm':socket,
        'output_sha256':digest(DEST)}
    (ROOT/'native_reopen_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('INDEPENDENT_NATIVE_REOPEN_VERIFIED',json.dumps(result,ensure_ascii=False),flush=True)

mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'build'
if mode=='verify':
    verify()
else:
    build()



