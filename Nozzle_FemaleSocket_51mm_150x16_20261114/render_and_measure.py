"""Native Blender model and independent STL ray measurements, mm."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
geo=json.loads((ROOT/'cad/geometry_checks.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
part=geo['parts'][0]
bpy.ops.wm.stl_import(filepath=str(ROOT/'print/STL'/(part['name']+'_mm.stl')))
ob=bpy.context.object;ob.name=part['name']
tr=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(f.vertices) for f in ob.data.polygons],all_triangles=True)
def span(origin,axis,distance=200):
    hits=[tr.ray_cast(Vector(origin),Vector(axis)*sign,distance) for sign in [-1,1]]
    assert all(h[0] is not None for h in hits)
    return sum(h[3] for h in hits)
socket=span((0,0,12),(0,1,0));throat=span((0,0,25.2),(0,1,0))
assert abs(socket-55.4)<.03 and abs(throat-51)<.03
gaps=[span((0,y,187.9),(1,0,0)) for y in [-74+148*k/60 for k in range(61)]]
assert max(abs(g-16) for g in gaps)<.025
length=span((0,0,187.9),(0,1,0));assert abs(length-150)<.025
assert tr.ray_cast(Vector((0,0,-.1)),Vector((0,0,1)),190)[0] is None
slot_open=[tr.ray_cast(Vector((0,0,10)),Vector((s,0,0)),40)[0] is None for s in [-1,1]]
assert all(slot_open)
heights=[max(v.co.z for v in ob.data.vertices if s*v.co.y>0) for s in [-1,1]]
assert abs(heights[0]-heights[1])<.001 and abs(heights[0]-188)<.001
checks=dict(measured_socket_ID_mm=socket,measured_flow_inlet_ID_mm=throat,gap_samples=61,gap_range_mm=[min(gaps),max(gaps)],
    outlet_span_mm=length,axial_passage_clear=True,clamp_slots_open=slot_open,outlet_end_heights_mm=heights,physical_fit_verified=False)
(ROOT/'cad/airpath_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
mat=bpy.data.materials.new('Blue PLA preview');mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.09,.35,.44,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4;ob.data.materials.append(mat)
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.86,.9,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
for location,power,size in [((200,-250,400),9000000,350),((-220,-100,150),6000000,300),((70,250,250),6000000,300),((100,-150,-200),4000000,200)]:
    bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object;light.data.energy=power;light.data.size=size
    light.rotation_euler=(Vector((0,0,75))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=245
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.view_settings.exposure=-1;scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
for name,location,target in [('CAD_female_nozzle',(350,-480,260),(0,0,90)),('CAD_socket_bottom',(270,-380,-150),(0,0,75))]:
    cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/'images'/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(350,-480,260);cam.rotation_euler=(Vector((0,0,90))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'cad/Nozzle_female_socket_55p4.blend'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'cad/Nozzle_female_socket_55p4.blend'))
native=bpy.data.objects[part['name']]
assert math.isclose(bpy.context.scene.unit_settings.scale_length,.001,abs_tol=1e-9)
assert max(abs(native.dimensions[i]-part['print_size_mm'][i]) for i in range(3))<.001
(ROOT/'cad/native_reopen_checks.json').write_text(json.dumps(dict(native_blend_reopened=True,dimensions_match_STL=True,scale_length=.001),indent=2),encoding='utf-8')
print('FEMALE_CAD_NATIVE_AND_MEASUREMENTS_VERIFIED',flush=True)
