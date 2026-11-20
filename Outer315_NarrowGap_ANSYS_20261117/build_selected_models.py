import hashlib
import json
import numpy as np
import trimesh
import manifold3d as manifold
import design
from design import ROOT,write_json
from build_parts import full_nozzle
from guide_geometry import plate_ring,limits
from cad_utils import loft,mesh

selection=json.loads((ROOT/'selection.json').read_text())
gap=selection['outer']['gap_mm'];design.GAP=gap
solid=full_nozzle(315,320,'ramp')
start,end=limits(320);zs=np.unique(np.r_[np.linspace(start,end,round(end-start)+1),start+15,end-15])
for k in range(2):solid+=loft([plate_ring(z,315,320,k) for z in zs])
original=mesh(solid.simplify(.001))
quantized=np.asarray(original.vertices,dtype=np.float32).astype(np.float64)
rebuilt=manifold.Manifold(manifold.Mesh64(quantized,np.asarray(original.faces,dtype=np.uint64)))
assert rebuilt.status()==manifold.Error.NoError
target=ROOT/'cad/full'/f'nozzle_W315_G{gap}_L320_ramp_guided_mm.stl'
mesh(rebuilt.simplify(.001)).export(target)
rows=[]
for key in ['inner','center','outer']:
    spec=selection[key];w=spec['width_mm'];g=spec['gap_mm'];L=spec['length_mm']
    suffix='_guided' if key=='outer' else ''
    path=ROOT/'cad/full'/f'nozzle_W{w}_G{g}_L{L}_ramp{suffix}_mm.stl'
    part=trimesh.load_mesh(path,process=True)
    assert part.is_watertight and part.is_winding_consistent and part.volume>0
    assert len(part.split(only_watertight=False))==1 and part.area_faces.min()>1e-10
    rows.append({'position':key,'width_mm':w,'gap_mm':g,'file':str(path),'size_mm':part.extents.tolist(),
                 'watertight_single_positive_solid':True,'minimum_triangle_area_mm2':float(part.area_faces.min()),
                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
write_json(ROOT/'cad/selected_STL_checks.json',rows)
print('MIXED_GAP_MODELS_VERIFIED',json.dumps(rows),flush=True)
