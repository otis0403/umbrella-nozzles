"""Continuous replaceable lips; keep the existing one-piece body unchanged."""
import hashlib,itertools,json,math,shutil
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m
from geometry import ROOT,section,rounded_rect,WALL
from cad_utils import tube,rect_loft,cylinder,box,mesh,save3mf,loft

SOURCE=ROOT.parent/'AirKnife_K1C_OnePieceBody_OnePieceLip_20261110'
LEGACY=ROOT.parent/'AirKnife_K1C_20261105'
H=260.;B=200.
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(p):return {f.relative_to(p).as_posix():sha(f) for f in p.rglob('*') if f.is_file()}
def read_obj(p):
    tm=trimesh.load_mesh(p,process=True)
    o=m.Manifold(m.Mesh64(np.array(tm.vertices),np.array(tm.faces,dtype=np.uint64)))
    assert o.status()==m.Error.NoError,p
    return o

def build_lip(gap):
    lip=tube(np.linspace(B,H,61),H,gap)
    skirt=rect_loft([B-6,B+3],lambda z:rounded_rect(226.,30.,2.4))
    skcut=rect_loft([B-7,B+4],lambda z:rounded_rect(221.2,25.2,1.))
    bridge=rect_loft([B,B+4],lambda z:rounded_rect(226.,30.,2.4))-rect_loft([B-1,B+5],lambda z:rounded_rect(216.,20.,0.))
    socket=skirt-skcut
    for side in [-1,1]:
        xl,xh=sorted([side*11.6,side*26.2])
        for yc in [0.,-70.,70.]:
            socket=socket-box([xl,yc-6.2,B-6.2],[xh,yc+6.2,B])
    lip=lip+socket+bridge
    for x in [-20.,20.]:
        for y in [-70.,70.]:
            lo,hi=sorted([math.copysign(11.8,x),math.copysign(26.,x)])
            lip=lip+box([lo,y-6,B],[hi,y+6,B+6])
            lip=lip-cylinder(3.4,10,[x,y,B+3])
    # External ribs omitted; fluid wall and interfaces are unchanged.
    # There are no former half-clamp ears, M3x30 holes, nuts, or dowel voids.
    for x in [-20.,20.]:
        for y in [-70.,70.]:
            lip=lip-cylinder(10.,H-(B+6.1)+2.,[x,y,(H+B+6.1+2.)/2])
    assert lip.status()==m.Error.NoError and len(lip.decompose())==1
    return lip

