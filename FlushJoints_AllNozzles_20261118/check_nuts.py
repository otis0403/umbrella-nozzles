"""Check standard nut envelopes independently against reloaded print solids."""
import json,math,sys
from pathlib import Path
import numpy as np
import trimesh,manifold3d as m
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'InnerMiddle_12_14_8_ANSYS_20261117'))
from cad_utils import cylinder,mesh,loft
from build_parts import ring
import design
data=json.loads((ROOT/'flush_checks.json').read_text(encoding='utf-8-sig'))
parts={r['id']:r for r in data['parts']};result=[]
for group in data['groups']:
    design.GAP=group['gap_mm']
    zs=np.linspace(25.01,group['height_mm']-.1,round(group['height_mm']*2))
    probe=loft([ring(w-.15,d-.15,max(r-.075,.01),z) for z in zs
                for w,d,r in [design.profile(z,group['width_mm'],group['length_mm'],'ramp')]])
    solid=None
    for name in group['parts']:
        row=parts[name];tri=trimesh.load_mesh(row['STL'],process=True);tri.apply_transform(np.array(row['assembly_from_print']))
        obj=m.Manifold(m.Mesh64(tri.vertices.astype(np.float64),tri.faces.astype(np.uint64)))
        assert obj.status()==m.Error.NoError
        solid=obj if solid is None else solid+obj
    for joint in group['joints']:
        for i,hw in enumerate(joint['hardware']):
            side=hw['side_X'];y,z=hw['center_YZ_mm'];x=(hw['nut_slot_X_abs_mm'][1]-1.2)*side
            nut=cylinder(5.5/math.cos(math.pi/6),2.4,[x,y,z],axis='x',segments=6)
            nut-=cylinder(3,3,[x,y,z],axis='x',segments=64)
            collision=abs((nut^solid).volume());assert collision<.01,(joint['id'],i,collision)
            intrusion=abs((nut^probe).volume());assert intrusion<.001,(joint['id'],i,'nut flow intrusion',intrusion)
            file=ROOT/'cad'/f'{joint["id"]}_nut{i}.stl';mesh(nut).export(file)
            hw['nut_envelope_STL']=str(file);hw['nut_collision_mm3']=collision;hw['nut_flow_intrusion_mm3']=intrusion
            result.append({'joint':joint['id'],'index':i,'collision_mm3':collision,'flow_intrusion_mm3':intrusion})
(ROOT/'flush_checks.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
(ROOT/'nut_checks.json').write_text(json.dumps({'all_nuts_fit_reloaded_plastic':True,'nut_count':len(result),'results':result},indent=2),encoding='utf-8')
print('ALL_18_CAPTIVE_NUTS_FIT',len(result),flush=True)
