"""Closed printable PLA solids. Assembly interfaces stay outside the airflow.

Shared split body + three pairs of interchangeable lips. Dimensions in mm.
No edits to original CAD files or printer configuration.
"""
import argparse,hashlib,itertools,json,math,zipfile
from pathlib import Path
import numpy as np
import manifold3d as m
import trimesh
from geometry import ROOT,WALL,HOLES,section,rounded_rect

def loft(rings):
    n=len(rings[0]);nr=len(rings)
    verts=np.vstack(rings).astype(np.float64);faces=[]
    for k in range(nr-1):
        for j in range(n):
            a=k*n+j;b=k*n+(j+1)%n;c=(k+1)*n+(j+1)%n;d=(k+1)*n+j
            faces.extend([(a,b,c),(a,c,d)])
    bottom=len(verts);top=bottom+1
    verts=np.vstack([verts,np.mean(rings[0],axis=0),np.mean(rings[-1],axis=0)])
    for j in range(n):
        faces.append((bottom,(j+1)%n,j))
        faces.append((top,(nr-1)*n+j,(nr-1)*n+(j+1)%n))
    result=m.Manifold(m.Mesh64(verts,np.array(faces,np.uint64)))
    assert result.status()==m.Error.NoError,result.status()
    return result

def rect_loft(zs,profile):
    return loft([[(x,y,z) for x,y in profile(z)] for z in zs])

def box(lo,hi):return m.Manifold.cube(np.array(hi)-lo).translate(lo)

def cylinder(d,length,center,axis='z',segments=48):
    o=m.Manifold.cylinder(length,d/2,circular_segments=segments,center=True)
    if axis=='x':o=o.rotate([0,90,0])
    if axis=='y':o=o.rotate([90,0,0])
    return o.translate(center)

def nut(center,axis='z',length=2.8):
    return cylinder(5.8/math.cos(math.pi/6),length,center,axis,6)

def tube(zs,height,gap):
    outer=rect_loft(zs,lambda z:rounded_rect(section(z,height,gap)[0]+2*WALL,
        section(z,height,gap)[1]+2*WALL,section(z,height,gap)[2]+WALL))
    cuts=[zs[0]-.2]+list(zs)+[zs[-1]+.2]
    inner=rect_loft(cuts,lambda z:rounded_rect(*section(max(zs[0],min(z,zs[-1])),height,gap)))
    return outer-inner

def mesh(obj):
    raw=obj.to_mesh64()
    return trimesh.Trimesh(np.array(raw.vert_properties,copy=True)[:,:3],np.array(raw.tri_verts,copy=True),process=False)

def save3mf(path,vertices,faces,name,translate=(0,0,0)):
    import xml.etree.ElementTree as ET
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    ET.register_namespace('',ns)
    root=ET.Element('{'+ns+'}model',unit='millimeter',attrib={'xml:lang':'en-US'})
    resources=ET.SubElement(root,'resources');obj=ET.SubElement(resources,'object',id='1',type='model',name=name)
    msh=ET.SubElement(obj,'mesh');vs=ET.SubElement(msh,'vertices');ts=ET.SubElement(msh,'triangles')
    for v in vertices:ET.SubElement(vs,'vertex',x=f'{v[0]:.9g}',y=f'{v[1]:.9g}',z=f'{v[2]:.9g}')
    for f in faces:ET.SubElement(ts,'triangle',v1=str(f[0]),v2=str(f[1]),v3=str(f[2]))
    build=ET.SubElement(root,'build');ET.SubElement(build,'item',objectid='1',transform='1 0 0 0 1 0 0 0 1 '+ ' '.join(str(v) for v in translate))
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))

