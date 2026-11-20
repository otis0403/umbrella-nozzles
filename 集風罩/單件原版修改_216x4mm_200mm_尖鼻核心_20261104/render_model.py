"""Actual saved manufacturing mesh; transparent materials for the inner view."""
from pathlib import Path
import sys,json,hashlib,math,bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from geometry import core_radii
report=json.loads((HERE/'尺寸與修改檢查.json').read_text(encoding='utf-8'))
SOURCE=HERE/report['blend_file'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
scene=bpy.context.scene;obj=next(o for o in scene.objects if o.type=='MESH')
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
if scene.world is None:scene.world=bpy.data.worlds.new('模型預覽背景')
scene.world.use_nodes=True
bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None) or scene.world.node_tree.nodes.new('ShaderNodeBackground')
out=next((n for n in scene.world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None) or scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],out.inputs[0]);bg.inputs[0].default_value=(.84,.87,.92,1);bg.inputs[1].default_value=.7
scene.view_settings.view_transform='AgX'
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;look(o,(0,0,100))
light('主光',(180,-260,350),1700000,230);light('補光',(-230,-120,230),900000,240);light('輪廓光',(70,230,300),1300000,200)
d=bpy.data.cameras.new('實際模型相機');camera=bpy.data.objects.new('實際模型相機',d);scene.collection.objects.link(camera);scene.camera=camera;d.type='ORTHO'
def render(name,loc,target,scale=285):
    camera.location=loc;look(camera,target);d.ortho_scale=scale;scene.render.filepath=str(HERE/name);bpy.ops.render.render(write_still=True)
render('01_實際模型_200mm單件外觀.png',(300,-450,290),(0,0,100))
def mat(name,color,opacity):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.4
    if opacity<1:
        trans=m.node_tree.nodes.new('ShaderNodeBsdfTransparent');mix=m.node_tree.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=opacity
        m.node_tree.links.new(trans.outputs[0],mix.inputs[1]);m.node_tree.links.new(n.outputs[0],mix.inputs[2]);m.node_tree.links.new(mix.outputs[0],out.inputs[0])
    else:m.node_tree.links.new(n.outputs[0],out.inputs[0])
    return m
obj.data.materials.clear()
for m in [mat('透明外殼',(.2,.26,.31),.055),mat('尖鼻核心',(.95,.26,.03),1),mat('薄十字片',(.08,.35,.5),.11)]:obj.data.materials.append(m)
counts={'core':0,'vanes':0,'shell':0}
for p in obj.data.polygons:
    x,y,z=p.center;rx,ry=core_radii(z)
    oncore=rx>0 and ry>0 and abs((x/rx)**2+(y/ry)**2-1)<.035
    onvane=(z<=144.01 and abs(y)<1.02) or (z<=134.01 and abs(x)<1.02)
    if oncore:p.material_index=1;counts['core']+=1
    elif onvane:p.material_index=2;counts['vanes']+=1
    else:p.material_index=0;counts['shell']+=1
render('02_實際模型_尖鼻核心與底面支撐.png',(150,-530,250),(0,0,100))
assert sha(SOURCE)==digest
(HERE/'預覽來源檢查.json').write_text(json.dumps({'source':SOURCE.name,'source_sha256':digest,'source_unchanged':True,
    'actual_saved_manufacturing_mesh':True,'interior_view':'Transparent materials only; no manufacturing geometry changes',
    'face_classification_counts':counts},ensure_ascii=False,indent=2),encoding='utf-8')
print('SINGLE_MODEL_PREVIEWS_DONE',flush=True)
