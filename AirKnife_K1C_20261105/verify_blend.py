"""Run after opening the saved native model, without saving over it."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
assert Path(bpy.data.filepath).resolve()==(ROOT/'cad'/'K1C_modular_airknife.blend').resolve()
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-8
out=[]
for name in ['body','lip_8','lip_12','lip_16']:
    col=bpy.data.collections[name]
    assert len(col.objects)==2,name
    expected=name not in ['body','lip_16']
    assert col.hide_render==expected and col.hide_viewport==expected,name
    out.append({'collection':name,'mesh_objects':[o.name for o in col.objects],
        'hidden_by_default':col.hide_render})
for col in out:
    for name in col['mesh_objects']:
        ob=bpy.data.objects[name]
        assert ob.type=='MESH' and len(ob.data.polygons)>0
        assert all(abs(v)<1e-8 for v in ob.location),'saved model must be assembled'
(ROOT/'cad'/'native_model_reopen.json').write_text(json.dumps({'native_blend_reopened':True,
    'millimetre_units':True,'saved_in_assembled_state':True,'default_gap_mm':16,'collections':out},indent=2),encoding='utf-8')
print('NATIVE_BLEND_REOPEN_VERIFIED',flush=True)
