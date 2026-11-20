import hashlib,itertools,json
from pathlib import Path
import numpy as np
import manifold3d as m
import trimesh
from geometry import ROOT

report=json.loads((ROOT/'cad'/'geometry_checks.json').read_text())
parts={}
for r in report['parts']:
    if r['group'] in ['pins','coupon']:continue
    tm=trimesh.load_mesh(ROOT/'cad'/'reference'/(r['name']+'.stl'),process=True)
    obj=m.Manifold(m.Mesh64(np.array(tm.vertices),np.array(tm.faces,dtype=np.uint64)))
    assert obj.status()==m.Error.NoError,r['name']
    parts[r['name']]=obj
checks=[]
tool_checks=[]
for gap in [8,12,16]:
    names=[r['name'] for r in report['parts'] if r['group'] in ['body',f'lip_{gap}']]
    for a,b in itertools.combinations(names,2):
        intersection=(parts[a]^parts[b]).volume()
        assert intersection<.02,(gap,a,b,intersection)
        checks.append({'gap_mm':gap,'parts':[a,b],'interference_volume_mm3':intersection})
    B=report['body_lip_joint_Z_mm'];H=report['height_mm']
    for x in [-20.,20.]:
        for y in [-70.,70.]:
            tool=m.Manifold.cylinder(H-B-4,4.,circular_segments=32,center=True).translate([x,y,(H+B+8.4)/2])
            hit=sum((parts[n]^tool).volume() for n in names)
            assert hit<.02,(gap,x,y,'screwdriver obstructed',hit)
            tool_checks.append({'gap_mm':gap,'coupling_screw_XY_mm':[x,y],'tool_diameter_mm':8,'blocked_volume_mm3':hit})
record={'no_part_interferences':True,'pair_checks':checks,'screwdriver_access_checks':tool_checks,'raw_source_stl_sha256':
        hashlib.sha256(next(p for p in ROOT.parent.rglob('*.stl') if '\u7121\u6838\u5fc3_20261105' in str(p.parent)).read_bytes()).hexdigest()}
assert record['raw_source_stl_sha256']=='6f8f9ca5d755b9c6a77b417ffdef844ebb825ae8b044a93c8e071cddce0158cc'
(ROOT/'cad'/'assembly_interference_checks.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('ASSEMBLY_INTERFERENCE_AND_ORIGINAL_SOURCE_VERIFIED',len(checks),flush=True)
