"""Render the actual saved core-free model; no manufacture file is edited."""
from pathlib import Path
import sys,json,hashlib,math,bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'尺寸與方向檢查.json').read_text(encoding='utf-8'))
SOURCE=HERE/r['blend_file'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=sha(SOURCE)
assert r['central_core_present'] is False
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
light('主光',(-260,-180,350),1700000,230);light('補光',(-120,230,230),900000,240);light('輪廓光',(230,70,300),1300000,200)
d=bpy.data.cameras.new('實際模型相機');camera=bpy.data.objects.new('實際模型相機',d);scene.collection.objects.link(camera);scene.camera=camera;d.type='ORTHO'
def render(name,loc):
    camera.location=loc;look(camera,(0,0,100));d.ortho_scale=285;scene.render.filepath=str(HERE/name);bpy.ops.render.render(write_still=True)
if '--interior-only' not in sys.argv:
    render('01_實際模型_12mm橫向出口_無核心.png',(-450,-300,290))
def material(name,color,opacity):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.4
    m.node_tree.links.new(n.outputs[0],out.inputs[0])
    return m
obj.data.materials.clear()
obj.data.materials.append(material('預覽切面外殼',(.25,.30,.35),1))
obj.data.materials.append(material('保留的十字薄導流片',(.08,.35,.5),1))
counts={'vanes':0,'shell':0}
for p in obj.data.polygons:
    x,y,z=p.center
    onvane=(z<=144.01 and abs(x)<1.02) or (z<=134.01 and abs(y)<1.02)
    p.material_index=1 if onvane else 0;counts['vanes' if onvane else 'shell']+=1
# Preview-only open housing: preserve all actual vane faces and the flange.
# No changed geometry is saved or exported to manufacturing files.
bm=bmesh.new();bm.from_mesh(obj.data)
remove=[f for f in bm.faces if f.material_index==0 and f.calc_center_median().x<0 and f.calc_center_median().z>3.05]
removed_faces=len(remove);bmesh.ops.delete(bm,geom=remove,context='FACES_ONLY')
bm.to_mesh(obj.data);bm.free();obj.data.update()
scene.cycles.samples=12;scene.render.resolution_x=1100;scene.render.resolution_y=1000
render('02_實際模型_無核心_保留十字導流片.png',(-430,-330,270))
assert sha(SOURCE)==digest
(HERE/'預覽來源檢查.json').write_text(json.dumps({'source':SOURCE.name,'source_sha256':digest,'source_unchanged':True,
    'actual_saved_manufacturing_mesh':True,'central_core_present':False,'interior_view':'Actual mesh with a preview-only housing cutaway; all manufacturing files unchanged',
    'preview_only_removed_shell_faces':removed_faces,
    'material_face_counts':counts},ensure_ascii=False,indent=2),encoding='utf-8')
print('CORE_FREE_PREVIEWS_DONE',flush=True)
