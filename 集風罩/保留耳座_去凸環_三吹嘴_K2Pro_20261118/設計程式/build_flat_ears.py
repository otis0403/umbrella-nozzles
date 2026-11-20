"""Remove only the raised plastic locator rings; retain external M4 ears/flanges."""
import hashlib,json,math,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh,manifold3d as m
ROOT=Path(__file__).resolve().parent
CFD=ROOT.parent/'InnerMiddle_12_14_8_ANSYS_20261117'
K2=ROOT.parent/'K2Pro_Outer315_Split_20261118'
sys.path.insert(0,str(CFD))
from cad_utils import box,cylinder,mesh,save3mf
source_data=json.loads((CFD/'modular/modular_checks.json').read_text(encoding='utf-8-sig'))
k2_data=json.loads((K2/'print_checks.json').read_text(encoding='utf-8-sig'))
mod_parts={r['id']:r for r in source_data['parts']};k2_parts={r['id']:r for r in k2_data['parts']}
for d in ['STL','3MF','cad','images']:(ROOT/d).mkdir(parents=True,exist_ok=True)
R=trimesh.transformations.rotation_matrix(math.pi/4,[0,0,1])

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path,transform=None):
    tri=trimesh.load_mesh(path,process=True)
    if transform is not None:tri.apply_transform(transform)
    solid=m.Manifold(m.Mesh64(tri.vertices.astype(np.float64),tri.faces.astype(np.uint64)))
    assert solid.status()==m.Error.NoError
    return solid

records=[];groups=[];sources={};changes=[]
jobs=[]
for g in source_data['groups']:
    key=g['position'];g=dict(g);g['parts']=[]
    g['raised_locator_rings']=False;g['female_recesses_retained']=True
    if key!='outer':
        row=mod_parts[g['body']]
        jobs.append({'id':g['body'],'group':key,'source':row['file'],'source_to_assembly':np.eye(4),
                     'print_from_source':R,'clip_source_Z_mm':g['split_Z_mm'],
                     'ring_centers_source_XY_mm':[g['screw_centers_XY_mm'][i] for i in g['locator_indices']]})
        g['parts'].append(g['body'])
        tip=mod_parts[g['preferred_tip']];assembly=np.eye(4);assembly[2,3]=g['split_Z_mm']
        jobs.append({'id':g['preferred_tip'],'group':key,'source':tip['file'],'source_to_assembly':assembly,
                     'print_from_source':R,'clip_source_Z_mm':None,'ring_centers_source_XY_mm':[]})
    else:
        for sid,newid,clip in [('inlet_lower','outer_inlet',55),('guided_upper','outer_guided_body',290)]:
            row=k2_parts[sid];assembly=np.array(row['assembly_from_print'])
            global_centers=(k2_data['new_joint_screw_centers_XY_mm'][::3] if sid=='inlet_lower'
                            else [g['screw_centers_XY_mm'][i] for i in g['locator_indices']])
            ring_z=55 if sid=='inlet_lower' else 345
            inv=np.linalg.inv(assembly)
            centers=[(inv@np.array([x,y,ring_z,1]))[:2].tolist() for x,y in global_centers]
            jobs.append({'id':newid,'group':key,'source':row['STL'],'source_to_assembly':assembly,
                         'print_from_source':np.eye(4),'clip_source_Z_mm':clip,'ring_centers_source_XY_mm':centers})
            g['parts'].append(newid)
        row=k2_parts['front_tip_g8']
        jobs.append({'id':g['preferred_tip'],'group':key,'source':row['STL'],
                     'source_to_assembly':np.array(row['assembly_from_print']),
                     'print_from_source':np.eye(4),'clip_source_Z_mm':None,'ring_centers_source_XY_mm':[]})
        g['rear_joint']={'split_Z_mm':55,'screw_centers_XY_mm':k2_data['new_joint_screw_centers_XY_mm'],
                         'screw_count':4,'male_ring_indices':[0,3],'flange_mm':[90,60,4],
                         'female_recesses_retained':True,'raised_locator_rings':False}
    g['parts'].append(g['preferred_tip']);groups.append(g)

