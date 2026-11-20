"""Complete 315 mm nozzle with two integrated 1.6 mm guide plates."""
import hashlib
import json
import numpy as np
import trimesh
import manifold3d as manifold

from design import ROOT, height, write_json
from guide_geometry import plate_ring, limits
from build_parts import full_nozzle
from cad_utils import loft, mesh

width,length=315,320
solid=full_nozzle(width,length,'ramp')
start,end=limits(length)
zs=np.unique(np.r_[np.linspace(start,end,round(end-start)+1),start+15,end-15])
for index in range(2):
    solid+=loft([plate_ring(z,width,length,index) for z in zs])
assert len(solid.decompose())==1
tri=mesh(solid.simplify(.001))
quantized=np.asarray(tri.vertices,dtype=np.float32).astype(np.float64)
rebuilt=manifold.Manifold(manifold.Mesh64(quantized,np.asarray(tri.faces,dtype=np.uint64)))
assert rebuilt.status()==manifold.Error.NoError
tri=mesh(rebuilt.simplify(.001))
out=ROOT/'cad/full/nozzle_W315_G16_L320_ramp_guided_mm.stl'
tri.export(out)
reread=trimesh.load_mesh(out,process=True)
assert reread.is_watertight and reread.is_winding_consistent and reread.volume>0
assert len(reread.split(only_watertight=False))==1
assert max(abs(reread.extents-np.array([60.2,319.8,388])))<.01
record={'width_mm':width,'gap_mm':16,'transition_length_mm':length,'height_mm':height(length),
        'profile_kind':'ramp','guide_count':2,'guide_nominal_thickness_mm':1.6,'guide_tip_thickness_mm':.8,
        'guide_axial_limits_mm':[start,end],'unpartitioned_outlet_length_mm':56,
        'full_reference_STL':str(out),'socket_ID_mm':55.4,'flow_ID_mm':51,
        'size_mm':reread.extents.tolist(),'closed_single_solid':True,
        'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'physical_fit_verified':False}
write_json(ROOT/'cad/nozzle_W315_G16_L320_ramp_guided_checks.json',record)
print('GUIDED_COMPLETE_NOZZLE_VERIFIED',json.dumps(record),flush=True)
