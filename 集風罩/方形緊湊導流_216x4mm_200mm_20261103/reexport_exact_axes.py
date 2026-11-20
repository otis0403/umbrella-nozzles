"""Export the unchanged saved mesh with exact 90-degree axis permutations."""
from pathlib import Path
import bpy,json,struct,hashlib
from mathutils import Vector
HERE=Path(__file__).resolve().parent
report=json.loads((HERE/'模型幾何檢查.json').read_text(encoding='utf-8'))
SOURCE=HERE/report['blend_file']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
parts=sorted((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:o.name)
for obj,part,side in zip(parts,report['parts'],[-1,1]):
    coords=[Vector((v.co.x,-side*v.co.z,side*v.co.y)) for v in obj.data.vertices]
    obj.data.calc_loop_triangles();path=HERE/part['file']
    with path.open('wb') as f:
        f.write(b'Compact rectangular guided nozzle, exact axis permutation, mm'.ljust(80,b' '))
        f.write(struct.pack('<I',len(obj.data.loop_triangles)))
        for t in obj.data.loop_triangles:
            a,b,c=[coords[i] for i in t.vertices];n=(b-a).cross(c-a).normalized()
            f.write(struct.pack('<12fH',*n,*a,*b,*c,0))
    lo=[min(p[k] for p in coords) for k in range(3)];hi=[max(p[k] for p in coords) for k in range(3)]
    part['sha256']=sha(path);part['print_size_mm']=[hi[k]-lo[k] for k in range(3)];part['minimum_print_Z_mm']=lo[2]
assert sha(SOURCE)==digest
report['STL_export_note']='Exact +/-90 degree coordinate permutation; no XY recentering; assembly mesh unchanged'
(HERE/'模型幾何檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('EXACT_AXIS_STL_REEXPORTED',flush=True)
