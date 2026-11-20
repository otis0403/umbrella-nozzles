import bpy,json,math,ast,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
CASE=ROOT.parent
report=json.loads((ROOT/'vertical_layout_checks.json').read_text(encoding='utf8'))
preserved=report['preserved_mesh_hashes'];shape_hashes=report['original_part_geometry_hashes']
SOURCE=Path(report['source']);source_hash=report['source_sha256']
DEST=ROOT/'完整模型_垂直上管_後殼加深800mm.blend'
helpers_path=CASE/'整機整合_三路51mm_150x16_20261116/integrate_latest.py'
lib={'__file__':str(helpers_path),'__name__':'geometry_helpers'}
syntax=ast.parse(helpers_path.read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in syntax.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign))],type_ignores=[]),'geometry_helpers','exec'),lib)
script=(ROOT/'build_vertical_assembly.py').read_text(encoding='utf-8-sig')
syntax=ast.parse(script)
function=next(n for n in syntax.body if isinstance(n,ast.FunctionDef) and n.name=='mesh_hash')
exec(compile(ast.Module(body=[function],type_ignores=[]),'mesh_hash','exec'),globals())
start=script.rindex('\nbpy.ops.wm.open_mainfile(filepath=str(DEST))')+1
exec(compile(script[start:],'native_verification_and_delivery','exec'),globals())
# Inspect the male connector across an intact section after independent reopen.
origin=Vector((0,110,125));radii=[]
for sign in [-1,1]:
    direction=Vector((sign,0,0))
    inner=tree.ray_cast(origin,direction,50)
    outer=tree.ray_cast(inner[0]+.001*direction,direction,10)
    radii.append(inner[3]+.001+outer[3])
assert abs(sum(radii)-55)<.03
verification['elbow_male_OD_mm']=sum(radii)
verification['elbow_male_to_nozzle_diameter_clearance_mm']=55.4-sum(radii)
(ROOT/'native_reopen_checks.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf8')
manifest=json.loads((ROOT/'delivery_manifest.json').read_text(encoding='utf8'))
manifest['native_reopen_checks.json']=lib['digest'](ROOT/'native_reopen_checks.json')
(ROOT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
assert all(lib['digest'](ROOT/name)==value for name,value in manifest.items())
assert lib['digest'](SOURCE)==source_hash
print('FINAL_NATIVE_AND_DELIVERY_CHECKS_PASSED',json.dumps({'male_OD_mm':sum(radii),'files_verified':len(manifest),'folder':str(ROOT)},ensure_ascii=False),flush=True)