for job in jobs:
    path=Path(job['source']);sources[str(path)]=sha(path)
    old=load(path);new=old;clip=job['clip_source_Z_mm']
    assembly=np.array(job['source_to_assembly']);print_matrix=np.array(job['print_from_source'])
    if clip is not None:
        new=old^box([-1000,-1000,-1],[1000,1000,clip])
        removed=old-new;allowed=None
        for x,y in job['ring_centers_source_XY_mm']:
            c=cylinder(7.5,1.52,[x,y,clip+.75],segments=64)
            allowed=c if allowed is None else allowed+c
        outside=abs((removed-allowed).volume());added=abs((new-old).volume())
        below=abs((removed^box([-1000,-1000,-1],[1000,1000,clip-.0001])).volume())
        assert outside<.001 and added<.001 and below<.001,(job['id'],outside,added,below)
        assert 50<removed.volume()<120,(job['id'],removed.volume())
        changes.append({'id':job['id'],'ring_count':2,'flat_source_Z_mm':clip,
                        'removed_volume_mm3':removed.volume(),'removed_outside_ring_masks_mm3':outside,
                        'added_material_mm3':added,'material_removed_below_face_mm3':below})
    target=ROOT/'STL'/(job['id']+'_flat_ears_mm.stl')
    unchanged_copy=clip is None and np.allclose(print_matrix,np.eye(4))
    if unchanged_copy:
        target.write_bytes(path.read_bytes())
    else:
        tri=mesh(new.simplify(.0001));tri.apply_transform(print_matrix)
        q=m.Manifold(m.Mesh64(np.asarray(tri.vertices,np.float32).astype(np.float64),tri.faces.astype(np.uint64)))
        assert q.status()==m.Error.NoError
        mesh(q.simplify(.00005)).export(target)
    tri=trimesh.load_mesh(target,process=True)
    assert tri.is_watertight and tri.is_winding_consistent and tri.volume>0,(job['id'],'solid')
    assert len(tri.split(only_watertight=False))==1 and tri.area_faces.min()>1e-10,(job['id'],'triangles',tri.area_faces.min())
    assert (tri.extents[:2]+16<300).all() and tri.bounds[0,2]>-.001 and tri.bounds[1,2]<=294
    model=ROOT/'3MF'/(job['id']+'_flat_ears_K2Pro300.3mf')
    save3mf(model,tri.vertices,tri.faces,job['id'],translate=(150,150,0))
    with zipfile.ZipFile(model) as z:
        assert z.testzip() is None
        xml=ET.fromstring(z.read('3D/3dmodel.model'))
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    assert xml.attrib['unit']=='millimeter'
    vv=np.array([[float(v.attrib[a]) for a in ['x','y','z']] for v in xml.findall('.//m:vertex',ns)])
    ff=np.array([[int(f.attrib[a]) for a in ['v1','v2','v3']] for f in xml.findall('.//m:triangle',ns)])
    tm=np.array([float(v) for v in xml.find('m:build/m:item',ns).attrib['transform'].split()])
    placed=vv@tm[:9].reshape(3,3)+tm[9:]
    assert (placed.min(0)[:2]>=8).all() and (placed.max(0)[:2]<=292).all() and placed[:,2].max()<300
    tri3=trimesh.Trimesh(vv,ff,process=True)
    assert tri3.is_watertight and abs(tri3.volume/tri.volume-1)<1e-5
    from_print=assembly@np.linalg.inv(print_matrix)
    record={'id':job['id'],'group':job['group'],'source':str(path),'STL':str(target),'3MF':str(model),
            'source_to_assembly':assembly.tolist(),'assembly_from_print':from_print.tolist(),
            'print_size_mm':tri.extents.tolist(),'placed_3MF_bounds_mm':[placed.min(0).tolist(),placed.max(0).tolist()],
            'minimum_triangle_area_mm2':float(tri.area_faces.min()),'watertight_single_positive_solid':True,
            'changed':clip is not None,'unchanged_byte_copy':unchanged_copy,'STL_sha256':sha(target),'3MF_sha256':sha(model),
            'flat_source_Z_mm':clip,'flat_assembly_Z_mm':None if clip is None else float((assembly@np.array([0,0,clip,1]))[2]),
            'ring_centers_assembly_XY_mm':[(assembly@np.array([x,y,clip,1]))[:2].tolist() for x,y in job['ring_centers_source_XY_mm']]}
    records.append(record);print('PART_VERIFIED',job['id'],tri.extents.tolist(),flush=True)

parts={r['id']:r for r in records}
for group in groups:
    union=None;overlaps=[]
    for name in group['parts']:
        r=parts[name];obj=load(r['STL'],np.array(r['assembly_from_print']))
        if union is None:union=obj
        else:overlaps.append(abs((union^obj).volume()));union+=obj
    assert max(overlaps)<.05,(group['position'],overlaps)
    group['assembly_overlap_mm3']=overlaps
assert all(sha(p)==v for p,v in sources.items())
assert len(records)==7 and sum(c['ring_count'] for c in changes)==8
result={'units':'mm','parts':records,'groups':groups,'removed_rings':changes,'source_hashes_unchanged':sources,
        'printer_volume_mm':[300,300,300],'brim_allowance_each_side_mm':8,
        'only_physical_change':'Remove eight raised locator collars from four male mating faces; retain all ears, flanges, holes and flow walls.',
        'hardware_one_three_head_set':{'M4x16_screws':18,'M4_nuts':18,'OD9_washers':36},
        'female_pockets_retained':True,'old_ear_interface_compatible':True,'new_CFD_run':False,
        'physical_slicing_print_fit_and_sealing_verified':False}
(ROOT/'flat_ear_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ALL_8_LOCATOR_RINGS_REMOVED_ONLY_AND_7_PARTS_VERIFIED',flush=True)
