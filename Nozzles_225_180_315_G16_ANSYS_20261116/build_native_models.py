"""Native horizontal nozzle models and independent STL passage measurements."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.001
scene.unit_settings.length_unit='MILLIMETERS'
records=[]
for label,width,length,xpos in [('inner',225,220,360),('center',180,180,0),('outer',315,320,-360)]:
    suffix='_guided' if width==315 and (ROOT/'use_guided315.flag').exists() else ''
    path=ROOT/'cad/full'/f'nozzle_W{width}_G16_L{length}_ramp{suffix}_mm.stl'
    bpy.ops.wm.stl_import(filepath=str(path),use_scene_unit=False)
    ob=bpy.context.object
    ob.name=f'{label}_{width}x16_complete'
    h=68+length
    tree=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)
    def span(point,axis):
        hits=[tree.ray_cast(Vector(point),sign*Vector(axis),500) for sign in [-1,1]]
        assert all(hit[0] is not None for hit in hits)
        return sum(hit[3] for hit in hits)
    gap=[span((0,-width/2+1+(width-2)*j/60,h-.1),(1,0,0)) for j in range(61)]
    measured_width=span((0,0,h-.1),(0,1,0))
    socket=span((0,0,12),(0,1,0))
    assert max(abs(g-16) for g in gap)<.03
    assert abs(measured_width-width)<.03 and abs(socket-55.4)<.03
    assert tree.ray_cast(Vector((0,0,-.1)),Vector((0,0,1)),h+.2)[0] is None
    matrix=Matrix(((0,1,0,xpos),(0,0,1,-h),(1,0,0,30.1),(0,0,0,1)))
    ob.matrix_world=matrix
    ob['source_STL']=str(path)
    ob['net_outlet_size_mm']=f'{width} x 16'
    ob['profile']='smooth ramp with limited peak widening rate'
    material=bpy.data.materials.new(f'nozzle_{width}')
    material.use_nodes=True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.045,.27,.32,1)
    material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4
    ob.data.materials.append(material)
    records.append({'name':ob.name,'width_mm':measured_width,'gap_range_mm':[min(gap),max(gap)],
                    'gap_samples':61,'socket_ID_mm':socket,'total_length_mm':h,'axial_passage_clear':True,
                    'flow_axis_world':[0,1,0],'broad_body_plane_parallel_floor':True,'source_STL':str(path),'guide_count':2 if suffix else 0})
    bpy.ops.object.text_add(location=(xpos+85,65,30.1),rotation=(0,0,math.pi))
    text=bpy.context.object
    text.data.body=f'{width} x 16 mm'
    text.data.size=25
    ink=bpy.data.materials.new(f'label_{width}')
    ink.use_nodes=True
    ink.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.025,.035,.05,1)
    text.data.materials.append(ink)

def aim(ob,target):
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

world=bpy.data.worlds.new('Studio')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.86,.9,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.55
scene.world=world
for location,power,size in [((150,-400,850),14000000,650),((-650,150,500),10000000,550),((500,650,600),12000000,600)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    light=bpy.context.object
    light.data.energy=power
    light.data.size=size
    aim(light,(0,-100,30))
bpy.ops.object.camera_add(location=(500,1400,1300))
camera=bpy.context.object
scene.camera=camera
camera.data.type='ORTHO'
camera.data.ortho_scale=1200
camera.data.clip_end=10000
aim(camera,(0,-130,30))
scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'
scene.render.threads=2
scene.render.resolution_x=1500
scene.render.resolution_y=950
scene.render.resolution_percentage=100
dest=ROOT/'cad/three_complete_nozzles_horizontal.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
scene.render.filepath=str(ROOT/'images/CAD_three_nozzles_horizontal.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(dest))
for row in records:
    ob=bpy.data.objects[row['name']]
    assert abs(ob.matrix_world.to_3x3().col[2].normalized().z)<1e-6
assert math.isclose(bpy.context.scene.unit_settings.scale_length,.001,abs_tol=1e-9)
(ROOT/'cad/native_geometry_checks.json').write_text(json.dumps({'native_reopened':True,'records':records},indent=2),encoding='utf-8')
print('THREE_COMPLETE_NATIVE_MODELS_VERIFIED',json.dumps(records),flush=True)
