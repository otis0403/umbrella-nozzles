import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'整機整合_水平吹向圓弧_20261116/完整模型_吹嘴水平朝圓弧_150x16.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
ob=bpy.data.objects['Cube'];world=[ob.matrix_world@v.co for v in ob.data.vertices]
rear=[i for i,p in enumerate(world) if abs(p.y+25)<.001]
record={'rear_plane_vertex_count':len(rear),'rear_points_cm':[list(world[i]) for i in rear],
    'modifiers':[(m.name,m.type) for m in ob.modifiers],'object_parent':ob.parent.name if ob.parent else None,
    'bounds_cm':[[min(p[i] for p in world) for i in range(3)],[max(p[i] for p in world) for i in range(3)]]}
(ROOT/'shell_rear_inspection.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('REAR_SHELL_INSPECTION',json.dumps({k:v for k,v in record.items() if k!='rear_points_cm'},ensure_ascii=False),flush=True)
