"""Independent read-back of every delivered STL and standard 3MF model."""
import hashlib,json,zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from geometry import ROOT

geo=json.loads((ROOT/'cad'/'geometry_checks.json').read_text())
ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
checks=[]
for r in geo['parts']:
    path=ROOT/'print'/'STL'/(r['name']+'_mm.stl')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['stl_sha256'],path
    tm=trimesh.load_mesh(path,process=True)
    assert tm.is_watertight and tm.is_winding_consistent and tm.volume>0
    assert len(tm.split(only_watertight=False))==1
    assert (tm.area_faces>1e-10).all()
    assert np.allclose(tm.extents,r['print_size_mm'],atol=1e-4)
    checks.append({'file':str(path.relative_to(ROOT)),'closed_single_solid':True,'matches_CAD_hash':True})
for path in sorted((ROOT/'print').rglob('*.3mf')):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        root=ET.fromstring(z.read('3D/3dmodel.model'))
    assert root.get('unit')=='millimeter'
    objects={}
    for ob in root.findall('m:resources/m:object',ns):
        vs=np.array([[float(v.get(k)) for k in ['x','y','z']] for v in ob.findall('m:mesh/m:vertices/m:vertex',ns)])
        fs=np.array([[int(v.get(k)) for k in ['v1','v2','v3']] for v in ob.findall('m:mesh/m:triangles/m:triangle',ns)])
        tm=trimesh.Trimesh(vs,fs,process=True)
        assert tm.is_watertight and tm.is_winding_consistent and tm.volume>0,path
        assert len(tm.split(only_watertight=False))==1,path
        original=next(r for r in geo['parts'] if r['name']==ob.get('name'))
        assert np.allclose(tm.extents,original['print_size_mm'],atol=1e-4)
        assert abs(tm.volume/original['volume_mm3']-1)<2e-5
        objects[ob.get('id')]=(tm,ob.get('name'))
    for item in root.findall('m:build/m:item',ns):
        tm,name=objects[item.get('objectid')]
        t=np.array([float(x) for x in item.get('transform').split()]).reshape(4,3)
        transformed=tm.vertices@t[:3,:]+t[3,:]
        lo=transformed.min(0);hi=transformed.max(0)
        assert (lo[:2]>=5-1e-6).all() and (hi[:2]<=215+1e-6).all()
        assert lo[2]>=-1e-6 and hi[2]<=240.001
    checks.append({'file':str(path.relative_to(ROOT)),'model_count':len(objects),
        'roundtrip_volume_and_dimensions_match_STL':True,'closed_single_solids':True,
        'within_K1C_allowing_5mm_brim':True})
(ROOT/'print'/'independent_readback_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('STL_AND_3MF_READBACK_COMPLETE',len(checks),flush=True)
