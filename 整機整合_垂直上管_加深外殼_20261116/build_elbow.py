import sys,json,math,hashlib
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'ThreeWay150_51mm_System_20261114'))
from cad_utils import loft,mesh,box,cylinder

def ring(p,d,r):
    p=np.asarray(p,float);d=np.asarray(d,float)
    x=np.array([1.,0.,0.]);y=np.cross(d,x)
    a=np.linspace(0,2*math.pi,160,endpoint=False)
    return p+r*(np.cos(a)[:,None]*x+np.sin(a)[:,None]*y)

R=90.;outer=[];inner=[]
for z,r in [(0,30.1),(25,30.1),(35,27.9)]:outer.append(ring([0,0,z],[0,0,1],r))
for z,r in [(-.2,28.3),(0,28.3),(1.2,27.7),(25,27.7),(25,25.5),(35,25.5)]:inner.append(ring([0,0,z],[0,0,1],r))
for a in np.linspace(0,math.pi/2,181)[1:]:
    p=[0,R*(1-math.cos(a)),35+R*math.sin(a)]
    d=[0,math.sin(a),math.cos(a)]
    outer.append(ring(p,d,27.9));inner.append(ring(p,d,25.5))
for t,r in [(5,27.5),(29,27.5),(30,27.1)]:outer.append(ring([0,R+t,125],[0,1,0],r))
inner.append(ring([0,120.2,125],[0,1,0],25.5))
solid=loft(outer)-loft(inner)
slots=box([-40,-1,-.2],[40,1,19])+cylinder(2,80,[0,0,19],axis='x',segments=64)
solid=solid-slots
assert len(solid.decompose())==1
part=mesh(solid.simplify(.001));path=ROOT/'print/STL/elbow_90deg_R90_ID51_socket55p4_spigot55_mm.stl'
part.export(path)
check=trimesh.load_mesh(path,process=True)
assert check.is_watertight and check.is_winding_consistent and check.volume>0
assert len(check.split(only_watertight=False))==1 and check.area_faces.min()>1e-10
assert (check.extents[:2]+10<=220).all() and check.extents[2]<=250
record={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'print_size_mm':check.extents.tolist(),
    'watertight_single_solid':True,'positive_volume_mm3':float(check.volume),'triangles':len(check.faces),
    'flow_ID_mm':51,'centerline_radius_mm':90,'turn_degrees':90,'female_ID_mm':55.4,'female_depth_mm':25,
    'male_OD_mm':55,'male_insertion_mm':25,'main_wall_mm':2.4,'male_wall_mm':2,
    'interface_origin_for_nozzle_mm':[0,95,125],'quantity':6,'K1C_space_plus_5mm_brim_checked':True,
    'actual_slicing_and_fit_verified':False}
(ROOT/'elbow_geometry_checks.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('ELBOW_GEOMETRY_VERIFIED',json.dumps(record,ensure_ascii=False),flush=True)
