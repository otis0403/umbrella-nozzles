import hashlib
import json
import math
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import manifold3d as m

ROOT=Path(__file__).resolve().parent
CFD=ROOT.parent/'InnerMiddle_12_14_8_ANSYS_20261117'
SOURCE=CFD/'modular'
sys.path.insert(0,str(CFD))
import design
from build_parts import ring
from cad_utils import loft,box,cylinder,mesh,save3mf
design.GAP=8
for name in ['STL','3MF','images','cad']:(ROOT/name).mkdir(parents=True,exist_ok=True)

def load(path,matrix=None):
    tri=trimesh.load_mesh(path,process=True)
    if matrix is not None:tri.apply_transform(matrix)
    solid=m.Manifold(m.Mesh64(np.asarray(tri.vertices,np.float64),np.asarray(tri.faces,np.uint64)))
    assert solid.status()==m.Error.NoError
    return solid
def slot(d,extra,z0,z1,x,y):
    result=cylinder(d,z1-z0,[x,y-extra/2,(z0+z1)/2],segments=64)
    if extra:
        result+=cylinder(d,z1-z0,[x,y+extra/2,(z0+z1)/2],segments=64)
        result+=box([x-d/2,y-extra/2,z0],[x+d/2,y+extra/2,z1])
    return result
def circle(d,z,x,y):
    a=np.linspace(0,2*np.pi,64,endpoint=False)
    return np.c_[x+d/2*np.cos(a),y+d/2*np.sin(a),np.full(64,z)]
def flange(z0,z1):
    outer=loft([ring(90,60,6,z) for z in [z0,z1]])
    zs=np.linspace(z0-.1,z1+.1,17)
    inner=loft([ring(w+.1,d+.1,r+.05,z) for z in zs for w,d,r in [design.profile(z,315,320,'ramp')]])
    return outer-inner

body_path=SOURCE/'STL/outer_body_mm.stl';tip_path=SOURCE/'STL/outer_tip_g8_mm.stl'
source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [body_path,tip_path]}
assert source_hashes[str(body_path)]=='bb1d7d3d2a9292830031f4f97664a4739c9830616458d7d7a0fb275a876fcab2'
assert source_hashes[str(tip_path)]=='444a71cd1a7dfb88ab8c5ae28de9032b9008e318544a1bfd6333c650dcf12a72'
body=load(body_path);tip=load(tip_path)
cut=55.
lower=body^box([-1000,-1000,-1],[1000,1000,cut])
original_upper=body^box([-1000,-1000,cut],[1000,1000,500])
upper=original_upper
lower+=flange(cut-4,cut);upper+=flange(cut,cut+4)
positions=[(x,y) for x in [-18,18] for y in [-35,35]]
for i,(x,y) in enumerate(positions):
    if i in [0,3]:
        lower+=loft([circle(d,z,x,y) for d,z in [(7.4,cut-.2),(7.4,cut+1.2),(7,cut+1.5)]])
    lower-=slot(4.4,0,cut-5,cut+2.5,x,y)
    upper-=slot(4.4,0 if i==0 else 1,cut-1,cut+5,x,y)
    if i in [0,3]:upper-=slot(7.9,0 if i==0 else 1,cut-.1,cut+1.8,x,y)
w,d,r=design.profile(cut,315,320,'ramp')
outer_groove=loft([ring(w+3.6,d+3.6,r+1.8,z) for z in [cut-.5,cut+.1]])
inner_groove=loft([ring(w+1.2,d+1.2,r+.6,z) for z in [cut-.6,cut+.2]])
lower-=outer_groove-inner_groove
assert abs((original_upper-upper).volume())<.01,'Original guide/body material removed'

