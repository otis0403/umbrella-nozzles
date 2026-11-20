"""Check the downward assembly path of each continuous lip, not only final fit."""
import json
import numpy as np
from geometry import ROOT
from build_lips import read_obj
body=read_obj(ROOT/'cad/reference/body_onepiece.stl')
checks=[]
for gap in [8,12,16]:
    lip=read_obj(ROOT/f'cad/reference/lip_{gap:02d}mm_onepiece_no_ribs.stl')
    positions=[]
    for dz in np.linspace(0,6.2,9):
        volume=(body^lip.translate([0,0,float(dz)])).volume()
        assert volume<.02,(gap,dz,volume)
        positions.append({'offset_Z_mm':float(dz),'interference_mm3':volume})
    checks.append({'gap_mm':gap,'sampled_axial_insertion_path_clear':True,'sampled_positions':positions})
(ROOT/'cad/insertion_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('AXIAL_INSERTION_SAMPLES_CLEAR',len(checks)*9,flush=True)
