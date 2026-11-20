"""Native modular assembly with independent STL ray checks and actual renders."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'modular_checks.json').read_text())
parts={row['id']:row for row in data['parts']}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
def material(name,color):
    result=bpy.data.materials.new(name);result.use_nodes=True
    result.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    result.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.42
    return result
body_mat=material('Fixed body',(.045,.27,.32))
tip_mat=material('Replaceable tip',(.8,.28,.065))
metal=material('Illustrative M4 hardware',(.3,.34,.38))
ink=material('Labels',(.025,.035,.05))
alternate=bpy.data.collections.new('Reference16mmTips_hidden');scene.collection.children.link(alternate)
alternate.hide_render=True;alternate.hide_viewport=True
records=[];preferred_objects=[];hardware_objects=[];texts=[]

def import_part(row,matrix):
    bpy.ops.wm.stl_import(filepath=row['file'],use_scene_unit=False)
    ob=bpy.context.object;ob.name=row['id'];ob.matrix_world=matrix
    ob.data.materials.append(body_mat if row['type']=='body' else tip_mat)
    ob['source_STL']=row['file'];ob['part_type']=row['type'];ob['assembly_translation_mm']=row['assembly_translation_mm']
    return ob
def tree(ob):return BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)
def span(bvh,point,axis):
    hits=[bvh.ray_cast(Vector(point),s*Vector(axis),1000) for s in [-1,1]]
    assert all(hit[0] is not None for hit in hits),(point,axis)
    return sum(hit[3] for hit in hits)
def add_hardware(name,radius,depth,point,matrix,vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=point)
    ob=bpy.context.object;ob.name=name;ob.matrix_world=matrix@ob.matrix_world
    ob.data.materials.append(metal);ob['illustration_only_not_print_part']=True;hardware_objects.append(ob)
for xpos,group in zip([360,0,-360],data['groups']):
    key=group['position'];w=group['width_mm'];g=group['preferred_gap_mm'];h=group['total_length_mm'];z=group['split_Z_mm']
    matrix=Matrix(((0,1,0,xpos),(0,0,1,-h),(1,0,0,30.1),(0,0,0,1)))
    body=import_part(parts[group['body']],matrix);body_tree=tree(body)
    socket=span(body_tree,(0,0,12),(0,1,0))
    joint_w=span(body_tree,(0,0,z-.1),(0,1,0));joint_d=span(body_tree,(0,0,z-.1),(1,0,0))
    assert abs(socket-55.4)<.03 and abs(joint_w-w)<.03 and abs(joint_d-22)<.03
    assert body_tree.ray_cast(Vector((0,0,-.1)),Vector((0,0,1)),z+2)[0] is None
    tips=[]
    for tip_id in group['tips']:
        row=parts[tip_id];tip_matrix=matrix@Matrix.Translation((0,0,z))
        ob=import_part(row,tip_matrix);bvh=tree(ob)
        gaps=[span(bvh,(0,-w/2+1+(w-2)*i/60,42.9),(1,0,0)) for i in range(61)]
        width=span(bvh,(0,0,42.9),(0,1,0))
        interface=span(bvh,(0,0,.1),(1,0,0))
        assert max(abs(value-row['gap_mm']) for value in gaps)<.03 and abs(width-w)<.03 and abs(interface-22)<.03
        assert bvh.ray_cast(Vector((0,0,-.1)),Vector((0,0,1)),43.2)[0] is None
        x,y=group['screw_centers_XY_mm'][0]
        bolt=span(bvh,(x,y,3),(1,0,0));pocket=span(bvh,(x,y,.7),(1,0,0))
        assert abs(bolt-4.4)<.03 and abs(pocket-7.9)<.03
        x2,y2=group['screw_centers_XY_mm'][-1]
        float_pocket=span(bvh,(x2,y2,.7),(0,1,0));float_hole=span(bvh,(x2,y2,3),(0,1,0))
        assert abs(float_pocket-8.9)<.03 and abs(float_hole-5.4)<.03
        tips.append({'id':tip_id,'gap_mm':row['gap_mm'],'gap61_range_mm':[min(gaps),max(gaps)],'width_mm':width,
                     'interface_depth_mm':interface,'M4_hole_mm':bolt,'fixed_recess_mm':pocket,
                     'floating_recess_Y_mm':float_pocket,'floating_hole_Y_mm':float_hole})
        if row['variant']=='reference':
            for collection in list(ob.users_collection):collection.objects.unlink(ob)
            alternate.objects.link(ob)
        else:preferred_objects.append((ob,matrix,z))
    x,y=group['screw_centers_XY_mm'][0]
    distances=[]
    for direction in [-1,1]:
        origin=Vector((x+direction*10,y,z+.7))
        hit=body_tree.ray_cast(origin,Vector((-direction,0,0)),20)
        assert hit[0] is not None;distances.append(hit[3])
    male=20-sum(distances)
    assert abs(male-7.4)<.03
    records.append({'position':key,'socket_ID_mm':socket,'joint_width_mm':joint_w,'joint_depth_mm':joint_d,
                    'locator_male_OD_mm':male,'tips':tips,'flow_axis_horizontal':True,'body_to_tip_translation_mm':[0,0,z]})
    for index,(x,y) in enumerate(group['screw_centers_XY_mm']):
        prefix=f'M4_{key}_{index}'
        add_hardware(prefix+'_shaft',2,16,(x,y,z-3.2),matrix)
        add_hardware(prefix+'_head',3.5,4,(x,y,z+6.8),matrix)
        add_hardware(prefix+'_front_washer',4.5,.8,(x,y,z+4.4),matrix)
        add_hardware(prefix+'_rear_washer',4.5,.8,(x,y,z-4.4),matrix)
        add_hardware(prefix+'_nut',3.5/math.cos(math.pi/6),3.2,(x,y,z-6.4),matrix,6)
    bpy.ops.object.text_add(location=(xpos+100,80,30.1),rotation=(0,0,math.pi))
    label=bpy.context.object;label.data.body=f'{w} x {g} mm\n{group["screw_count"]} x M4';label.data.size=20
    label.data.materials.append(ink);texts.append(label)
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.86,.9,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.6;scene.world=world
for location,power,size in [((150,-400,850),14000000,650),((-650,150,500),10000000,550),((500,650,600),12000000,600)]:
    bpy.ops.object.light_add(type='AREA',location=location);ob=bpy.context.object;ob.data.energy=power;ob.data.size=size;aim(ob,(0,-110,30))
bpy.ops.object.camera_add(location=(500,1400,1300));camera=bpy.context.object;scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=1200;camera.data.clip_end=10000;aim(camera,(0,-115,30))
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
native=ROOT/'cad/modular_nozzles_assembled_mm.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
scene.render.filepath=str(ROOT/'images/modular_assembled.png');bpy.ops.render.render(write_still=True)
for ob,matrix,z in preferred_objects:ob.matrix_world=matrix@Matrix.Translation((0,0,z+45))
for ob in hardware_objects:ob.hide_render=True
for ob in texts:ob.location.y+=70
scene.render.filepath=str(ROOT/'images/modular_exploded.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(native))
assert math.isclose(bpy.context.scene.unit_settings.scale_length,.001,abs_tol=1e-9)
for group in data['groups']:
    body=bpy.data.objects[group['body']];tip=bpy.data.objects[group['preferred_tip']]
    translation=(body.matrix_world.inverted()@tip.matrix_world).translation
    assert (translation-Vector((0,0,group['split_Z_mm']))).length<1e-4
    assert abs(body.matrix_world.to_3x3().col[2].normalized().z)<1e-6
(ROOT/'native_geometry_checks.json').write_text(json.dumps({'native_reopened':True,'records':records,'illustrative_hardware_not_STL_parts':True},indent=2),encoding='utf-8')
print('MODULAR_NATIVE_REOPEN_AND_DIMENSIONS_PASSED',json.dumps(records),flush=True)
