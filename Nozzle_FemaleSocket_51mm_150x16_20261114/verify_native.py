import bpy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
geo=json.loads((ROOT/'cad/geometry_checks.json').read_text(encoding='utf-8'));part=geo['parts'][0]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'cad/Nozzle_female_socket_55p4.blend'))
ob=bpy.data.objects[part['name']];scale=bpy.context.scene.unit_settings.scale_length
assert math.isclose(scale,.001,abs_tol=1e-9)
assert max(abs(ob.dimensions[i]-part['print_size_mm'][i]) for i in range(3))<.001
(ROOT/'cad/native_reopen_checks.json').write_text(json.dumps(dict(native_blend_reopened=True,dimensions_match_STL=True,
    scale_length=scale,scale_comparison_absolute_tolerance=1e-9),indent=2),encoding='utf-8')
print('FEMALE_NATIVE_REOPEN_VERIFIED',flush=True)
