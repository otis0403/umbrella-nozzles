import hashlib
import json
import numpy as np
import trimesh
import manifold3d as manifold
import design
from design import ROOT,write_json
from build_parts import full_nozzle
from cad_utils import mesh

selection=json.loads((ROOT/'selection.json').read_text())
for key in ['inner','center']:
    spec=selection[key];design.GAP=spec['gap_mm']
    solid=full_nozzle(spec['width_mm'],spec['length_mm'],'ramp')
    original=mesh(solid.simplify(.001))
    quantized=np.asarray(original.vertices,dtype=np.float32).astype(np.float64)
    rebuilt=manifold.Manifold(manifold.Mesh64(quantized,np.asarray(original.faces,dtype=np.uint64)))
    assert rebuilt.status()==manifold.Error.NoError
    target=ROOT/'cad/full'/f"nozzle_W{spec['width_mm']}_G{spec['gap_mm']}_L{spec['length_mm']}_ramp_mm.stl"
    mesh(rebuilt.simplify(.001)).export(target)
rows=[]
for key in ['inner','center','outer']:
    spec=selection[key];w=spec['width_mm'];g=spec['gap_mm'];L=spec['length_mm'];suffix='_guided' if key=='outer' else ''
    path=ROOT/'cad/full'/f'nozzle_W{w}_G{g}_L{L}_ramp{suffix}_mm.stl'
    part=trimesh.load_mesh(path,process=True)
    assert part.is_watertight and part.is_winding_consistent and part.volume>0
    assert len(part.split(only_watertight=False))==1 and part.area_faces.min()>1e-10
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if key=='outer':assert digest=='0f76ae2e12f1f269beaad7fceb69eda281e676a1572df9bd89fe97240e360dd8'
    rows.append({'position':key,'width_mm':w,'gap_mm':g,'file':str(path),'size_mm':part.extents.tolist(),
                 'watertight_single_positive_solid':True,'minimum_triangle_area_mm2':float(part.area_faces.min()),'sha256':digest})
write_json(ROOT/'cad/selected_STL_checks.json',rows)
print('MODELS_VERIFIED',json.dumps(rows),flush=True)
