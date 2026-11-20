"""Same printed body and four original M3 interfaces; new smooth head only."""
import argparse,hashlib,json,shutil
import numpy as np
import trimesh
import manifold3d as m
from geometry import ROOT,DESIGNS,HOLES,activate,section,wall_at,rounded_rect
from cad_utils import rect_loft,box,cylinder,mesh,save3mf
SOURCE=ROOT.parent/'AirKnife_K1C_OnePieceLip_NoRibs_20261110'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def obj(p):
    tm=trimesh.load_mesh(p,process=True);o=m.Manifold(m.Mesh64(np.array(tm.vertices),np.array(tm.faces,dtype=np.uint64)))
    assert o.status()==m.Error.NoError;return o
def head_solid(name):
    activate(name);c=DESIGNS[name];b=c['body'];h=c['height']
    zs=sorted(set(list(np.linspace(b,h,int((h-b)*2)+1))+[h-6,h-1]))
    outer=rect_loft(zs,lambda z:rounded_rect(section(z)[0]+2*wall_at(z),section(z)[1]+2*wall_at(z),wall_at(z)))
    # Exact radial offset of the original body's rounded outer mouth, 0.25 mm clearance.
    socket=rect_loft([b-6,b+3],lambda z:rounded_rect(227.3,31.3,5.65))-rect_loft([b-7,b+4],lambda z:rounded_rect(221.3,25.3,2.65))
    for side in [-1,1]:
        lo,hi=sorted([side*11.6,side*26.2])
        for y in [0.,-70.,70.]:socket=socket-box([lo,y-6.25,b-6.2],[hi,y+6.25,b])
    bridge=rect_loft([b,b+4],lambda z:rounded_rect(227.3,31.3,5.65))
    solid=outer+socket+bridge
    for x in [-20.,20.]:
        for y in [-70.,70.]:
            lo,hi=sorted([11.8*np.sign(x),26.*np.sign(x)])
            solid=solid+box([lo,y-6,b],[hi,y+6,b+6])-cylinder(3.4,10,[x,y,b+3])
    # One continuous cut keeps the bridge and shell exactly off the CFD air path.
    air_z=sorted(set([b-7,b-.2]+zs+[h+.2]))
    air=rect_loft(air_z,lambda z:rounded_rect(*section(max(b,min(h,z)))))
    solid=solid-air
    assert solid.status()==m.Error.NoError and len(solid.decompose())==1
    return solid
def main(names):
    for sub in ['cad/reference','print/STL','print/3MF','print/plates','images']:(ROOT/sub).mkdir(parents=True,exist_ok=True)
    for rel in ['cad/reference/body_onepiece.stl','print/STL/body_onepiece_mm.stl','print/3MF/body_onepiece.3mf','print/plates/01_body_onepiece_Z45.3mf']:
        shutil.copyfile(SOURCE/rel,ROOT/rel);assert sha(SOURCE/rel)==sha(ROOT/rel)
    original=json.loads((SOURCE/'cad/geometry_checks.json').read_text());parts=[next(r for r in original['parts'] if r['group']=='body')]
    body=obj(ROOT/'cad/reference/body_onepiece.stl');checks=[]
    for name in names:
        solid=head_solid(name);c=DESIGNS[name];label=f'head_{name}_16mm_body200'
        reference=mesh(solid);reference.export(ROOT/'cad/reference'/(label+'.stl'))
        assert reference.extents[1]<=300
        printmesh=mesh(solid.rotate([0,0,45]));bounds=printmesh.bounds;printmesh.vertices-=np.r_[bounds.mean(0)[:2],bounds[0,2]]
        assert max(printmesh.extents[:2]+10)<=220 and printmesh.extents[2]<=250
        path=ROOT/'print/STL'/(label+'_mm.stl');printmesh.export(path)
        tm=trimesh.load_mesh(path,process=True);assert tm.is_watertight and tm.is_winding_consistent and tm.volume>0
        assert len(tm.split(only_watertight=False))==1 and (tm.area_faces>1e-10).all()
        assert abs(tm.volume/reference.volume-1)<2e-5
        save3mf(ROOT/'print/3MF'/(label+'.3mf'),printmesh.vertices,printmesh.faces,label,(110,110,0))
        shutil.copyfile(ROOT/'print/3MF'/(label+'.3mf'),ROOT/'print/plates'/(f'02_{name}_head_Z45.3mf'))
        parts.append({'name':label,'design':name,'group':name,'rotation_XYZ_deg':[0,0,45],'print_size_mm':tm.extents.tolist(),
            'assembly_bounds_mm':reference.bounds.tolist(),'assembly_size_mm':reference.extents.tolist(),'maximum_outside_width_mm':float(reference.extents[1]),
            'volume_mm3':float(reference.volume),'approx_PLA_mass_g':float(reference.volume*.00124),
            'triangles':len(tm.faces),'single_closed_component':True,'zero_degenerate_triangles':True,'stl_sha256':sha(path)})
        test=obj(ROOT/'cad/reference'/(label+'.stl'));hit=(body^test).volume();assert hit<.02
        insert=[]
        for dz in np.linspace(0,6.2,9):
            vol=(body^test.translate([0,0,float(dz)])).volume();assert vol<.02
            insert.append({'offset_Z_mm':float(dz),'interference_mm3':vol})
        tools=[]
        for x in [-20.,20.]:
            for y in [-70.,70.]:
                tool=cylinder(8,c['height']-206.2+2,[x,y,(c['height']+208.2)/2])
                vol=(body^tool).volume()+(test^tool).volume();assert vol<.02;tools.append({'XY_mm':[x,y],'tool_obstruction_mm3':vol})
        checks.append({'design':name,'assembly_interference_mm3':hit,'insertion_samples':insert,'8mm_driver_checks':tools})
        print('HEAD_CAD_READY',name,tm.extents.tolist(),flush=True)
    report={'date':'2026-11-14','body_unchanged':True,'original_holes':HOLES,'parts':parts,
        'designs':{n:DESIGNS[n] for n in names},'body_height_mm':200,'outlet_gap_mm':16,'M3x16_screws':4,'M3_nuts':4,
        'alignment_pins':0,'external_ribs':0,'actual_slicing_verified':False,'physical_print_verified':False}
    (ROOT/'cad/geometry_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ROOT/'cad/compatibility_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('designs',nargs='+');main(p.parse_args().designs)
