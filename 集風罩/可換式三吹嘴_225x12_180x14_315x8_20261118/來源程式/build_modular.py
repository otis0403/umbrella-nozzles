"""Separate the common chamber from replaceable contraction tips; millimetres."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m

ROOT=Path(__file__).resolve().parent
CFD=ROOT.parent
sys.path.insert(0,str(CFD))
import design
from cad_utils import loft,box,cylinder,mesh
from build_parts import full_nozzle,ring

(ROOT/'STL').mkdir(parents=True,exist_ok=True)
(ROOT/'cad').mkdir(exist_ok=True)
(ROOT/'images').mkdir(exist_ok=True)
selection=json.loads((CFD/'selection.json').read_text())

def solid_from_file(path):
    tri=trimesh.load_mesh(path,process=True)
    result=m.Manifold(m.Mesh64(np.asarray(tri.vertices,np.float64),np.asarray(tri.faces,np.uint64)))
    assert result.status()==m.Error.NoError
    return result

def disk_ring(d,z,x=0,y=0,n=64):
    t=np.linspace(0,2*np.pi,n,endpoint=False)
    return np.c_[x+d/2*np.cos(t),y+d/2*np.sin(t),np.full(n,z)]

def slot(d,extension,z0,z1,x,y):
    result=cylinder(d,z1-z0,[x,y-extension/2,(z0+z1)/2],segments=64)
    if extension:
        result+=cylinder(d,z1-z0,[x,y+extension/2,(z0+z1)/2],segments=64)
        result+=box([x-d/2,y-extension/2,z0],[x+d/2,y+extension/2,z1])
    return result

def ear(x,y,z0,z1):
    result=cylinder(14,z1-z0,[x,y,(z0+z1)/2],segments=64)
    x0,x1=sorted([np.sign(x)*12.4,x])
    return result+box([x0,y-7,z0],[x1,y+7,z1])

def export(solid,name,translation=(0,0,0)):
    assert solid.status()==m.Error.NoError and len(solid.decompose())==1,name
    tri=mesh(solid.translate(translation).simplify(.0001))
    q=np.asarray(tri.vertices,dtype=np.float32).astype(np.float64)
    rebuilt=m.Manifold(m.Mesh64(q,np.asarray(tri.faces,np.uint64)))
    assert rebuilt.status()==m.Error.NoError,name
    tri=mesh(rebuilt.simplify(.00005))
    path=ROOT/'STL'/(name+'_mm.stl');tri.export(path)
    loaded=trimesh.load_mesh(path,process=True)
    assert loaded.is_watertight and loaded.is_winding_consistent and loaded.volume>0,name
    assert len(loaded.split(only_watertight=False))==1 and loaded.area_faces.min()>1e-10,(name,loaded.area_faces.min())
    return {'id':name,'file':str(path),'watertight':True,'single_connected_component':True,
            'positive_volume_mm3':float(loaded.volume),'minimum_triangle_area_mm2':float(loaded.area_faces.min()),
            'size_mm':loaded.extents.tolist(),'bounds_mm':loaded.bounds.tolist(),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

records=[];groups=[]
for key in ['inner','center','outer']:
    spec=selection[key];width=spec['width_mm'];gap=spec['gap_mm'];length=spec['length_mm'];h=spec['height_mm']
    split=25+length;design.GAP=gap
    suffix='_guided' if key=='outer' else ''
    source=CFD/'cad/full'/f'nozzle_W{width}_G{gap}_L{length}_ramp{suffix}_mm.stl'
    full=solid_from_file(source)
    lower=full^box([-1000,-1000,-1],[1000,1000,split])
    upper_box=box([-1000,-1000,split],[1000,1000,h+1])
    ys=[-width/2+30,width/2-30] if key!='outer' else [-width/2+30,0,width/2-30]
    screws=[(x,y) for x in [-19.4,19.4] for y in ys]
    locator_indices=[0,len(screws)-1]
    for index,(x,y) in enumerate(screws):
        lower+=ear(x,y,split-4,split)
        if index in locator_indices:
            lower+=loft([disk_ring(d,z,x,y) for d,z in [(7.4,split-.2),(7.4,split+1.2),(7.0,split+1.5)]])
    # Closed face seal groove remains outside the fluid wall; flat lands touch.
    outer=loft([ring(width+3.6,25.6,4.8,z) for z in [split-.5,split+.1]])
    inner=loft([ring(width+1.2,23.2,3.6,z) for z in [split-.6,split+.2]])
    lower-=outer-inner
    for x,y in screws:lower-=slot(4.4,0,split-5,split+2.5,x,y)
    body_record=export(lower,key+'_body')
    body_record.update(position=key,type='body',width_mm=width,split_Z_mm=split,
                       assembly_translation_mm=[0,0,0],source_full_STL=str(source))
    records.append(body_record)
    tips=[]
    for tip_gap in ([gap,16] if key!='outer' else [gap]):
        design.GAP=tip_gap
        tip_full=full if tip_gap==gap else full_nozzle(width,length,'ramp')
        upper=tip_full^upper_box
        for index,(x,y) in enumerate(screws):
            upper+=ear(x,y,split,split+4)
        for index,(x,y) in enumerate(screws):
            upper-=slot(4.4,0 if index==0 else 1,split-1,split+5,x,y)
            if index in locator_indices:
                upper-=slot(7.9,0 if index==0 else 1,split-.1,split+1.8,x,y)
        kind='preferred' if tip_gap==gap else 'reference'
        name=f'{key}_tip_g{tip_gap}'+('_reference' if kind=='reference' else '')
        tip_record=export(upper,name,[0,0,-split])
        tip_record.update(position=key,type='tip',variant=kind,width_mm=width,gap_mm=tip_gap,
                          axial_length_mm=43,assembly_translation_mm=[0,0,split])
        # Re-read both pieces at the same exported precision before fit checks.
        reread_body=solid_from_file(Path(body_record['file']))
        reread_tip=solid_from_file(Path(tip_record['file'])).translate([0,0,split])
        overlap=abs((reread_body^reread_tip).volume())
        assert overlap<.01,(name,'interference',overlap)
        assembled=reread_body+reread_tip
        added=assembled-tip_full
        # Probe only the joint region, all added features are external to flow.
        zs=np.linspace(split-5,split+5,41)
        probe=loft([ring(w-.1,d-.1,max(r-.05,.01),z) for z in zs
                    for w,d,r in [design.profile(z,width,length,'ramp')]])
        intrusion=abs((added^probe).volume())
        assert intrusion<.01,(name,'flow intrusion',intrusion)
        tip_record.update(body_tip_interference_mm3=overlap,added_features_inside_flow_probe_mm3=intrusion)
        records.append(tip_record);tips.append(name)
        print('MODULAR_PAIR_VERIFIED',name,'overlap',overlap,'flow_intrusion',intrusion,flush=True)
    groups.append({'position':key,'width_mm':width,'preferred_gap_mm':gap,'total_length_mm':h,'split_Z_mm':split,
                   'body':key+'_body','tips':tips,'preferred_tip':f'{key}_tip_g{gap}',
                   'screw_centers_XY_mm':[list(p) for p in screws],'screw_count':len(screws),
                   'locator_indices':locator_indices,'bolt_hole_diameter_mm':4.4,'tip_hole_float_Y_mm':1,
                   'locator_male_OD_mm':7.4,'locator_recess_diameter_mm':7.9,'radial_clearance_mm':.25,
                   'locator_height_mm':1.5,'recess_depth_mm':1.8,'axial_clearance_mm':.3,
                   'ear_thickness_each_mm':4,'seal_groove_width_mm':1.2,'seal_groove_depth_mm':.5,
                   'inner_sealing_land_mm':.6,'hardware':'M4x16 bolts, M4 nuts, two OD9 washers each'})

result={'units':'mm','groups':groups,'parts':records,'preferred_part_count':6,'reference_tip_count':2,
        'total_STL_count':len(records),'hardware_per_group':{'M4x16_bolts':14,'M4_nuts':14,'M4_OD9_washers':28},
        'physical_fit_and_sealing_verified':False,'CFD_source':str(CFD),
        'nominal_flow_profile_preserved':True,'printer_capacity_segmentation_deferred':True}
(ROOT/'modular_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ALL_MODULAR_PARTS_VERIFIED',len(records),flush=True)