def main():
    before=snapshot(SOURCE)
    for sub in ['cad/reference','print/STL','print/3MF','print/plates','images']:(ROOT/sub).mkdir(parents=True,exist_ok=True)
    for rel in ['cad/reference/body_onepiece.stl','print/STL/body_onepiece_mm.stl',
                'print/3MF/body_onepiece.3mf','print/plates/01_body_onepiece_Z45.3mf']:
        shutil.copyfile(SOURCE/rel,ROOT/rel);assert sha(SOURCE/rel)==sha(ROOT/rel)
    old=json.loads((SOURCE/'cad/geometry_checks.json').read_text())
    body=read_obj(ROOT/'cad/reference/body_onepiece.stl')
    parts=[next(r for r in old['parts'] if r['group']=='body')]
    checks=[]
    for gap in [8,12,16]:
        lip=build_lip(gap);name=f'lip_{gap:02d}mm_onepiece_no_ribs'
        reference=mesh(lip);reference.export(ROOT/'cad/reference'/(name+'.stl'))
        oriented=mesh(lip.rotate([0,0,45]));bounds=oriented.bounds
        oriented.vertices-=np.r_[bounds.mean(0)[:2],bounds[0,2]]
        assert (oriented.extents[:2]+10<=220).all() and oriented.extents[2]<=250
        path=ROOT/'print/STL'/(name+'_mm.stl');oriented.export(path)
        reloaded=trimesh.load_mesh(path,process=True)
        assert reloaded.is_watertight and reloaded.is_winding_consistent and reloaded.volume>0
        assert len(reloaded.split(only_watertight=False))==1 and (reloaded.area_faces>1e-10).all()
        assert abs(reloaded.volume/reference.volume-1)<2e-5
        save3mf(ROOT/'print/3MF'/(name+'.3mf'),oriented.vertices,oriented.faces,name,(110,110,0))
        shutil.copyfile(ROOT/'print/3MF'/(name+'.3mf'),ROOT/'print/plates'/(f'02_lip_{gap:02d}mm_onepiece_no_ribs_Z45.3mf'))
        r={'name':name,'group':f'lip_{gap}','rotation_XYZ_deg':[0,0,45],
            'print_size_mm':reloaded.extents.tolist(),'assembly_bounds_mm':reference.bounds.tolist(),
            'volume_mm3':float(reference.volume),'approx_PLA_mass_g':float(reference.volume*.00124),
            'triangles':len(reloaded.faces),'single_closed_component':True,'zero_degenerate_triangles':True,
            'stl_sha256':sha(path)}
        parts.append(r)
        legacy=read_obj(SOURCE/f'cad/reference/lip_{gap:02d}mm_onepiece.stl')
        fluid=rect_loft([B-.2]+list(np.linspace(B,H,61))+[H+.2],lambda z:rounded_rect(*section(max(B,min(H,z)),H,gap)))
        intrusion=(lip^fluid).volume();assert intrusion<.02,(gap,intrusion)
        band=rect_loft(np.linspace(B,H,61),lambda z:rounded_rect(section(z,H,gap)[0]+.8,section(z,H,gap)[1]+.8,section(z,H,gap)[2]+.4))-fluid
        diff=((lip^band)-(legacy^band)).volume()+((legacy^band)-(lip^band)).volume()
        assert diff<.05,(gap,diff)
        contact=box([-27,-77,B-6], [27,77,B+6])
        interface_diff=((lip^contact)-(legacy^contact)).volume()+((legacy^contact)-(lip^contact)).volume()
        assert interface_diff<.05,(gap,interface_diff)
        interference=(body^lip).volume();assert interference<.02,(gap,interference)
        # Material differences are restricted to the two old ribs on each side.
        removed=legacy-lip;added=lip-legacy
        rib_zones=box([-50,-109,B+12.49],[50,109,B+15.51])+box([-50,-109,B+42.49],[50,109,B+45.51])
        outside=(removed-rib_zones).volume()
        assert outside<.05 and added.volume()<.05,(gap,outside,added.volume())
        toolchecks=[]
        for x in [-20.,20.]:
            for y in [-70.,70.]:
                tool=cylinder(8,56,[x,y,234.2]);hit=(lip^tool).volume()+(body^tool).volume()
                assert hit<.02,(gap,x,y,hit)
                toolchecks.append({'XY_mm':[x,y],'8mm_tool_obstruction_mm3':hit})
        checks.append({'gap_mm':gap,'airway_intrusion_mm3':intrusion,'inner_wall_band_difference_mm3':diff,
            'attachment_interface_difference_mm3':interface_diff,'body_intersection_mm3':interference,
            'driver_access_checks':toolchecks,'old_clamp_ears_removed':True,'no_pin_or_half_clamp_holes':True,
            'external_ribs_per_side':0,'removed_rib_volume_mm3':removed.volume(),
            'removed_outside_rib_height_bands_mm3':outside,'added_material_mm3':added.volume()})
        print('ONEPIECE_LIP_BUILT',gap,r['print_size_mm'],flush=True)
    rep={'date':'2026-11-10','height_mm':H,'body_lip_joint_Z_mm':B,'span_mm':216,'wall_mm':WALL,
        'gap_options_mm':[8,12,16],'original_holes':old['original_holes'],'body_unchanged':True,'external_ribs_per_side':0,
        'main_printed_parts_per_assembly':2,'lip_is_one_continuous_solid':True,
        'lip_half_M3x30_count':0,'alignment_pin_count':0,'lip_module_M3x16_count':4,'required_M3_nut_count':4,
        'K1C_nominal_build_mm':[220,220,250],'bed_orientation_Z_deg':45,'parts':parts,
        'new_design_core_present':False,'internal_vanes':0,'physical_print_verified':False,'actual_slicing_verified':False}
    (ROOT/'cad/geometry_checks.json').write_text(json.dumps(rep,indent=2),encoding='utf-8')
    (ROOT/'cad/compatibility_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    assert snapshot(SOURCE)==before,'previous delivery was modified'
    (ROOT/'source_integrity.json').write_text(json.dumps({'source_folder':SOURCE.name,'original_files_unchanged':True,
        'file_count':len(before),'source_files_sha256':before},indent=2),encoding='utf-8')
    print('ALL_LIPS_ONEPIECE_BODY_COMPATIBLE_SOURCE_UNCHANGED',len(before),flush=True)

if __name__=='__main__':main()
