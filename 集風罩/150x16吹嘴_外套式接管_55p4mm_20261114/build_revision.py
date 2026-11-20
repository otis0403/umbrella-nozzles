"""Separate female-socket prototype. Millimetres; no original file mutations."""
import sys,json,math,hashlib,shutil,zipfile
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'ThreeWay150_51mm_System_20261114'
sys.path.insert(0,str(ROOT/'dependencies' if (ROOT/'dependencies').exists() else BASE))
from geometry import smooth,cross_grid,boundary
from cad_utils import loft,cylinder,box,mesh,save3mf

SOCKET=55.4;WALL=2.4;INSERT=25.;H=188.;FLOW=51.

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def profile(z):
    if z<=25:return FLOW,FLOW,FLOW/2
    a0=math.pi*(FLOW/2)**2;a1=150*22-(4-math.pi)*3**2
    if z<=145:
        q=float(smooth((z-25)/120));w=FLOW+(150-FLOW)*q;r=FLOW/2+(3-FLOW/2)*q
        area=a0+(a1-a0)*q;d=(area+(4-math.pi)*r*r)/w
        if r>d/2:
            alpha=1-math.pi/4;d=2*area/(w+math.sqrt(w*w-4*alpha*area));r=d/2
        return w,d,r
    q=float(smooth((z-145)/35));r=3+(.8-3)*q
    area=a1+(150*16-(4-math.pi)*.8**2-a1)*q
    return 150,(area+(4-math.pi)*r*r)/150,r

def ring(w,d,r,z):return np.c_[boundary(cross_grid(w,d,r,64,64)),np.full(256,z)]

def nozzle():
    zs=np.unique(np.r_[np.linspace(0,H,377),25,35,145,180])
    outside=[]
    for z in zs:
        if z<=25:w=d=SOCKET+2*WALL;r=w/2
        else:
            w,d,r=profile(z);wall=2+.4*float(smooth((H-z-8)/5))
            extra=(SOCKET-FLOW)*(1-float(smooth((z-25)/10)))
            w+=2*wall+extra;d+=2*wall+extra;r+=wall+extra/2
        outside.append(ring(w,d,r,z))
    upper=loft([ring(*profile(z),z) for z in np.r_[24.999,np.linspace(25,H,327),H+.1]])
    # Lead-in chamfer: diameter +1.2 at the open end, nominal by z=1.2.
    cavity=loft([ring(d,d,d/2,z) for z,d in [(-.1,SOCKET+1.2),(0,SOCKET+1.2),(1.2,SOCKET),(25,SOCKET)]])
    solid=loft(outside)-(upper+cavity)
    # Two short clamp relief slots, open below; rounded ends at z=20.
    slots=box([-40,-1,-.2],[40,1,19])+cylinder(2,80,[0,0,19],axis='x',segments=64)
    return solid-slots

def coupon(d):
    outer=cylinder(d+2*WALL,10,[0,0,5],segments=192)
    cut=loft([ring(v,v,v/2,z) for z,v in [(-.1,d+1.2),(0,d+1.2),(1.2,d),(10.1,d)]])
    return outer-cut

def export(solid,name,kind):
    assert len(solid.decompose())==1
    original=mesh(solid.simplify(.001))
    quantized=np.asarray(original.vertices,dtype=np.float32).astype(np.float64)
    rebuilt=m.Manifold(m.Mesh64(quantized,np.asarray(original.faces,dtype=np.uint64)))
    assert rebuilt.status()==m.Error.NoError
    out=mesh(rebuilt.simplify(.001));stl=ROOT/'print/STL'/(name+'_mm.stl');out.export(stl)
    read=trimesh.load_mesh(stl,process=True)
    assert read.is_watertight and read.is_winding_consistent and read.volume>0
    assert len(read.split(only_watertight=False))==1 and read.area_faces.min()>1e-10
    assert (read.extents[:2]+10<=220).all() and read.extents[2]<=250
    save3mf(ROOT/'print/3MF'/(name+'.3mf'),read.vertices,read.faces,name,(110,110,0))
    record=dict(name=name,kind=kind,print_size_mm=read.extents.tolist(),volume_mm3=float(read.volume),triangles=len(read.faces),
        minimum_triangle_area_mm2=float(read.area_faces.min()),closed_single_solid=True,sha256=digest(stl),independent_STL_readback=True)
    print('PART_VERIFIED',json.dumps(record),flush=True)
    return record

