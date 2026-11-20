import bpy
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .001
scene.unit_settings.length_unit = 'MILLIMETERS'

def aim(ob, target):
    ob.rotation_euler = (Vector(target)-ob.location).to_track_quat('-Z', 'Y').to_euler()

for width, length, xpos in [(225, 220, -360), (180, 180, 0), (315, 320, 360)]:
    path = ROOT/'cad/full'/f'nozzle_W{width}_G16_L{length}_ramp_mm.stl'
    bpy.ops.wm.stl_import(filepath=str(path))
    ob = bpy.context.object
    ob.name = f'nozzle_{width}x16_candidate'
    ob.rotation_euler.z = math.pi/2
    ob.location.x = xpos
    material = bpy.data.materials.new(f'nozzle_{width}')
    material.diffuse_color = (.055, .31, .36, 1)
    material.use_nodes = True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.055, .31, .36, 1)
    material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .4
    ob.data.materials.append(material)
    bpy.ops.object.text_add(location=(xpos-86, -75, -45), rotation=(math.pi/2, 0, 0))
    text = bpy.context.object
    text.data.body = f'{width} x 16 mm'
    text.data.size = 25
    text.data.extrude = .12
    label = bpy.data.materials.new(f'label_{width}')
    label.diffuse_color = (.08, .1, .13, 1)
    text.data.materials.append(label)
world = bpy.data.worlds.new('Studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.8, .84, .89, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = .6
scene.world = world
for location, energy, size in [((200,-500,850),16000000,700),((-650,-250,400),12000000,600),((450,450,600),14000000,650)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    ob = bpy.context.object
    ob.data.energy = energy
    ob.data.size = size
    aim(ob, (0,0,140))
bpy.ops.object.camera_add(location=(650,-2000,900))
cam = bpy.context.object
scene.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 1200
cam.data.clip_end = 10000
aim(cam, (0,0,170))
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 2
scene.render.resolution_x = 1500
scene.render.resolution_y = 950
scene.render.resolution_percentage = 100
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'cad/three_sizes_ramp_candidates.blend'))
scene.render.filepath = str(ROOT/'images/CAD_three_sizes_candidates.png')
bpy.ops.render.render(write_still=True)
print('THREE_SIZE_CANDIDATE_PREVIEW_COMPLETE', flush=True)
