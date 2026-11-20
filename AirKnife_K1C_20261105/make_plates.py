"""Portable 3MF model plates. No G-code or printer firmware changes."""
import json,zipfile
from pathlib import Path
import numpy as np
import trimesh
import xml.etree.ElementTree as ET
from geometry import ROOT
records=json.loads((ROOT/'cad'/'geometry_checks.json').read_text())['parts']
byname={r['name']:r for r in records}
dest=ROOT/'print'/'plates';dest.mkdir(exist_ok=True)

def plate(name,items):
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',ns)
    model=ET.Element('{'+ns+'}model',unit='millimeter');res=ET.SubElement(model,'resources');build=ET.SubElement(model,'build')
    bounds=[]
    for idx,(part,cx,cy) in enumerate(items,1):
        tm=trimesh.load_mesh(ROOT/'print'/'STL'/(part+'_mm.stl'),process=True)
        ob=ET.SubElement(res,'object',id=str(idx),type='model',name=part)
        msh=ET.SubElement(ob,'mesh');vs=ET.SubElement(msh,'vertices');ts=ET.SubElement(msh,'triangles')
        for v in tm.vertices:ET.SubElement(vs,'vertex',x=f'{v[0]:.9g}',y=f'{v[1]:.9g}',z=f'{v[2]:.9g}')
        for f in tm.faces:ET.SubElement(ts,'triangle',v1=str(f[0]),v2=str(f[1]),v3=str(f[2]))
        ET.SubElement(build,'item',objectid=str(idx),transform=f'1 0 0 0 1 0 0 0 1 {cx} {cy} 0')
        b=tm.bounds.copy();b[:,:2]+=[cx,cy]
        assert b[0,0]>=5 and b[0,1]>=5 and b[1,0]<=215 and b[1,1]<=215 and b[1,2]<=240,(part,b)
        bounds.append({'name':part,'bounds_mm':b.tolist()})
    filename=dest/(name+'.3mf')
    with zipfile.ZipFile(filename,'w',zipfile.ZIP_DEFLATED) as z:
        template=ROOT/'print'/'3MF'/(items[0][0]+'.3mf')
        with zipfile.ZipFile(template) as old:
            for item in ['[Content_Types].xml','_rels/.rels']:z.writestr(item,old.read(item))
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
    with zipfile.ZipFile(filename) as z:
        assert z.testzip() is None
        parsed=ET.fromstring(z.read('3D/3dmodel.model'))
        assert parsed.attrib['unit']=='millimeter'
    return {'file':str(filename.relative_to(ROOT)),'models':bounds,'within_K1C_with_5mm_brim':True,
            'model_plate_only_not_sliced':True}

allplates=[]
coupon=[('fit_coupon_3p1',65,90),('fit_coupon_3p2',110,90),('fit_coupon_3p3',155,90)]
coupon += [('alignment_pin_2p8x6',85+10*i,115+10*j) for j in range(4) for i in range(4)]
allplates.append(plate('00_fit_test_and_16_pins',coupon))
for name in ['body_A','body_B']:allplates.append(plate('01_'+name if name.endswith('A') else '02_'+name,[(name,110,110)]))
for gap in [8,12,16]:
    allplates.append(plate(f'03_lip_{gap:02d}mm_pair',[(f'lip_{gap:02d}mm_front',75,110),(f'lip_{gap:02d}mm_back',145,110)]))
(ROOT/'print'/'plate_checks.json').write_text(json.dumps(allplates,indent=2),encoding='utf-8')
print('PORTABLE_3MF_PLATES_VERIFIED',len(allplates))
