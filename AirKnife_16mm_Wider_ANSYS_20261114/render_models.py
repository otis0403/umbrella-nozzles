"""Native geometry read-back and honest CAD previews; no old model writes."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
report=json.loads((ROOT/'cad/geometry_checks.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
collections={}
for group in ['body','lip_H320','lip_H360']:
    c=bpy.data.collections.new(group);scene.collection.children.link(c);collections[group]=c
for r in report['parts']:
    bpy.ops.wm.stl_import(filepath=str(ROOT/'cad/reference'/(r['name']+'.stl')))
    ob=bpy.context.object;ob.name=r['name']
    for col in list(ob.users_collection):col.objects.unlink(ob)
    collections[r['group']].objects.link(ob)
    color=(.08,.14,.19) if r['group']=='body' else (.08,.42,.46)
    mat=bpy.data.materials.new(ob.name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4;ob.data.materials.append(mat)
def bvh(obs):
    verts=[];faces=[]
    for ob in obs:
        off=len(verts);verts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
        faces.extend(tuple(off+i for i in p.vertices) for p in ob.data.polygons)
    return BVHTree.FromPolygons(verts,faces,all_triangles=True)
checks=[]
for height in [320,360]:
    tr=bvh(list(collections['body'].objects)+list(collections[f'lip_H{height}'].objects));widths=[]
    for j in range(61):
        p=Vector((0,-125.5+251*j/60,height-.1));hits=[tr.ray_cast(p,Vector((s,0,0)),30) for s in [-1,1]]
        assert all(h[0] is not None for h in hits)
        gap=sum(h[3] for h in hits);assert abs(gap-16)<.025; widths.append(gap)
    length=sum(tr.ray_cast(Vector((.3,0,height-.1)),Vector((0,s,0)),140)[3] for s in [-1,1]);assert abs(length-252)<.03
    assert tr.ray_cast(Vector((0,0,-1)),Vector((0,0,1)),height+2)[0] is None
    for hole in report['original_holes']:
        assert tr.ray_cast(Vector((hole['x'],hole['y'],-1)),Vector((0,0,1)),5)[0] is None
    for x in [-20.,20.]:
        for y in [-70.,70.]:assert tr.ray_cast(Vector((x,y,193)),Vector((0,0,1)),14)[0] is None
    ob=next(iter(collections[f'lip_H{height}'].objects));v=[p.co for p in ob.data.vertices]
    top=[max(p.z for p in v if s*p.x>0) for s in [-1,1]];assert max(top)-min(top)<.001 and abs(top[0]-height)<.001
    checks.append({'height_mm':height,'slot_sample_count':61,'measured_gap_range_mm':[min(widths),max(widths)],
        'measured_clear_span_mm':length,'12_original_holes_clear':True,'4_module_screw_paths_clear':True,
        'central_axis_clear':True,'opposite_outlet_rim_top_Z_mm':top})
(ROOT/'cad/airpath_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
world=bpy.data.worlds.new('Studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.78,.85,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
for loc,power,size in [((150,-250,600),10000000,400),((-280,-100,250),6000000,350),((100,350,400),8000000,350)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.shape='DISK';ob.data.size=size
    ob.rotation_euler=(Vector((0,0,180))-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(500,-700,480));cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2;scene.view_settings.exposure=-1
scene.render.resolution_x=1200;scene.render.resolution_y=1300;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
def show(height):
    for name,col in collections.items():col.hide_render=col.hide_viewport=name not in ['body',f'lip_H{height}']
    cam.location=(500,-700,480);cam.rotation_euler=(Vector((0,0,height/2))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=height+180
for h in [320,360]:
    show(h);scene.render.filepath=str(ROOT/'images'/f'CAD_H{h}_W252_gap16.png');bpy.ops.render.render(write_still=True)
show(320)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=(0,0,160);area.spaces.active.region_3d.view_distance=600;area.spaces.active.clip_end=10000
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'cad/K1C_252x16_longer_no_ribs.blend'))
print('NATIVE_MODELS_AND_AIRPATH_CHECKS_COMPLETE',flush=True)
