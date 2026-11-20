"""One continuous 200 mm body; keep the existing 60 mm replaceable lips."""
import hashlib,itertools,json,shutil
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m
from geometry import ROOT,HOLES,rounded_rect,section,WALL
from cad_utils import tube,rect_loft,cylinder,nut,box,mesh,save3mf

SOURCE=ROOT.parent/'AirKnife_K1C_20261105'
H=260.;B=200.

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def record_hashes():
    return {p.relative_to(SOURCE).as_posix():sha(p) for p in SOURCE.rglob('*') if p.is_file()}

def obj(path):
    tm=trimesh.load_mesh(path,process=True)
    o=m.Manifold(m.Mesh64(np.array(tm.vertices),np.array(tm.faces,dtype=np.uint64)))
    assert o.status()==m.Error.NoError,path
    return o

def main():
    before=record_hashes()
    for sub in ['cad/reference','print/STL','print/3MF','print/plates','images']:
        (ROOT/sub).mkdir(parents=True,exist_ok=True)
    zs=sorted(set([2.5,3.,12.,B]+[float(x) for x in np.linspace(3,B,round(B/2)+1)]))
    body=tube(zs,H,12)
    flange=rect_loft([0.,3.],lambda z:[(x+2,y) for x,y in rounded_rect(120,118,4)])
    aperture=rect_loft([-1.,4.],lambda z:rounded_rect(88,82,3))
    flange=flange-aperture
    for h in HOLES:flange=flange-cylinder(h['d'],6,[h['x'],h['y'],1.5])
    body=body+flange
    # Identical attachment ears and nut pockets; no old Y=0 split or rails.
    for x in [-20.,20.]:
        for y in [-70.,70.]:
            side=1 if x>0 else -1
            lo,hi=sorted([side*11.8,side*26.])
            body=body+box([lo,y-6,B-6],[hi,y+6,B])
            body=body-cylinder(3.4,10,[x,y,B-3])-nut([x,y,B-4.6])
    assert body.status()==m.Error.NoError and len(body.decompose())==1
    reference=mesh(body)
    assert reference.is_watertight and reference.volume>0
    reference.export(ROOT/'cad/reference/body_onepiece.stl')
    rotated=mesh(body.rotate([0,0,45]))
    rotated.vertices-=np.r_[rotated.bounds.mean(axis=0)[:2],rotated.bounds[0,2]]
    assert max(rotated.extents[:2]+10)<=220 and rotated.extents[2]<=250
    path=ROOT/'print/STL/body_onepiece_mm.stl';rotated.export(path)
    readback=trimesh.load_mesh(path,process=True)
    assert readback.is_watertight and readback.is_winding_consistent and readback.volume>0
    assert len(readback.split(only_watertight=False))==1
    assert (readback.area_faces>1e-10).all()
    assert np.allclose(readback.extents,rotated.extents,atol=1e-4)
    save3mf(ROOT/'print/3MF/body_onepiece.3mf',rotated.vertices,rotated.faces,'body_onepiece',(110,110,0))
    shutil.copyfile(ROOT/'print/3MF/body_onepiece.3mf',ROOT/'print/plates/01_body_onepiece_Z45.3mf')
    print('ONEPIECE_BODY_BUILT',readback.extents.tolist(),flush=True)
    parts=[{'name':'body_onepiece','group':'body','rotation_XYZ_deg':[0,0,45],
        'print_size_mm':readback.extents.tolist(),'assembly_bounds_mm':reference.bounds.tolist(),
        'volume_mm3':float(reference.volume),'approx_PLA_mass_g':float(reference.volume*.00124),
        'triangles':len(readback.faces),'single_closed_component':True,'zero_degenerate_triangles':True,
        'stl_sha256':sha(path)}]
    old=json.loads((SOURCE/'cad/geometry_checks.json').read_text(encoding='utf-8'))
    unchanged_lips=[]
    for r in old['parts']:
        if not r['group'].startswith('lip_'):continue
        for sub,filename in [('cad/reference',r['name']+'.stl'),('print/STL',r['name']+'_mm.stl'),('print/3MF',r['name']+'.3mf')]:
            shutil.copyfile(SOURCE/sub/filename,ROOT/sub/filename)
            assert sha(SOURCE/sub/filename)==sha(ROOT/sub/filename)
        parts.append(r)
        unchanged_lips.append({'part':r['name'],'copied_without_geometry_change':True,'stl_sha256':r['stl_sha256']})
    for g in [8,12,16]:
        f=f'03_lip_{g:02d}mm_pair.3mf';shutil.copyfile(SOURCE/'print/plates'/f,ROOT/'print/plates'/f)
    (ROOT/'print/optional').mkdir(exist_ok=True)
    shutil.copyfile(SOURCE/'print/STL/alignment_pin_2p8x6_mm.stl',ROOT/'print/optional/alignment_pin_2p8x6_mm.stl')
    rep={'date':'2026-11-10','height_mm':H,'body_lip_joint_Z_mm':B,'span_mm':216,
        'gap_options_mm':[8,12,16],'wall_mm':WALL,'original_holes':HOLES,
        'body_is_one_continuous_solid':True,'body_seam_rails_removed':True,
        'body_seam_fasteners_removed':8,'body_alignment_pins_removed':8,
        'body_seam_M3x16_count':0,'lip_module_M3x16_count':4,'lip_half_M3x30_count':4,
        'required_M3_nut_count':8,'optional_lip_alignment_pin_count':4,
        'main_printed_parts_per_assembly':3,'K1C_nominal_build_mm':[220,220,250],
        'body_bed_orientation_Z_deg':45,'body_5mm_brim_bounds_within_K1C':True,
        'new_design_core_present':False,'internal_vanes':0,'unchanged_lips':unchanged_lips,
        'parts':parts,'physical_print_verified':False,'actual_slicing_verified':False}
    (ROOT/'cad/geometry_checks.json').write_text(json.dumps(rep,indent=2),encoding='utf-8')
    # Verify a union of the old halves agrees exactly wherever an air wall exists.
    legacy=obj(SOURCE/'cad/reference/body_A.stl')+obj(SOURCE/'cad/reference/body_B.stl')
    removed=legacy-body;added=body-legacy
    # Changes must lie beyond the old shell's lateral seam rails, never inside the air path.
    # Check thin sampled wall bands and the flange by a restricted Boolean comparison.
    common_flange=box([-60,-61,-1],[62,61,3.0])
    flange_difference=((legacy^common_flange)-(body^common_flange)).volume()+((body^common_flange)-(legacy^common_flange)).volume()
    assert flange_difference<.02,flange_difference
    fluid_profile=rect_loft([-.1]+zs+[B+.1],lambda z:rounded_rect(*section(max(0,min(B,z)),H,12)))
    assert (body^fluid_profile).volume()<.02,'new body intrudes into nominal airflow'
    # A narrow 0.4 mm wall band proves both old and new continuous air-side surfaces agree.
    inner_band=rect_loft(zs,lambda z:rounded_rect(section(z,H,12)[0]+.8,section(z,H,12)[1]+.8,section(z,H,12)[2]+.4))-fluid_profile
    band_diff=((body^inner_band)-(legacy^inner_band)).volume()+((legacy^inner_band)-(body^inner_band)).volume()
    assert band_diff<.05,band_diff
    lip_objects={r['name']:obj(ROOT/'cad/reference'/(r['name']+'.stl')) for r in parts if r['group'].startswith('lip_')}
    pairs=[];tools=[]
    for g in [8,12,16]:
        assembly={'body_onepiece':body,**{n:o for n,o in lip_objects.items() if n.startswith(f'lip_{g:02d}mm')}}
        for a,b in itertools.combinations(assembly,2):
            vol=(assembly[a]^assembly[b]).volume();assert vol<.02,(g,a,b,vol)
            pairs.append({'gap_mm':g,'parts':[a,b],'intersection_mm3':vol})
        for x in [-20.,20.]:
            for y in [-70.,70.]:
                tool=cylinder(8,56,[x,y,234.2])
                hit=sum((o^tool).volume() for o in assembly.values());assert hit<.02,(g,x,y,hit)
                tools.append({'gap_mm':g,'coupling_screw_XY_mm':[x,y],'8mm_tool_blocked_volume_mm3':hit})
    checks={'flange_preserved_symmetric_difference_mm3':flange_difference,
        'air_side_wall_band_difference_mm3':band_diff,'removed_outer_rail_volume_mm3':removed.volume(),
        'added_material_mm3':added.volume(),'assembly_pair_checks':pairs,'driver_access_checks':tools}
    (ROOT/'cad/assembly_compatibility_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    after=record_hashes();assert before==after,'existing delivery folder changed'
    (ROOT/'source_integrity.json').write_text(json.dumps({'source_folder':SOURCE.name,
        'all_existing_files_unchanged':True,'file_count':len(before),'source_files_sha256':after},indent=2),encoding='utf-8')
    print('OLD_LIPS_COMPATIBLE_AND_SOURCE_UNCHANGED',len(pairs),len(before),flush=True)

if __name__=='__main__':main()
