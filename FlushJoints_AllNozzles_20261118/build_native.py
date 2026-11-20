import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'flush_checks.json').read_text(encoding='utf-8-sig'))
assert json.loads((ROOT/'nut_checks.json').read_text())['all_nuts_fit_reloaded_plastic']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
parts={r['id']:r for r in data['parts']};objects={};trees={};hw_objects=[];matrices={};checks=[]
def mat(name,color):
    o=bpy.data.materials.new(name);o.use_nodes=True
    o.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    o.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4
    return o
bodymat=mat('Continuous housing',(.055,.30,.37));tipmat=mat('Replaceable tip',(.9,.33,.07));lower=mat('Inlet',(.035,.16,.23));metal=mat('M3 hardware illustration',(.14,.18,.21))
def import_model(path,name,matrix,material,geometry=None):
    bpy.ops.wm.stl_import(filepath=str(path),use_scene_unit=False)
    ob=bpy.context.object;ob.name=name
    if geometry:ob.data.transform(geometry)
    ob.matrix_world=matrix;ob.data.materials.append(material)
    return ob
def span(tree,p,axis):
    hits=[tree.ray_cast(Vector(p),s*Vector(axis),1000) for s in [-1,1]]
    assert all(h[0] is not None for h in hits),(p,axis)
    return sum(h[3] for h in hits)
for group,xpos in zip(data['groups'],[-340,0,360]):
    key=group['id'];h=group['height_mm'];w=group['width_mm'];gap=group['gap_mm']
    matrix=Matrix(((0,1,0,xpos),(0,0,1,-h),(1,0,0,35.7),(0,0,0,1)));matrices[key]=matrix
    for name in group['parts']:
        row=parts[name];material=tipmat if '_tip_' in name else lower if name=='outer_inlet' else bodymat
        ob=import_model(row['STL'],name,matrix,material,Matrix(row['assembly_from_print']))
        ob['printable_part']=True;ob['group']=key;objects[name]=ob
        trees[name]=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)
    inlet=trees[group['parts'][0]];tip=trees[group['parts'][-1]]
    socket=span(inlet,(0,0,12),(0,1,0));bore=span(inlet,(0,0,25.1),(0,1,0))
    gaps=[span(tip,(0,-w/2+1+(w-2)*i/60,h-.1),(1,0,0)) for i in range(61)]
    width=span(tip,(0,0,h-.1),(0,1,0))
    assert abs(socket-55.4)<.03 and abs(bore-51)<.03
    assert max(abs(v-gap) for v in gaps)<.03 and abs(width-w)<.03
    assert tip.ray_cast(Vector((0,0,group['tip_visible_seam_Z_mm']-.1)),Vector((0,0,1)),55.2)[0] is None
    row={'id':key,'socket_ID_mm':socket,'main_bore_mm':bore,'gap61_range_mm':[min(gaps),max(gaps)],'width_mm':width}
    if key=='outer':
        guide_z=[]
        for y in [-8.030094,8.030094]:
            hit=trees['outer_guided_body'].ray_cast(Vector((0,y,54)),Vector((0,0,1)),5)
            assert hit[0] is not None and abs(hit[0].z-55)<.01;guide_z.append(hit[0].z-55)
        row['guide_leading_faces_print_Z_mm']=guide_z
        source_path=next(p for p in data['source_hashes_unchanged'] if 'W315' in p)
        source_ob=import_model(source_path,'Verification_source_only',Matrix.Identity(4),bodymat)
        source_tree=BVHTree.FromPolygons([v.co for v in source_ob.data.vertices],[tuple(p.vertices) for p in source_ob.data.polygons],all_triangles=True)
        guide_errors=[]
        for z in [55.1,70,100,150,200,250,300,331.9]:
            for side in [-1,1]:
                values=[]
                for tree in [source_tree,trees['outer_guided_body']]:
                    direction=Vector((0,side,0));hit=tree.ray_cast(Vector((0,0,z)),direction,200)
                    assert hit[0] is not None
                    outer_hit=tree.ray_cast(hit[0]+direction*4,-direction,8)
                    assert outer_hit[0] is not None
                    values.append((hit[0].y,outer_hit[0].y))
                guide_errors.extend(abs(values[1][k]-values[0][k]) for k in [0,1])
        assert max(guide_errors)<.02,guide_errors
        row['guide_surface_max_change_from_source_mm']=max(guide_errors)
        bpy.data.objects.remove(source_ob,do_unlink=True)
    checks.append(row)
    for joint in group['joints']:
        for i,hw in enumerate(joint['hardware']):
            for kind in ['screw','nut']:
                ob=import_model(hw[kind+'_envelope_STL'],f'{joint["id"]}_{kind}{i}',matrix,metal)
                ob['illustration_only']=True;ob['group']=key;ob['joint']=joint['id'];ob['hardware_kind']=kind;hw_objects.append(ob)
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.87,.91,.95,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.6;scene.world=world
for loc,power,size in [((200,-450,900),10000000,650),((-650,250,650),9000000,600),((700,500,700),11000000,600)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.size=size;aim(ob,(50,-150,35))
bpy.ops.object.camera_add(location=(450,1300,1250));camera=bpy.context.object;scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=1120;camera.data.clip_end=10000;aim(camera,(0,-150,35))
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
native=ROOT/'cad/flush_three_nozzles_assembled_mm.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
scene.render.filepath=str(ROOT/'images/all_three_assembled.png');bpy.ops.render.render(write_still=True)
for ob in list(objects.values())+hw_objects:
    if ob['group']!='outer':ob.hide_render=True
camera.location=(930,520,680);camera.data.ortho_scale=580;aim(camera,(360,-180,35))
scene.render.resolution_x=1400;scene.render.resolution_y=1100
scene.render.filepath=str(ROOT/'images/outer_assembled.png');bpy.ops.render.render(write_still=True)
matrix=matrices['outer']
objects['outer_inlet'].matrix_world=matrix@Matrix.Translation((0,0,-45))
objects['outer_tip_g8'].matrix_world=matrix@Matrix.Translation((0,0,45))
for ob in hw_objects:
    if ob['group']=='outer' and ob['hardware_kind']=='screw':
        shift=-45 if ob['joint']=='outer_body_joint' else 45;ob.matrix_world=matrix@Matrix.Translation((0,0,shift))
camera.data.ortho_scale=690;aim(camera,(360,-190,35))
scene.render.filepath=str(ROOT/'images/outer_exploded.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(native))
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-9
assert len([o for o in bpy.context.scene.objects if o.get('printable_part')])==7
for group in data['groups']:
    for name in group['parts']:
        ob=bpy.data.objects[name];expected=matrices[group['id']]
        assert max(abs(ob.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<1e-5
(ROOT/'native_checks.json').write_text(json.dumps({'native_reopened':True,'printable_part_count':7,'all_assembled_poses_verified':True,
    'verified_STL_sha256':{r['id']:hashlib.sha256(Path(r['STL']).read_bytes()).hexdigest() for r in data['parts']},
    'ray_checks':checks},indent=2),encoding='utf-8')
print('FLUSH_NATIVE_READBACK_PASSED',json.dumps(checks),flush=True)
