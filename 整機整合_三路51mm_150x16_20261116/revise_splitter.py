import json, hashlib
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent
source=ROOT.parent/'ThreeWay150_51mm_System_20261114/print/STL/splitter_H110_neck46_mm.stl'
out=ROOT/'print/STL/splitter_center_neck_plus10_mm.stl'
out.parent.mkdir(parents=True,exist_ok=True)
mesh=trimesh.load_mesh(source,process=True)
original=mesh.vertices.copy()
mask=(np.abs(original[:,0])<=25.01)&(original[:,2]>85.0001)
assert mask.any()
mesh.vertices[mask,2]=85+(mesh.vertices[mask,2]-85)*1.4
assert np.array_equal(mesh.vertices[~mask],original[~mask])
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
assert len(mesh.split())==1
mesh.export(out)
readback=trimesh.load_mesh(out,process=True)
assert readback.is_watertight and readback.is_winding_consistent and readback.volume>0
assert len(readback.split())==1
assert abs(readback.bounds[1,2]-120)<.001
report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'output':str(out),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
    'change':'center circular spigot stretched from 25 to 35 mm above z=85 mm; side ports and lower body identical',
    'center_tip_height_mm':120,'side_tip_axis_height_mm':98,'center_neck_length_mm':35,
    'nominal_hose_insertion_mm':25,'center_uncovered_neck_mm':10,
    'bounds_mm':readback.bounds.tolist(),'watertight_single_solid':True,'winding_consistent':True,
    'unchanged_vertices_outside_center_neck':True,'modified_vertices':int(mask.sum())}
(ROOT/'splitter_revision_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('CENTER_NECK_REVISION_VERIFIED',json.dumps(report,ensure_ascii=False),flush=True)
