import hashlib,json,zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from geometry import ROOT
ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
geo=json.loads((ROOT/'cad/geometry_checks.json').read_text());checks=[]
for part in geo['parts']:
    path=ROOT/'print/STL'/(part['name']+'_mm.stl');assert hashlib.sha256(path.read_bytes()).hexdigest()==part['sha256']
    tm=trimesh.load_mesh(path,process=True);assert tm.is_watertight and tm.is_winding_consistent and tm.volume>0 and tm.area_faces.min()>1e-10
    assert len(tm.split(only_watertight=False))==1 and np.allclose(tm.extents,part['print_size_mm'],atol=1e-4)
    with zipfile.ZipFile(ROOT/'print/3MF'/(part['name']+'.3mf')) as z:
        assert z.testzip() is None;root=ET.fromstring(z.read('3D/3dmodel.model'))
    assert root.get('unit')=='millimeter'
    ob=root.find('m:resources/m:object',ns);vertices=np.array([[float(v.get(k)) for k in ['x','y','z']] for v in ob.findall('m:mesh/m:vertices/m:vertex',ns)])
    faces=np.array([[int(v.get(k)) for k in ['v1','v2','v3']] for v in ob.findall('m:mesh/m:triangles/m:triangle',ns)])
    solid=trimesh.Trimesh(vertices,faces,process=True);assert solid.is_watertight and len(solid.split(only_watertight=False))==1
    assert abs(solid.volume/tm.volume-1)<2e-5
    transform=np.array([float(x) for x in root.find('m:build/m:item',ns).get('transform').split()]).reshape(4,3)
    v=vertices@transform[:3]+transform[3];assert (v[:,:2].min(0)>=5).all() and (v[:,:2].max(0)<=215).all() and v[:,2].max()<=250
    checks.append(dict(part=part['name'],STL_hash_matches=True,STL_and_3MF_closed_single_solids=True,volume_and_dimensions_match=True,within_K1C_with_5mm_brim=True))
(ROOT/'print/independent_readback_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('PRINT_READBACK_COMPLETE',len(checks),flush=True)
