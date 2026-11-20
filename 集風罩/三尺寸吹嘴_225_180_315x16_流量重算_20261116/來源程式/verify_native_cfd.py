"""Fresh Fluent read of saved native case/data, without additional iterations."""
import json
import hashlib
import numpy as np
from design import ROOT, write_json
from cfd_solver import connect, reports, PRIVATE

selection=json.loads((ROOT/'selection.json').read_text())
names=[selection[key]['case'] for key in ['inner','center','outer']]
curves=json.loads((ROOT/'selected_pressure_curves.json').read_text())
names+= [point['case'] for curve in curves.values() for point in curve['points']]
names+= [p.parent.name for p in (ROOT/'cfd').glob('network_*/results.json')]
names+= [p.parent.name for p in (ROOT/'cfd').glob('jet_*/results.json')]
names=list(dict.fromkeys(names))
s=connect(launch=True,cleanup=True)
records=[]
try:
    for name in names:
        folder=ROOT/'cfd'/name
        result=json.loads((folder/'results.json').read_text())
        s.settings.file.read_case_data(file_name=str(folder/'solution.cas.h5'))
        s.tui.mesh.check()
        variables=s.fields.solution_variable_data
        volumes=variables.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
        assert np.isfinite(volumes).all() and volumes.min()>0
        keys=[key for key in result['reports'] if key not in ['batch','elapsed_s']]
        got=reports(s,keys)
        relative={key:abs(value-result['reports'][key])/max(abs(result['reports'][key]),1e-5) for key,value in got.items()}
        assert max(relative.values())<2e-7,(name,relative)
        row={'case':name,'cell_count':len(volumes),'minimum_cell_volume_m3':float(volumes.min()),
             'native_reports_reproduced':True,'maximum_relative_report_difference':max(relative.values()),
             'native_case_sha256':hashlib.sha256((folder/'solution.cas.h5').read_bytes()).hexdigest(),
             'native_data_sha256':hashlib.sha256((folder/'solution.dat.h5').read_bytes()).hexdigest()}
        records.append(row);write_json(ROOT/'native_cfd_readback.json',records)
        print('NATIVE_CASE_DATA_VERIFIED',json.dumps(row),flush=True)
finally:
    s.exit(timeout=20,wait=30);PRIVATE.unlink(missing_ok=True)
print('ALL_NATIVE_CASE_DATA_READBACK_COMPLETE',len(records),flush=True)
