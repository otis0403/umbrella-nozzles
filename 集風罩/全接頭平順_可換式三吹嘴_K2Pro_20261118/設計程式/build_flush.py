"""No external ears/flanges: telescoping joints with captive M3 nuts and sunk heads."""
import hashlib,json,math,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import manifold3d as m
ROOT=Path(__file__).resolve().parent
CFD=ROOT.parent/'InnerMiddle_12_14_8_ANSYS_20261117'
sys.path.insert(0,str(CFD))
import design
from build_parts import ring
from cad_utils import loft,box,cylinder,mesh,save3mf
for d in ['STL','3MF','cad','images']:(ROOT/d).mkdir(parents=True,exist_ok=True)
selection=json.loads((CFD/'selection.json').read_text(encoding='utf-8-sig'))
WALL_LONG=4.4;WALL_SHORT=8.;MALE_LONG=2.;MALE_SHORT=4.8;CLEAR=.3
OVERLAP=12.
records=[];groups=[];source_hashes={}

def load(path,matrix=None):
    tri=trimesh.load_mesh(path,process=True)
    if matrix is not None:tri.apply_transform(matrix)
    obj=m.Manifold(m.Mesh64(np.asarray(tri.vertices,np.float64),np.asarray(tri.faces,np.uint64)))
    assert obj.status()==m.Error.NoError
    return obj

def profile(z,spec):return design.profile(z,spec['width_mm'],spec['length_mm'],'ramp')
def contour(z,spec,long,short,clear=0):
    w,d,r=profile(z,spec)
    return ring(w+2*(long+clear),d+2*(short+clear),r+long+clear,z)
def perimeter_x(points,y):
    xs=[]
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        if min(a[1],b[1])-1e-8<=y<=max(a[1],b[1])+1e-8 and abs(b[1]-a[1])>1e-10:
            t=(y-a[1])/(b[1]-a[1]);xs.append(a[0]+t*(b[0]-a[0]))
    assert xs
    return max(xs)

def yz_circle(x,y,z,d):
    a=np.linspace(0,2*np.pi,64,endpoint=False)
    return np.c_[np.full(64,x),y+d/2*np.cos(a),z+d/2*np.sin(a)]
def x_frustum(x0,x1,y,z,d0,d1):return loft([yz_circle(x0,y,z,d0),yz_circle(x1,y,z,d1)])

def wrapped(solid,spec):
    h=spec['height_mm'];split=25+spec['length_mm']
    zs=np.unique(np.r_[np.linspace(0,h,int(h)+1),25,35,split-12,split,split+12,h-8,h])
    outside=[]
    for z in zs:
        if z<=25:
            outside.append(ring(55.4+2*WALL_LONG,55.4+2*WALL_SHORT,27.7+WALL_LONG,z))
        else:
            w,d,r=profile(z,spec)
            # Uniform strengthened body; taper both walls smoothly across the tip.
            t=float(design.smooth((z-split-1)/34))
            wl=WALL_LONG+(2-WALL_LONG)*t;ws=WALL_SHORT+(2-WALL_SHORT)*t
            extra=4.4*(1-float(design.smooth((z-25)/10)))
            outside.append(ring(w+2*wl+extra,d+2*ws+extra,r+wl+extra/2,z))
    outer=loft(outside)
    # Added material stays outside the original void; original walls/guides survive.
    zs_inner=np.r_[-.1,0,24.999,25,np.linspace(25.001,h,int(h)),h+.1]
    protected=[]
    for z in zs_inner:
        if z<=25:protected.append(ring(55.6,55.6,27.8,z))
        else:
            w,d,r=profile(z,spec);protected.append(ring(w+.2,d+.2,r+.1,z))
    result=(solid+(outer-loft(protected)))^outer
    # Keep the existing hose-socket compliance slit through the thicker skin.
    result-=box([-100,-1,-.2],[100,1,19])+cylinder(2,200,[0,0,19],axis='x',segments=64)
    return result,outer

def envelope(spec,a,b,long,short,clear=0):
    return loft([contour(z,spec,long,short,clear) for z in np.linspace(a,b,max(3,math.ceil((b-a)*3)+1))])

