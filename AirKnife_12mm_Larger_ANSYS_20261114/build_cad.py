"""Two longer, wider 12 mm lips for the already printed 200 mm body."""
import hashlib,json,math,shutil
import numpy as np
import manifold3d as m
import trimesh
from geometry import ROOT,HOLES,section,rounded_rect,WALL
from cad_utils import tube,rect_loft,box,cylinder,mesh,save3mf
SOURCE=ROOT.parent/'AirKnife_K1C_OnePieceLip_NoRibs_20261110'
B=200.
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def obj(p):
    tm=trimesh.load_mesh(p,process=True)
    o=m.Manifold(m.Mesh64(np.array(tm.vertices),np.array(tm.faces,dtype=np.uint64)))
    assert o.status()==m.Error.NoError
    return o
def build_lip(height):
    lip=tube(np.linspace(B,height,int(height-B)+1),height,12)
    socket=rect_loft([B-6,B+3],lambda z:rounded_rect(226.,30.,2.4))-rect_loft([B-7,B+4],lambda z:rounded_rect(221.2,25.2,1.))
    bridge=rect_loft([B,B+4],lambda z:rounded_rect(226.,30.,2.4))-rect_loft([B-1,B+5],lambda z:rounded_rect(216.,20.,0.))
    for side in [-1,1]:
        xl,xh=sorted([side*11.6,side*26.2])
        for yc in [0.,-70.,70.]:socket=socket-box([xl,yc-6.2,B-6.2],[xh,yc+6.2,B])
    lip=lip+socket+bridge
    for x in [-20.,20.]:
        for y in [-70.,70.]:
            lo,hi=sorted([math.copysign(11.8,x),math.copysign(26.,x)])
            lip=lip+box([lo,y-6,B],[hi,y+6,B+6])-cylinder(3.4,10,[x,y,B+3])
    assert lip.status()==m.Error.NoError and len(lip.decompose())==1
    return lip
def main():
    for sub in ['cad/reference','print/STL','print/3MF','print/plates','images']:(ROOT/sub).mkdir(parents=True,exist_ok=True)
    for rel in ['cad/reference/body_onepiece.stl','print/STL/body_onepiece_mm.stl','print/3MF/body_onepiece.3mf','print/plates/01_body_onepiece_Z45.3mf']:
        shutil.copyfile(SOURCE/rel,ROOT/rel);assert sha(SOURCE/rel)==sha(ROOT/rel)
    previous=json.loads((SOURCE/'cad/geometry_checks.json').read_text())
    body=obj(ROOT/'cad/reference/body_onepiece.stl');oldlip=obj(SOURCE/'cad/reference/lip_12mm_onepiece_no_ribs.stl')
    parts=[next(r for r in previous['parts'] if r['group']=='body')];checks=[]
    for height in [320,360]:
        name=f'lip_252x12_H{height}_no_ribs';lip=build_lip(height);tm=mesh(lip)
        tm.export(ROOT/'cad/reference'/(name+'.stl'))
        oriented=mesh(lip.rotate([0,0,45]));bounds=oriented.bounds
        oriented.vertices-=np.r_[bounds.mean(0)[:2],bounds[0,2]]
        assert max(oriented.extents[:2]+10)<=220 and oriented.extents[2]<=250
        dest=ROOT/'print/STL'/(name+'_mm.stl');oriented.export(dest)
        reloaded=trimesh.load_mesh(dest,process=True)
        assert reloaded.is_watertight and reloaded.is_winding_consistent and reloaded.volume>0
        assert len(reloaded.split(only_watertight=False))==1 and (reloaded.area_faces>1e-10).all()
        assert abs(reloaded.volume/tm.volume-1)<2e-5
        save3mf(ROOT/'print/3MF'/(name+'.3mf'),oriented.vertices,oriented.faces,name,(110,110,0))
        shutil.copyfile(ROOT/'print/3MF'/(name+'.3mf'),ROOT/'print/plates'/(f'02_lip_H{height}_W252_gap12_Z45.3mf'))
        parts.append({'name':name,'group':f'lip_H{height}','rotation_XYZ_deg':[0,0,45],
            'print_size_mm':reloaded.extents.tolist(),'assembly_bounds_mm':tm.bounds.tolist(),
            'volume_mm3':float(tm.volume),'approx_PLA_mass_g':float(tm.volume*.00124),'triangles':len(reloaded.faces),
            'single_closed_component':True,'zero_degenerate_triangles':True,'stl_sha256':sha(dest)})
        # Compare independently reloaded STL solids at the same numeric precision.
        checked_lip=obj(ROOT/'cad/reference'/(name+'.stl'))
        interface=box([-27,-113,194],[27,113,200])
        a=checked_lip^interface;b=oldlip^interface;diff=(a-b).volume()+(b-a).volume()
        assert diff<.05,(height,diff)
        interference=(body^checked_lip).volume();assert interference<.02
        inserted=[]
        for dz in np.linspace(0,6.2,9):
            hit=(body^checked_lip.translate([0,0,float(dz)])).volume();assert hit<.02
            inserted.append({'offset_Z_mm':float(dz),'interference_mm3':hit})
        tools=[]
        for x in [-20.,20.]:
            for y in [-70.,70.]:
                tool=cylinder(8,height-206.2+2,[x,y,(height+208.2)/2])
                blocked=(checked_lip^tool).volume()+(body^tool).volume();assert blocked<.02
                tools.append({'XY_mm':[x,y],'8mm_driver_blocked_volume_mm3':blocked})
        checks.append({'height_mm':height,'same_hard_stop_interface_difference_mm3':diff,
            'body_intersection_mm3':interference,'insertion_samples':inserted,'driver_access':tools})
        print('LONG_LIP_CAD_READY',height,reloaded.extents.tolist(),flush=True)
    report={'date':'2026-11-14','body_lip_joint_Z_mm':200,'body_unchanged':True,'clear_outlet_span_mm':252,
        'outlet_gap_mm':12,'height_options_mm':[320,360],'maximum_assembled_width_mm':256.8,
        'original_holes':HOLES,'parts':parts,'external_ribs':0,'alignment_pins':0,
        'M3x16_module_screws':4,'M3_nuts':4,'main_printed_parts_per_assembly':2,
        'physical_print_verified':False,'actual_slicing_verified':False}
    (ROOT/'cad/geometry_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ROOT/'cad/compatibility_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('CAD_EXPORT_COMPLETE',flush=True)
if __name__=='__main__':main()
