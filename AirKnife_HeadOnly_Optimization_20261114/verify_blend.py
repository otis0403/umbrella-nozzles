import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'cad/HeadOnly_16mm_Optimization.blend'))
r=json.loads((ROOT/'cad/geometry_checks.json').read_text(encoding='utf-8'))
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-8
checks=[]
for part in r['parts']:
    ob=bpy.data.objects[part['name']];vertices=[ob.matrix_world@v.co for v in ob.data.vertices]
    bounds=[[min(v[i] for v in vertices) for i in range(3)],[max(v[i] for v in vertices) for i in range(3)]]
    assert all(abs(bounds[j][i]-part['assembly_bounds_mm'][j][i])<.001 for i in range(3) for j in range(2))
    checks.append({'part':ob.name,'assembly_bounds_mm':bounds,'matches_delivered_STL_bounds':True})
(ROOT/'cad/native_blend_reopen_checks.json').write_text(json.dumps({'native_blend_reopened':True,'unit_scale':.001,'parts':checks},indent=2),encoding='utf-8')
print('NATIVE_BLEND_REOPEN_VERIFIED',flush=True)
