"""Reconstruct print STLs, ray-check interfaces, save and reread Blender model."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'print_checks.json').read_text(encoding='utf-8-sig'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
display=Matrix(((0,1,0,0),(0,0,1,-388),(1,0,0,30.1),(0,0,0,1)))
objects={};trees={}
def material(name,color):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.42
    return mat
for row,color in zip(data['parts'],[(.04,.20,.27),(.10,.43,.49),(.95,.32,.07)]):
    bpy.ops.wm.stl_import(filepath=row['STL'],use_scene_unit=False)
    ob=bpy.context.object;ob.name=row['id']
    ob.data.transform(Matrix(row['assembly_from_print']));ob.matrix_world=display
    ob.data.materials.append(material(row['id'],color))
    ob['print_file']=Path(row['STL']).name;ob['source_frame_mm']=True
    objects[row['id']]=ob
    trees[row['id']]=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)

def span(bvh,p,axis):
    hits=[bvh.ray_cast(Vector(p),s*Vector(axis),1000) for s in [-1,1]]
    assert all(h[0] is not None for h in hits),(p,axis)
    return sum(h[3] for h in hits)
lower=trees['inlet_lower'];upper=trees['guided_upper'];tip=trees['front_tip_g8']
socket=span(lower,(0,0,12),(0,1,0));assert abs(socket-55.4)<.03
joint_d=span(upper,(0,0,344.9),(1,0,0));joint_w=span(upper,(0,0,344.9),(0,1,0))
assert abs(joint_d-22)<.03 and abs(joint_w-315)<.03
gaps=[span(tip,(0,-156.5+313*i/60,387.9),(1,0,0)) for i in range(61)]
width=span(tip,(0,0,387.9),(0,1,0))
assert max(abs(g-8) for g in gaps)<.03 and abs(width-315)<.03
assert tip.ray_cast(Vector((0,0,344.9)),Vector((0,0,1)),43.2)[0] is None
wp,dp,rp=data['new_joint_nominal_flow_mm']
cross_d=span(upper,(0,0,55.1),(1,0,0))
yhi=upper.ray_cast(Vector((0,wp*.35,55.1)),Vector((0,1,0)),100)[0].y
ylo=upper.ray_cast(Vector((0,-wp*.35,55.1)),Vector((0,-1,0)),100)[0].y
assert abs(cross_d-dp)<.05 and abs((yhi-ylo)-wp)<.08
guide_starts=[]
# Source mapped rounded-section guide midlines at X=0, Z=55 are +/-8.030094.
# The grid's normalized fraction is not a Cartesian Y fraction in this capsule.
for y in [-8.030094,8.030094]:
    hit=upper.ray_cast(Vector((0,y,54)),Vector((0,0,1)),5)
    assert hit[0] is not None and abs(hit[0].z-55)<.01
    guide_starts.append(hit[0].z-55)
x,y=data['new_joint_screw_centers_XY_mm'][0]
bolt=span(upper,(x,y,58),(1,0,0));recess=span(upper,(x,y,55.7),(1,0,0))
x2,y2=data['new_joint_screw_centers_XY_mm'][-1]
float_recess=span(upper,(x2,y2,55.7),(0,1,0));float_hole=span(upper,(x2,y2,58),(0,1,0))
assert abs(bolt-4.4)<.03 and abs(recess-7.9)<.03 and abs(float_recess-8.9)<.03 and abs(float_hole-5.4)<.03
dist=[]
for direction in [-1,1]:
    hit=lower.ray_cast(Vector((x+direction*10,y,55.7)),Vector((-direction,0,0)),20)
    assert hit[0] is not None;dist.append(hit[3])
male=20-sum(dist);assert abs(male-7.4)<.03
records={'socket_ID_mm':socket,'existing_tip_interface_mm':[joint_w,joint_d],
         'tip_gap61_range_mm':[min(gaps),max(gaps)],'tip_width_mm':width,
         'new_joint_flow_section_mm':[yhi-ylo,cross_d],
         'guide_leading_faces_print_Z_mm':guide_starts,'M4_hole_mm':bolt,
         'fixed_recess_mm':recess,'floating_recess_Y_mm':float_recess,
         'floating_hole_Y_mm':float_hole,'male_locator_OD_mm':male}

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.85,.9,.94,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
for loc,power,size in [((200,-400,600),4500000,400),((-450,80,350),3500000,400),((300,350,500),4000000,400)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object
    ob.data.energy=power;ob.data.size=size;aim(ob,(0,-160,30))
bpy.ops.object.camera_add(location=(570,520,680));camera=bpy.context.object;scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=565;camera.data.clip_end=10000;aim(camera,(0,-180,30))
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
native=ROOT/'cad/outer315_K2Pro_assembled_mm.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
scene.render.filepath=str(ROOT/'images/assembled.png');bpy.ops.render.render(write_still=True)
objects['guided_upper'].matrix_world=display@Matrix.Translation((0,0,40))
objects['front_tip_g8'].matrix_world=display@Matrix.Translation((0,0,80))
camera.data.ortho_scale=650;aim(camera,(0,-140,30))
scene.render.filepath=str(ROOT/'images/exploded.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(native))
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-9
for key in objects:
    ob=bpy.data.objects[key]
    assert max(abs(ob.matrix_world[i][j]-display[i][j]) for i in range(4) for j in range(4))<1e-5
    assert len(ob.data.polygons)>0
assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==3
(ROOT/'native_geometry_checks.json').write_text(json.dumps({'native_reopened':True,'assembled_pose_verified':True,'ray_checks':records},indent=2),encoding='utf-8')
print('K2PRO_NATIVE_REOPEN_AND_DIMENSIONS_PASSED',json.dumps(records),flush=True)