angle=math.pi/4
rotation=np.array([[math.cos(angle),-math.sin(angle),0,0],[math.sin(angle),math.cos(angle),0,0],[0,0,1,0],[0,0,0,1.]])
records=[]
for name,solid,z_origin,assembly_z in [('inlet_lower',lower,0,0),('guided_upper',upper,55,0),('front_tip_g8',tip,0,345)]:
    tri=mesh(solid.simplify(.0001))
    transform=rotation.copy();shift=np.eye(4);shift[2,3]=-z_origin;transform=transform@shift
    tri.apply_transform(transform)
    quantized=np.asarray(tri.vertices,np.float32).astype(np.float64)
    rebuilt=m.Manifold(m.Mesh64(quantized,np.asarray(tri.faces,np.uint64)))
    assert rebuilt.status()==m.Error.NoError
    tri=mesh(rebuilt.simplify(.00005))
    stl=ROOT/'STL'/(name+'_K2Pro_mm.stl');tri.export(stl)
    reread=trimesh.load_mesh(stl,process=True)
    assert reread.is_watertight and reread.is_winding_consistent and reread.volume>0
    assert len(reread.split(only_watertight=False))==1 and reread.area_faces.min()>1e-10
    assert (reread.extents[:2]+16<300).all() and reread.bounds[0,2]>-.001 and reread.bounds[1,2]<=294
    assembly=np.linalg.inv(transform);assembly[2,3]+=assembly_z
    model=ROOT/'3MF'/(name+'_K2Pro_300mm.3mf')
    save3mf(model,reread.vertices,reread.faces,name,translate=(150,150,0))
    with zipfile.ZipFile(model) as z:
        assert z.testzip() is None
        xml=ET.fromstring(z.read('3D/3dmodel.model'))
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    assert xml.attrib['unit']=='millimeter'
    vv=np.array([[float(v.attrib[a]) for a in ['x','y','z']] for v in xml.findall('.//m:vertex',ns)])
    ff=np.array([[int(f.attrib[a]) for a in ['v1','v2','v3']] for f in xml.findall('.//m:triangle',ns)])
    item=xml.find('m:build/m:item',ns);matrix=np.array([float(a) for a in item.attrib['transform'].split()])
    placed=vv@matrix[:9].reshape(3,3)+matrix[9:]
    bounds=np.array([placed.min(0),placed.max(0)])
    assert (bounds[0,:2]-8>=0).all() and (bounds[1,:2]+8<=300).all() and bounds[1,2]<300
    xml_mesh=trimesh.Trimesh(vv,ff,process=True)
    assert xml_mesh.is_watertight and abs(xml_mesh.volume/reread.volume-1)<1e-5
    row={'id':name,'STL':str(stl),'3MF':str(model),'print_size_mm':reread.extents.tolist(),
         'placed_3MF_bounds_mm':bounds.tolist(),'XY_space_with_8mm_brim_mm':(reread.extents[:2]+16).tolist(),
         'Z_margin_mm':300-float(reread.bounds[1,2]),'assembly_from_print':assembly.tolist(),
         'watertight_single_positive_solid':True,'minimum_triangle_area_mm2':float(reread.area_faces.min()),
         'STL_sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'3MF_sha256':hashlib.sha256(model.read_bytes()).hexdigest()}
    records.append(row);print('PRINT_PART_VERIFIED',json.dumps(row),flush=True)

assembled_lower=load(Path(records[0]['STL']),np.array(records[0]['assembly_from_print']))
assembled_upper=load(Path(records[1]['STL']),np.array(records[1]['assembly_from_print']))
assembled_tip=load(Path(records[2]['STL']),np.array(records[2]['assembly_from_print']))
overlaps={'new_body_joint':abs((assembled_lower^assembled_upper).volume()),'existing_tip_joint':abs((assembled_upper^assembled_tip).volume())}
assert max(overlaps.values())<.01,overlaps
assembled_body=assembled_lower+assembled_upper
probe=loft([ring(pw-.1,pd-.1,max(pr-.05,.01),z) for z in np.linspace(cut-6,cut+6,49)
            for pw,pd,pr in [design.profile(z,315,320,'ramp')]])
added_flow=abs(((assembled_body-body)^probe).volume())
removed_flow=abs(((body-assembled_body)^probe).volume())
assert added_flow<1 and removed_flow<1,(added_flow,removed_flow)
missing_upper=abs((original_upper-assembled_upper).volume())
assert missing_upper<max(.01,original_upper.volume()*1e-5),missing_upper
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in source_hashes.items())
result={'printer':'Creality K2 Pro','build_volume_mm':[300,300,300],'rotation_Z_deg':45,'brim_space_each_side_mm':8,
        'split_Z_mm':55,'guides_start_Z_mm':55,'guides_split':False,'new_joint_nominal_flow_mm':[w,d,r],
        'new_joint_screw_centers_XY_mm':[list(p) for p in positions],'new_joint_screws':'4 x M4x16 + nuts + 8 washers',
        'new_joint_flange_mm':[90,60,4],'source_hashes_unchanged':source_hashes,'parts':records,
        'assembly_overlap_mm3':overlaps,'added_material_in_joint_flow_probe_mm3':added_flow,
        'removed_material_in_joint_flow_probe_mm3':removed_flow,'original_upper_material_missing_mm3':missing_upper,
        'physical_fit_slicing_print_and_sealing_verified':False,'existing_tip_geometry_preserved_by_rigid_transform':True}
(ROOT/'print_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('K2PRO_SPLIT_AND_PRINT_VOLUME_VERIFIED',flush=True)