def export(name,obj,rotation,group,parts):
    assert obj.status()==m.Error.NoError,(name,obj.status())
    assert len(obj.decompose())==1,(name,'disconnected',len(obj.decompose()))
    tm=mesh(obj);assert tm.is_watertight and tm.is_winding_consistent and tm.volume>0,name
    reference=ROOT/'cad'/'reference';stls=ROOT/'print'/'STL';mf=ROOT/'print'/'3MF'
    for p in [reference,stls,mf]:p.mkdir(parents=True,exist_ok=True)
    tm.export(reference/(name+'.stl'))
    oriented=mesh(obj.rotate(rotation));bounds=oriented.bounds
    oriented.vertices-=np.r_[bounds.mean(0)[:2],bounds[0,2]]
    dims=oriented.extents
    assert dims[0]<=200.01 and dims[1]<=200.01 and dims[2]<=240.01,(name,dims)
    dest=stls/(name+'_mm.stl');oriented.export(dest)
    reloaded=trimesh.load_mesh(dest,process=True)
    assert reloaded.is_watertight and reloaded.is_winding_consistent,name
    assert len(reloaded.split(only_watertight=False))==1,name
    assert (reloaded.area_faces>1e-10).all(),name
    assert abs(reloaded.volume/tm.volume-1)<2e-5,name
    save3mf(mf/(name+'.3mf'),oriented.vertices,oriented.faces,name,(110,110,0))
    rec={'name':name,'group':group,'rotation_XYZ_deg':rotation,'print_size_mm':dims.tolist(),
         'assembly_bounds_mm':tm.bounds.tolist(),'volume_mm3':float(tm.volume),'approx_PLA_mass_g':float(tm.volume*.00124),
         'triangles':len(tm.faces),'single_closed_component':True,'zero_degenerate_triangles':True,
         'stl_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    parts.append(rec);print('CAD_PART',name,[round(v,2) for v in dims],flush=True)

def build(height):
    B=height-60;parts=[]
    zs=sorted(set([2.5,3.,12.,B]+[float(x) for x in np.linspace(3,B,round(B/2)+1)]))
    body=tube(zs,height,12)
    flange=rect_loft([0.,3.],lambda z:[(x+2,y) for x,y in rounded_rect(120,118,4)])
    aperture=rect_loft([-1.,4.],lambda z:rounded_rect(88,82,3))
    flange=flange-aperture
    for h in HOLES:flange=flange-cylinder(h['d'],6,[h['x'],h['y'],1.5])
    body=body+flange
    print('CAD_FLANGE_12_HOLES_DONE',flush=True)
    # Full rails are split at Y=0 together with the shell. No fastener enters air.
    for side in [-1,1]:
        rings=[]
        for z in zs[1:]:
            d=section(z,height,12)[1];a=d/2+WALL-.6;b=d/2+WALL+10
            x0,x1=sorted([side*a,side*b])
            rings.append([(x0,-6,z),(x1,-6,z),(x1,6,z),(x0,6,z)])
        body=body+loft(rings)
    screw_z=list(np.arange(20,B-10,45))
    split_z=B/2 if B>220 else None
    if split_z is not None:screw_z=[z for z in screw_z if abs(z-split_z)>15]
    for z in screw_z:
        d=section(z,height,12)[1]
        for side in [-1,1]:
            x=side*(d/2+WALL+5)
            body=body-cylinder(3.4,16,[x,0,z],'y')
            body=body-nut([x,-4.6,z],'y')
            # Loose printed dowels; both mating faces can lie flat on the bed.
            zp=z+7;xp=side*(section(zp,height,12)[1]/2+WALL+5)
            body=body-cylinder(3.2,6.4,[xp,0,zp],'y')
    # Four axial screws attach the replaceable lip module at a hard stop.
    coupling_x=20.
    for x in [-coupling_x,coupling_x]:
        for y in [-70.,70.]:
            side=1 if x>0 else -1
            lo,hi=sorted([side*11.8,side*26.])
            body=body+box([lo,y-6,B-6],[hi,y+6,B])
            body=body-cylinder(3.4,10,[x,y,B-3])
            body=body-nut([x,y,B-4.6])
    if split_z is not None:
        w,d,r=section(split_z,height,12)
        collar=rect_loft([split_z-3,split_z+3],lambda z:rounded_rect(w+2*WALL+16,d+2*WALL+16,r+WALL+8))
        cut=rect_loft([split_z-4,split_z+4],lambda z:rounded_rect(w+2*WALL-1,d+2*WALL-1,r+WALL-.5))
        body=body+(collar-cut)
        for x in [-1,1]:
            for y in [-1,1]:body=body-cylinder(3.4,10,[x*(d/2+WALL+4),y*(w/2+WALL+4),split_z])
    comps=body.decompose()
    # Blind alignment bores are enclosed void shells until the mating cut.
    assert body.status()==m.Error.NoError and sum(c.volume()>0 for c in comps)==1,body.status()
    sections=[('body',body)] if split_z is None else [
        ('body_lower',body.trim_by_plane([0,0,-1],-split_z)),
        ('body_upper',body.trim_by_plane([0,0,1],split_z))]
    for prefix,obj in sections:
        # Flow axis upright: internal walls are self-supporting; open halves
        # allow removal of any local support around external bolt ears.
        for label,normal,rotation in [('A',[0,1,0],[0,0,0]),('B',[0,-1,0],[0,0,0])]:
            export(prefix+'_'+label,obj.trim_by_plane(normal,0),rotation,'body',parts)
    for gap in [8.,12.,16.]:
        lip=tube(np.linspace(B,height,61),height,gap)
        # External locating skirt: 0.2 mm radial clearance, no internal step.
        skirt=rect_loft([B-6,B+3],lambda z:rounded_rect(226.,30.,2.4))
        skcut=rect_loft([B-7,B+4],lambda z:rounded_rect(221.2,25.2,1.))
        bridge=rect_loft([B,B+4],lambda z:rounded_rect(226.,30.,2.4))-rect_loft([B-1,B+5],lambda z:rounded_rect(216.,20.,0.))
        socket=skirt-skcut
        # Clearance notches let the socket pass the body's external bolt ears
        # and the two seam rails. These never reach the internal air channel.
        for side in [-1,1]:
            xl,xh=sorted([side*11.6,side*26.2])
            for yc,halfwidth in [(0.,6.2),(-70.,6.2),(70.,6.2)]:
                socket=socket-box([xl,yc-halfwidth,B-6.2],[xh,yc+halfwidth,B])
        lip=lip+socket+bridge
        for x in [-coupling_x,coupling_x]:
            for y in [-70.,70.]:
                lo,hi=sorted([math.copysign(11.8,x),math.copysign(26.,x)])
                lip=lip+box([lo,y-6,B],[hi,y+6,B+6])
                lip=lip-cylinder(3.4,10,[x,y,B+3])
        # Longitudinal external ribs stiffen the slot without internal supports.
        for side in [-1,1]:
            for zc in [B+14,B+44]:
                rings=[]
                for y,ribh in [(-108.,0.),(-92.,16.),(92.,16.),(108.,0.)]:
                    x0=side*(section(zc,height,gap)[1]/2+WALL-.6)
                    x1=side*(section(zc,height,gap)[1]/2+WALL+ribh)
                    lo,hi=sorted([x0,x1])
                    rings.append([(lo,y,zc-1.5),(lo,y,zc+1.5),(hi,y,zc+1.5),(hi,y,zc-1.5)])
                lip=lip+loft(rings)
        for y in [-1,1]:
            yy=114*y
            for zc in [B+13,B+47]:
                yl,yh=sorted([108*y,118*y])
                lip=lip+box([-12,yl,zc-8],[12,yh,zc+8])
                lip=lip-cylinder(3.4,28,[0,yy,zc-3],'x')
                lip=lip-nut([10.6,yy,zc-3],'x')
                lip=lip-cylinder(3.2,6.4,[0,yy,zc+4],'x')
        # A screwdriver must reach each axial coupling screw past both ribs.
        # The access cylinders stay entirely outside the fluid wall.
        for x in [-coupling_x,coupling_x]:
            for y in [-70.,70.]:
                lip=lip-cylinder(10.,height-(B+6.1)+2.,[x,y,(height+B+6.1+2.)/2])
        assert lip.status()==m.Error.NoError and sum(c.volume()>0 for c in lip.decompose())==1,('lip',gap,lip.status())
        for label,normal in [('front',[1,0,0]),('back',[-1,0,0])]:
            export(f'lip_{int(gap):02d}mm_'+label,lip.trim_by_plane(normal,0),[90,0,0],f'lip_{int(gap)}',parts)
    for diameter in [2.6,2.8,3.0]:
        pin=m.Manifold.cylinder(6,diameter/2,circular_segments=32)
        export('alignment_pin_'+str(diameter).replace('.','p')+'x6',pin,[0,0,0],'pins',parts)
    # Three short paired fit coupons: holes give 0.15, 0.20, 0.25 mm radial clearance.
    for diameter in [3.1,3.2,3.3]:
        coupon=box([-6,-6,0],[6,6,5])-cylinder(diameter,8,[0,0,2.5])
        export('fit_coupon_'+str(diameter).replace('.','p'),coupon,[0,0,0],'coupon',parts)
    report={'height_mm':height,'span_mm':216,'gap_options_mm':[8,12,16],'body_lip_joint_Z_mm':B,
        'wall_mm':WALL,'new_design_core_present':False,'internal_vanes':0,
        'flange_XYZ_mm':[118,120,3],'flange_X_offset_mm':2,'original_holes':HOLES,
        'K1C_nominal_build_mm':[220,220,250],'part_design_limit_mm':[200,200,240],
        'filament':'PLA/PLA+','nominal_nozzle_mm':.4,'suggested_layer_mm':.2,
        'joint_radial_clearance_mm':.2,'loose_alignment_pin_diameter_mm':2.8,'alignment_hole_mm':3.2,
        'body_seam_M3x16_count':2*len(screw_z),'lip_module_M3x16_count':4,'lip_half_M3x30_count':4,
        'optional_mid_joint_M3x12_count':4 if split_z else 0,'body_pin_count':2*len(screw_z),'lip_pin_count':4,
        'parts':parts,'physical_print_verified':False,'10_second_drying_verified':False}
    (ROOT/'cad'/'geometry_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CAD_EXPORT_COMPLETE',len(parts),height,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--height',type=float,default=260);build(p.parse_args().height)
