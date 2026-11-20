import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;r=json.loads((ROOT/'cad/geometry_checks.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'cad/ThreeWay150_51mm_System.blend'))
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-8
checks=[]
for part in r['parts']:
    ob=bpy.data.objects[part['name']];local=[[min(v.co[i] for v in ob.data.vertices) for i in range(3)],[max(v.co[i] for v in ob.data.vertices) for i in range(3)]]
    assert all(abs(local[j][i]-part['assembly_bounds_mm'][j][i])<.002 for i in range(3) for j in range(2))
    checks.append(dict(part=ob.name,STL_dimensions_match_native_model=True))
(ROOT/'cad/native_reopen_checks.json').write_text(json.dumps(dict(native_blend_reopened=True,scale_length=.001,parts=checks),indent=2),encoding='utf-8')
print('NATIVE_BLEND_REOPEN_COMPLETE',flush=True)
