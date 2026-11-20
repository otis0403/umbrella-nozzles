"""Save the chosen display state, then reopen the new native model for verification."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
h=json.loads((ROOT/'selection.json').read_text())['selected_total_height_mm']
path=ROOT/'cad/K1C_252x16_longer_no_ribs.blend'
assert Path(bpy.data.filepath).resolve()==path.resolve()
bpy.context.preferences.filepaths.save_version=0
for name in ['body','lip_H320','lip_H360']:
    col=bpy.data.collections[name];col.hide_viewport=col.hide_render=name not in ['body',f'lip_H{h}']
cam=bpy.context.scene.camera;cam.rotation_euler=(Vector((0,0,h/2))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=h+180
bpy.ops.wm.save_as_mainfile(filepath=str(path));bpy.ops.wm.open_mainfile(filepath=str(path))
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-8
for name in ['body','lip_H320','lip_H360']:
    col=bpy.data.collections[name];assert len(col.objects)==1
    assert col.hide_render==(name not in ['body',f'lip_H{h}'])
    assert all(abs(v)<1e-8 for ob in col.objects for v in ob.location)
(ROOT/'cad/native_reopen_check.json').write_text(json.dumps({'native_file_reopened':True,'mm_units':True,
    'selected_height_mm':h,'saved_assembled_state':True,'one_object_per_component':True},indent=2),encoding='utf-8')
print('NATIVE_MODEL_REOPEN_VERIFIED',flush=True)