def verify_3mf(path,quantity=1):
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None;root=ET.fromstring(z.read('3D/3dmodel.model'))
    assert root.get('unit')=='millimeter'
    objects={}
    for obj in root.findall('m:resources/m:object',ns):
        v=np.array([[float(p.get(k)) for k in ['x','y','z']] for p in obj.findall('m:mesh/m:vertices/m:vertex',ns)])
        f=np.array([[int(p.get(k)) for k in ['v1','v2','v3']] for p in obj.findall('m:mesh/m:triangles/m:triangle',ns)])
        tm=trimesh.Trimesh(v,f,process=True);assert tm.is_watertight and tm.volume>0 and len(tm.split(only_watertight=False))==1
        objects[obj.get('id')]=v
    items=root.findall('m:build/m:item',ns);assert len(items)==quantity
    for item in items:
        t=np.array([float(x) for x in item.get('transform').split()]).reshape(4,3)
        v=objects[item.get('objectid')]@t[:3]+t[3]
        assert (v[:,:2].min(0)>=5).all() and (v[:,:2].max(0)<=215).all()
        assert v[:,2].min()>=0 and v[:,2].max()<=250

def quantity_plate(part):
    p=ROOT/'print/3MF'/(part['name']+'.3mf');ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(p) as z:files={n:z.read(n) for n in z.namelist()}
    root=ET.fromstring(files['3D/3dmodel.model']);build=root.find('m:build',ns)
    for item in list(build):build.remove(item)
    for x in [38,110,182]:ET.SubElement(build,'{'+ns['m']+'}item',objectid='1',transform=f'1 0 0 0 1 0 0 0 1 {x} 110 0')
    files['3D/3dmodel.model']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    dest=ROOT/'print/3MF/nozzles_quantity3_K1C.3mf'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items():z.writestr(n,v)
    assert 72-part['print_size_mm'][0]>10
    verify_3mf(dest,3)

def main():
    for folder in ['print/STL','print/3MF','cad','images']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
    originals=[BASE/'print/STL/nozzle_150x16_H188_W150_P22_mm.stl',BASE/'print/STL/splitter_H110_neck46_mm.stl',
        BASE/'ThreeWay_51mm_150x16_PrintPack.zip']
    existing=[p for p in originals if p.exists()]
    if existing:write(ROOT/'original_release_hashes.json',{str(p):digest(p) for p in existing})
    parts=[export(nozzle(),'nozzle_150x16_female_ID55p4_H188','nozzle')]
    for d in [55.,55.4,55.8]:parts.append(export(coupon(d),f'fit_ring_ID{d:g}'.replace('.','p'),'fit_ring'))
    for part in parts:verify_3mf(ROOT/'print/3MF'/(part['name']+'.3mf'))
    quantity_plate(parts[0])
    write(ROOT/'cad/geometry_checks.json',dict(parts=parts,socket_ID_mm=SOCKET,socket_OD_mm=SOCKET+2*WALL,
        hose_ID_mm=51,hose_maximum_thickness_mm=1.8,hose_outer_envelope_estimate_mm=54.6,
        diameter_clearance_estimate_mm=.8,socket_depth_mm=25,clamp_relief_slots=2,slot_width_mm=2,slot_height_mm=20,
        flow_inlet_ID_mm=51,outlet_clear_mm=[150,16],total_height_mm=H,main_wall_mm=2.4,
        clamp_outer_diameter_mm=60.2,fit_coupon_IDs_mm=[55,55.4,55.8],source_url='https://www.goodnice.com.tw/p-h05.html',
        source_row=[51,'2 inch',250,.4,1.8,40,2,20,240],outer_diameter_directly_specified=False,
        physical_fit_verified=False,CFD_rerun=False,previous_CFD_not_a_validation_of_this_revision=True,
        actual_slicing_verified=False,physical_print_verified=False,K1C_space_and_5mm_brim_checked=True))

if __name__=='__main__':main()
