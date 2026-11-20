import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'整機整合_三路51mm_150x16_20261116/完整模型_中央弧線_三路51mm_150x16.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
shell=bpy.data.objects['Cube'];shell.data.calc_loop_triangles()
vertices=[shell.matrix_world@v.co for v in shell.data.vertices]
tr=BVHTree.FromPolygons(vertices,[tuple(t.vertices) for t in shell.data.loop_triangles],all_triangles=True)
rows=[]
for ob in bpy.context.scene.objects:
    if not ob.name.startswith('小型集風罩_'):continue
    mouth=ob.matrix_world@Vector((0,0,188))
    tangent=ob.matrix_world.to_3x3().col[1].normalized()
    direction=tangent.cross(Vector((0,0,1))).normalized()
    rays=[]
    for height in [mouth.z,62.5,75]:
        p=Vector((mouth.x,mouth.y,height))
        for sign in [-1,1]:
            hit=tr.ray_cast(p,sign*direction,150)
            rays.append({'z_cm':height,'direction_sign':sign,'hit_cm':list(hit[0]) if hit[0] else None,'distance_cm':hit[3]})
    rows.append({'name':ob.name,'mouth_cm':list(mouth),'forward':list(direction),'rays':rays})
report={'units_scale':bpy.context.scene.unit_settings.scale_length,'outlets':rows}
(ROOT/'orientation_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HORIZONTAL_ORIENTATION_INSPECTION',json.dumps(report,ensure_ascii=False),flush=True)
