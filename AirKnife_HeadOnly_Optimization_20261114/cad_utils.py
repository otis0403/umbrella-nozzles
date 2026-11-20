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

