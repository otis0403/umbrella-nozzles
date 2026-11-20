import json
import hashlib
import trimesh
from design import ROOT, write_json
rows=[]
for width,length,suffix in [(225,220,''),(180,180,''),(315,320,'_guided')]:
    path=ROOT/'cad/full'/f'nozzle_W{width}_G16_L{length}_ramp{suffix}_mm.stl'
    model=trimesh.load_mesh(path,process=True)
    minimum=float(model.area_faces.min())
    assert model.is_watertight and model.is_winding_consistent and model.volume>0
    assert len(model.split(only_watertight=False))==1 and minimum>1e-10
    rows.append({'width_mm':width,'size_mm':model.extents.tolist(),'minimum_triangle_area_mm2':minimum,
                 'positive_single_solid':True,'watertight':True,'volume_mm3':float(model.volume),
                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
write_json(ROOT/'cad/selected_STL_independent_checks.json',rows)
print(json.dumps(rows,indent=2),flush=True)
