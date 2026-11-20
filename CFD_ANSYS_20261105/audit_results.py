"""Independent checks on the exported numeric arrays, not a replacement for CFD validation."""
import json
from pathlib import Path
import numpy as np
from session import ROOT

checks=[]
for file in sorted(ROOT.glob('*/Q*/results.json')):
    case=file.parent
    data=np.load(case/'cell_fields.npz')
    result=json.loads(file.read_text(encoding='utf-8'))
    mesh=json.loads((case.parent/'mesh_summary.json').read_text())
    xyz=data['SV_CENTROID'].reshape(-1,3)
    vol=data['SV_VOLUME'];w=data['SV_W']
    assert len(vol)==mesh['cells']==len(w)==len(xyz)
    assert all(np.isfinite(v).all() for v in data.values())
    assert vol.min()>0 and data['SV_K'].min()>=0 and data['SV_O'].min()>0
    assert abs(vol.sum()/mesh['volume_m3']-1)<1e-8
    fractions={}
    for label,lo,hi in [('inlet_transition',0,.05),('middle',.05,.13),
                        ('short_vane_tip',.13,.14),('long_vane_tip',.14,.15),('final_channel',.15,.201)]:
        mask=(xyz[:,2]>=lo)&(xyz[:,2]<hi)&(w<-.01)
        fractions[label]={'reverse_cell_count':int(mask.sum()),
            'reverse_volume_fraction_of_whole_domain':float(vol[mask].sum()/vol.sum())}
    result['reverse_volume_by_axial_region']=fractions
    file.write_text(json.dumps(result,indent=2),encoding='utf-8')
    outlet=np.load(case/'outlet_fields.npz')
    assert np.isfinite(outlet['z-velocity']).all()
    assert len(outlet['offsets'])-1==len(outlet['z-velocity'])
    assert (outlet['areas_m2']>0).all()
    assert abs(outlet['areas_m2'].sum()/.002592-1)<1e-5
    for p in case.glob('*.h5'):
        assert p.stat().st_size>1000
        assert p.open('rb').read(8)==b'\x89HDF\r\n\x1a\n',p.name
    check={'case':str(case.relative_to(ROOT)),'cell_count_matches_mesh':True,'all_fields_finite':True,
        'positive_cell_volumes':True,'nonnegative_k_and_positive_omega':True,
        'exported_cell_volume_matches_original_mesh':True,'outlet_area_matches':True,
        'reverse_volume_fraction':float(vol[w<-.01].sum()/vol.sum()),
        'minimum_axial_velocity_position_m':xyz[w.argmin()].tolist()}
    checks.append(check)
(ROOT/'exported_data_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps(checks,indent=2))