def make_joint(male,female,spec,a,b,ys,leading_end,label,outer):
    z=(a+b)/2;hardware=[]
    male_contour=contour(z,spec,MALE_LONG,MALE_SHORT)
    full_contour=contour(z,spec,WALL_LONG,WALL_SHORT)
    for side in [-1,1]:
        for y in ys:
            xm=perimeter_x(male_contour,y);xo=perimeter_x(full_contour,y)
            xi=perimeter_x(contour(z,spec,0,0),y)
            nut_hi=xm-.7;nut_lo=nut_hi-2.7
            assert nut_lo-xi>.8,(label,y,'nut floor',nut_lo-xi)
            channel_z=(z-3.3,b+.15) if leading_end=='high' else (a-.15,z+3.3)
            cavity=box([nut_lo,y-2.9,channel_z[0]],[nut_hi,y+2.9,channel_z[1]])
            bore=cylinder(3.4,xm+.3-xi-.8,[(xm+.3+xi+.8)/2,y,z],axis='x',segments=64)
            for recess in np.arange(.55,1.001,.05):
                face=xo-float(recess);tip=face-6
                screw=x_frustum(face-1.7,face,y,z,3.0,6.0)
                screw+=cylinder(3.0,6-1.7,[(tip+face-1.7)/2,y,z],axis='x',segments=64)
                screw-=cylinder(2/math.cos(math.pi/6),1.2,[face-.5,y,z],axis='x',segments=6)
                if abs((screw-outer).volume())<.001:break
            assert tip-xi>.45 and tip<nut_hi-2.4-.05,(label,y,'thread reach',tip-xi,nut_hi-2.4-tip)
            female_cut=cylinder(3.6,20,[xo,y,z],axis='x',segments=64)
            # 0.15 mm radial head allowance; avoid an oversized cone that lets
            # the screw seat too deeply and consume the blind-hole floor.
            female_cut+=x_frustum(face-1.7,face+.2,y,z,3.3,6.65)
            # Positive axial overlap avoids coplanar zero-thickness ring shells.
            female_cut+=cylinder(6.65,10,[face+5.1,y,z],axis='x',segments=64)
            if side<0:
                cavity=cavity.mirror([1,0,0]);bore=bore.mirror([1,0,0]);female_cut=female_cut.mirror([1,0,0]);screw=screw.mirror([1,0,0])
            male-=cavity+bore;female-=female_cut
            head_outside=abs((screw-outer).volume());assert head_outside<.01,(label,'protruding screw',head_outside)
            hardware.append({'side_X':side,'center_YZ_mm':[y,z],'head_face_X_mm':side*face,
                             'tip_X_mm':side*tip,'nut_slot_X_abs_mm':[nut_lo,nut_hi],
                             'screw_head_recess_mm':float(recess),
                             'nut_slot_Z_mm':list(channel_z),'male_outer_X_abs_mm':xm,
                             'thread_beyond_nut_mm':nut_hi-2.4-tip,'screw_outside_smooth_outer_mm3':head_outside,
                             'illustrative_screw':screw})
    # Circumferential seal groove, away from the open captive-nut channels.
    gz=a+1.3 if leading_end=='high' else b-2.5
    groove_outer=envelope(spec,gz,gz+1.2,MALE_LONG+.02,MALE_SHORT+.02)
    groove_inner=envelope(spec,gz-.1,gz+1.3,MALE_LONG-.4,MALE_SHORT-.4)
    male-=groove_outer-groove_inner
    row={'id':label,'overlap_Z_mm':[a,b],'overlap_mm':12,'visible_seam_Z_mm':a if leading_end=='high' else b,
         'male_leading_end':leading_end,'screw_count':len(hardware),'screw':'M3x6 DIN7991 countersunk',
         'nut':'M3 DIN934 AF5.5 thickness2.4','screw_clearance_mm':3.6,
         'nut_slot_mm':[2.7,5.8],'seal_groove_Z_mm':[gz,gz+1.2],'seal_groove_depth_mm':.4,
         'hardware':hardware}
    return male,female,row

