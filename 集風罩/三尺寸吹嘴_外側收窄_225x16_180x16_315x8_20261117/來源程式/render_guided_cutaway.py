"""Render an actual STL cutaway; this visualization is not a print part."""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.001
gap=json.loads((ROOT/'selection.json').read_text())['outer']['gap_mm']
bpy.ops.wm.stl_import(filepath=str(ROOT/'cad/full'/f'nozzle_W315_G{gap}_L320_ramp_guided_mm.stl'))
ob=bpy.context.object
ob.name='315_guided_cutaway_visualization_only'
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0001,
                       plane_co=(0,0,0),plane_no=(1,0,0),clear_outer=True)
bm.to_mesh(ob.data);bm.free()
ob.matrix_world=Matrix(((0,1,0,0),(0,0,1,-388),(1,0,0,0),(0,0,0,1)))
mat=bpy.data.materials.new('cutaway_teal');mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.04,.31,.37,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.42
ob.data.materials.append(mat)
def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.88,.91,.94,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.world=world
for loc in [(200,100,700),(-400,-200,500),(0,-800,500)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object;light.data.energy=7000000;light.data.size=500;aim(light,(0,-180,0))
bpy.ops.object.camera_add(location=(280,420,1150))
scene.camera=bpy.context.object;scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=530
scene.camera.data.clip_end=10000;aim(scene.camera,(0,-190,0))
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1200;scene.render.resolution_y=1100
scene.render.filepath=str(ROOT/'images/CAD_315_guide_cutaway.png')
bpy.ops.render.render(write_still=True)
print('ACTUAL_STL_GUIDE_CUTAWAY_RENDERED',flush=True)
