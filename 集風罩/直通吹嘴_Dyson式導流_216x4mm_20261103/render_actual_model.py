"""Render the actual new manufacturing mesh; all cutaways are disposable."""
from pathlib import Path
import bpy,math,json,hashlib
from mathutils import Vector

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'直通吹嘴_216x4mm_中央鴨嘴導流_單件.blend'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source_hash=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
scene=bpy.context.scene
obj=next(o for o in scene.objects if o.type=='MESH')
# The manifold solver retains the manufacturing geometry but may collapse
# material assignments. Identify exposed fairing/plate surfaces for the preview.
def smooth(t):
    t=max(0,min(1,t));return t*t*t*(10+t*(-15+6*t))
counts={'core':0,'vanes':0,'shell':0}
for poly in obj.data.polygons:
    x,y,z=poly.center
    s=smooth((z-24)/116);rx=18+(0.8-18)*s;ry=21+(0.8-21)*s
    q=(x/rx)**2+(y/ry)**2
    if -.001<=z<=140.001 and .97<q<1.02:
        poly.material_index=1;counts['core']+=1
    elif (z<=180.001 and abs(y)<1.02) or (z<=170.001 and abs(x)<1.02):
        poly.material_index=2;counts['vanes']+=1
    else:poly.material_index=0;counts['shell']+=1
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
if scene.world is None:scene.world=bpy.data.worlds.new('預覽背景')
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.85,.9,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
scene.view_settings.view_transform='AgX'

def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def area(name,location,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=location;look(o,(0,0,100))

area('主光',(180,-260,380),1700000,230)
area('補光',(-240,-100,230),900000,230)
area('輪廓光',(70,260,300),1300000,180)
camera_data=bpy.data.cameras.new('預覽相機');camera=bpy.data.objects.new('預覽相機',camera_data)
scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=310
camera.location=(330,-480,310);look(camera,(0,0,120))

def render(name):
    scene.render.filepath=str(HERE/name);bpy.ops.render.render(write_still=True)

render('01_實際模型_完整外觀.png')

# Transparent preview-only materials expose the original core and crossed plates
# without removing manufacturing faces or saving any changes to the .blend.
for index,fraction in [(0,.055),(2,.24)]:
    mat=obj.data.materials[index];nodes=mat.node_tree.nodes;links=mat.node_tree.links
    output=nodes.get('Material Output');principled=nodes.get('Principled BSDF')
    transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader')
    mix.inputs[0].default_value=fraction
    links.new(transparent.outputs[0],mix.inputs[1]);links.new(principled.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],output.inputs['Surface'])
camera.location=(280,-500,270);look(camera,(0,0,110));camera.data.ortho_scale=310
render('02_實際模型_核心與十字導流剖視.png')
assert sha(SOURCE)==source_hash
(HERE/'預覽來源檢查.json').write_text(json.dumps({'source':str(SOURCE),'source_sha256':source_hash,
    'source_unchanged':True,'preview_method':'Actual manufacturing mesh; transparent housing/plate materials only',
    'preview_material_face_counts':counts,
    'render_engine':'Cycles CPU','samples':24,'saved_preview_scene':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('ACTUAL_MESH_PREVIEWS_DONE',flush=True)