def export(obj,name,z0,assembly_z=0):
    assert obj.status()==m.Error.NoError,(name,obj.status())
    obj=obj.set_tolerance(.001)
    components=obj.decompose()
    zero_volumes=[c.volume() for c in components if abs(c.volume())<1e-9]
    components=[c for c in components if abs(c.volume())>=1e-9]
    assert len(components)==1,(name,'component volumes',[c.volume() for c in components])
    obj=components[0]
    tri=mesh(obj);rot=trimesh.transformations.rotation_matrix(math.pi/4,[0,0,1])
    tr=rot@trimesh.transformations.translation_matrix([0,0,-z0]);tri.apply_transform(tr)
    # Let the solid kernel collapse Boolean slivers while preserving topology.
    q=m.Manifold(m.Mesh64(np.asarray(tri.vertices,np.float32).astype(np.float64),np.asarray(tri.faces,np.uint64)))
    assert q.status()==m.Error.NoError
    tri=mesh(q.set_tolerance(.001));path=ROOT/'STL'/(name+'_mm.stl');tri.export(path)
    reread=trimesh.load_mesh(path,process=True)
    assert reread.is_watertight and reread.is_winding_consistent and reread.volume>0
    assert len(reread.split(only_watertight=False))==1 and reread.area_faces.min()>1e-10
    assert (reread.extents[:2]+16<300).all() and reread.bounds[0,2]>-.001 and reread.bounds[1,2]<=294
    transform=np.linalg.inv(tr);transform[2,3]+=assembly_z
    model=ROOT/'3MF'/(name+'_K2Pro300.3mf');save3mf(model,reread.vertices,reread.faces,name,translate=(150,150,0))
    with zipfile.ZipFile(model) as arc:
        assert arc.testzip() is None
        xml=ET.fromstring(arc.read('3D/3dmodel.model'))
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    assert xml.attrib['unit']=='millimeter'
    vv=np.array([[float(v.attrib[c]) for c in ['x','y','z']] for v in xml.findall('.//m:vertex',ns)])
    ff=np.array([[int(f.attrib[c]) for c in ['v1','v2','v3']] for f in xml.findall('.//m:triangle',ns)])
    tm=np.array([float(v) for v in xml.find('m:build/m:item',ns).attrib['transform'].split()])
    placed=vv@tm[:9].reshape(3,3)+tm[9:]
    assert (placed.min(0)[:2]>=8).all() and (placed.max(0)[:2]<=292).all() and placed[:,2].max()<300
    reread3=trimesh.Trimesh(vv,ff,process=True)
    assert reread3.is_watertight and abs(reread3.volume/reread.volume-1)<1e-5
    row={'id':name,'STL':str(path),'3MF':str(model),'print_size_mm':reread.extents.tolist(),
         'assembly_from_print':transform.tolist(),'watertight_single_positive_solid':True,
         'minimum_triangle_area_mm2':float(reread.area_faces.min()),'volume_mm3':float(reread.volume),
         'discarded_numerically_zero_component_volumes_mm3':zero_volumes,
         'placed_3MF_bounds_mm':[placed.min(0).tolist(),placed.max(0).tolist()],
         'STL_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'3MF_sha256':hashlib.sha256(model.read_bytes()).hexdigest()}
    records.append(row);print('PART_VERIFIED',name,row['print_size_mm'],flush=True)
    return load(path,transform)

for key in ['inner','center','outer']:
    spec=selection[key];design.GAP=spec['gap_mm'];w=spec['width_mm'];h=spec['height_mm'];split=25+spec['length_mm'];a=split-12
    source=CFD/'cad/full'/('nozzle_W%d_G%d_L%d_ramp%s_mm.stl'%(w,spec['gap_mm'],spec['length_mm'],'_guided' if key=='outer' else ''))
    source_hashes[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest();original=load(source)
    full,outer=wrapped(original,spec)
    body=(full^box([-1000,-1000,-1],[1000,1000,split]))
    body-=box([-1000,-1000,a],[1000,1000,split+.1])-envelope(spec,a,split,MALE_LONG,MALE_SHORT)
    tip=(full^box([-1000,-1000,a],[1000,1000,h+1]))-envelope(spec,a-.1,split,MALE_LONG,MALE_SHORT,CLEAR)
    ys=[-w/2+30,w/2-30] if key!='outer' else [-w/2+30,0,w/2-30]
    body,tip,joint=make_joint(body,tip,spec,a,split,ys,'high',key+'_tip_joint',outer)
    joints=[joint];assembled=[];part_ids=[];designed=[]
    if key=='outer':
        lower=(body^box([-1000,-1000,-1],[1000,1000,67]))-envelope(spec,55,67.001,MALE_LONG,MALE_SHORT,CLEAR)
        upper=body^box([-1000,-1000,55],[1000,1000,split+.1])
        upper-=box([-1000,-1000,54.9],[1000,1000,67])-envelope(spec,55,67,MALE_LONG,MALE_SHORT)
        upper,lower,joint2=make_joint(upper,lower,spec,55,67,[-6,6],'low','outer_body_joint',outer)
        joints.append(joint2)
        for name,obj,z0 in [('outer_inlet',lower,0),('outer_guided_body',upper,55)]:
            assembled.append(export(obj,name,z0));part_ids.append(name);designed.append(obj)
    else:
        name=key+'_body';assembled.append(export(body,name,0));part_ids.append(name);designed.append(body)
    name=key+'_tip_g'+str(spec['gap_mm']);assembled.append(export(tip,name,a));part_ids.append(name);designed.append(tip)
    union=assembled[0]
    overlaps=[]
    for obj in assembled[1:]:
        overlaps.append(abs((union^obj).volume()));union+=obj
    assert max(overlaps)<.05,(key,overlaps)
    zprobe=np.unique(np.r_[np.linspace(25.01,h-.1,int(h*2)),55,67,a,split])
    probe=loft([ring(pw-.15,pd-.15,max(pr-.075,.01),z) for z in zprobe for pw,pd,pr in [profile(z,spec)]])
    nominal=designed[0]
    for obj in designed[1:]:nominal+=obj
    nominal_added=abs(((nominal-original)^probe).volume());nominal_removed=abs(((original-nominal)^probe).volume())
    assert nominal_added<.01 and nominal_removed<.01,(key,'nominal flow',nominal_added,nominal_removed)
    added=abs(((union-original)^probe).volume());removed=abs(((original-union)^probe).volume())
    # Reoriented float32 STLs move the large guide faces by microns. Native
    # ray checks independently compare their surface positions to the source.
    assert added<.5 and removed<.5,(key,'STL flow probe',added,removed)
    hw_records=[]
    for j in joints:
        for i,hw in enumerate(j['hardware']):
            screw=hw.pop('illustrative_screw')
            intrude=abs((screw^probe).volume());collide=abs((screw^union).volume())
            assert intrude<.001 and collide<.01,(j['id'],i,'screw',intrude,collide)
            screw_path=ROOT/'cad'/f'{j["id"]}_screw{i}.stl';mesh(screw).export(screw_path)
            hw.update(flow_intrusion_mm3=intrude,plastic_collision_mm3=collide,screw_envelope_STL=str(screw_path))
            seated=screw.translate([-.16*hw['side_X'],0,0])
            seat_collision=abs((seated^union).volume());seat_intrusion=abs((seated^probe).volume())
            assert seat_collision<.01 and seat_intrusion<.001,(j['id'],i,'additional seating',seat_collision,seat_intrusion)
            hw.update(additional_seating_checked_mm=.16,additional_seating_collision_mm3=seat_collision,
                      additional_seating_flow_intrusion_mm3=seat_intrusion)
            hw_records.append(hw)
    groups.append({'id':key,**{k:spec[k] for k in ['width_mm','gap_mm','height_mm','length_mm']},
                   'parts':part_ids,'tip_visible_seam_Z_mm':a,'nominal_tip_length_mm':55,
                   'joints':joints,'overlap_mm3':overlaps,'added_in_flow_probe_mm3':added,'removed_in_flow_probe_mm3':removed,
                   'nominal_added_in_flow_probe_mm3':nominal_added,'nominal_removed_in_flow_probe_mm3':nominal_removed,
                   'screw_count':len(hw_records),'old_ear_interface_compatible':False})
    print('GROUP_FLOW_AND_FLUSH_CHECKED',key,added,removed,flush=True)

assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in source_hashes.items())
result={'units':'mm','printer_volume_mm':[300,300,300],'brim_allowance_each_side_mm':8,
        'source_hashes_unchanged':source_hashes,'parts':records,'groups':groups,
        'outer_walls_short_long_mm':[WALL_SHORT,WALL_LONG],'male_walls_short_long_mm':[MALE_SHORT,MALE_LONG],
        'radial_telescoping_clearance_mm':CLEAR,'overlap_mm':12,'socket_ID_mm':55.4,'socket_insertion_mm':25,'main_bore_mm':51,
        'external_ears_or_flanges':False,'nominal_flow_preserved':True,'physical_print_fit_strength_seal_verified':False,
        'new_CFD_run':False}
(ROOT/'flush_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ALL_FLUSH_JOINTS_GEOMETRY_VERIFIED',flush=True)
