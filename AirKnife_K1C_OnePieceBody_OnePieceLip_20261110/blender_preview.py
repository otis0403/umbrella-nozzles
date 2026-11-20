"""Native CAD inspection and renders; never read or save the old blends."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
report=json.loads((ROOT/'cad'/'geometry_checks.json').read_text())
H=report['height_mm'];B=report['body_lip_joint_Z_mm']
DEFAULT_GAP=16
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
objects={};collections={}
for group in ['body','lip_8','lip_12','lip_16']:
    col=bpy.data.collections.new(group);scene.collection.children.link(col);collections[group]=col
for rec in report['parts']:
    if rec['group'] not in collections:continue
    bpy.ops.wm.stl_import(filepath=str(ROOT/'cad'/'reference'/(rec['name']+'.stl')))
    ob=bpy.context.object;ob.name=rec['name']
    for col in list(ob.users_collection):col.objects.unlink(ob)
    collections[rec['group']].objects.link(ob);objects[ob.name]=ob
    color=(.08,.14,.19) if rec['group']=='body' else (.08,.42,.46)
    if rec['name'].endswith('_B') or rec['name'].endswith('_back'):color=tuple(min(1,c*1.5) for c in color)
    mat=bpy.data.materials.new(ob.name+'_color');mat.diffuse_color=(*color,1);mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4;ob.data.materials.append(mat)
    for f in ob.data.polygons:f.use_smooth=False

def tree(group):
    verts=[];faces=[]
    for ob in group:
        off=len(verts);verts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
        faces.extend(tuple(off+i for i in f.vertices) for f in ob.data.polygons)
    return BVHTree.FromPolygons(verts,faces,all_triangles=True)

checks=[]
for gap in [8,12,16]:
    obs=list(collections['body'].objects)+list(collections[f'lip_{gap}'].objects)
    tr=tree(obs);samples=[]
    for j in range(61):
        y=-107.5+215*j/60;p=Vector((0,y,H-.1))
        hits=[tr.ray_cast(p,Vector((s,0,0)),40) for s in [-1,1]]
        assert all(h[0] is not None for h in hits),(gap,y,'missing wall')
        width=sum(h[3] for h in hits);assert abs(width-gap)<.025,(gap,y,width)
        samples.append(width)
    length=sum(tr.ray_cast(Vector((.3,0,H-.1)),Vector((0,s,0)),120)[3] for s in [-1,1])
    assert abs(length-216)<.03,(gap,length)
    assert tr.ray_cast(Vector((0,0,-1)),Vector((0,0,1)),H+2)[0] is None,'central path blocked'
    holes=[]
    for hole in report['original_holes']:
        assert tr.ray_cast(Vector((hole['x'],hole['y'],-1)),Vector((0,0,1)),5)[0] is None,hole
        center=Vector((hole['x'],hole['y'],1.5))
        diameter=sum(tr.ray_cast(center,Vector((s,0,0)),8)[3] for s in [-1,1])
        assert abs(diameter-hole['d'])<.025,(hole,diameter)
        holes.append({**hole,'measured_diameter_mm':diameter})
    checks.append({'gap_mm':gap,'measured_gap_range_mm':[min(samples),max(samples)],
        'slot_sample_count':61,'measured_clear_length_mm':length,'original_12_holes_clear':True,
        'central_axis_clear_throughout':True,'measured_mounting_holes':holes})
(ROOT/'cad'/'assembled_airpath_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
for k,col in collections.items():col.hide_render=col.hide_viewport=k not in ['body',f'lip_{DEFAULT_GAP}']

def camera(location,target,scale):
    bpy.ops.object.camera_add(location=location);c=bpy.context.object
    c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
    c.data.type='ORTHO';c.data.ortho_scale=scale;scene.camera=c;return c
cam=camera((420,-540,390),(0,0,H/2),430)
world=bpy.data.worlds.new('Studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.78,.85,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
for loc,power,size in [((150,-250,500),10000000,350),((-280,-100,250),6000000,300),((100,350,350),8000000,300)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size
    l.rotation_euler=(Vector((0,0,H/2))-l.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.view_settings.exposure=-1.
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.region_3d.view_location=(0,0,H/2);a.spaces.active.region_3d.view_distance=450
        a.spaces.active.clip_end=10000
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'cad'/'K1C_two_piece_airknife.blend'))
(ROOT/'images').mkdir(exist_ok=True)
scene.render.filepath=str(ROOT/'images'/'01_assembled.png');bpy.ops.render.render(write_still=True)
for ob in collections[f'lip_{DEFAULT_GAP}'].objects:
    ob.location.z+=45
cam.data.ortho_scale=520
scene.render.filepath=str(ROOT/'images'/'02_exploded.png');bpy.ops.render.render(write_still=True)
print('ASSEMBLY_RAYS_AND_RENDERS_COMPLETE',flush=True)
