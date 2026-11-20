import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
CASE=ROOT.parent
source=CASE/'完整模型.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':{'system':bpy.context.scene.unit_settings.system,'scale':bpy.context.scene.unit_settings.scale_length},'objects':[]}
for ob in bpy.context.scene.objects:
    points=[ob.matrix_world@Vector(c) for c in ob.bound_box]
    entry={'name':ob.name,'type':ob.type,'location':list(ob.location),'dimensions':list(ob.dimensions),'matrix':[list(r) for r in ob.matrix_world],'bounds':[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]],'hide_render':ob.hide_render}
    if ob.type=='MESH':
        entry.update(vertices=len(ob.data.vertices),faces=len(ob.data.polygons),materials=[m.name if m else None for m in ob.data.materials])
        if len(ob.data.vertices)<300:
            entry['world_vertices']=[list(ob.matrix_world@v.co) for v in ob.data.vertices]
    report['objects'].append(entry)
(ROOT/'source_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('SOURCE_INSPECTION_BEGIN')
for ob in report['objects']:
    print(json.dumps({k:v for k,v in ob.items() if k not in ['world_vertices','matrix']},ensure_ascii=False))
print('SOURCE_INSPECTION_DONE')
