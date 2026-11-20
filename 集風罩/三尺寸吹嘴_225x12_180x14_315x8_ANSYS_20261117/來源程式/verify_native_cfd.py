import hashlib
import json
import numpy as np
from design import ROOT,write_json
from cfd_solver import connect,reports,PRIVATE

folders=[p.parent for p in (ROOT/'cfd').glob('*/completed_checkpoint.json')]
s=connect(launch=True,cleanup=True);rows=[]
try:
    for folder in sorted(folders):
        r=json.loads((folder/'results.json').read_text())
        s.settings.file.read_case_data(file_name=str(folder/'solution.cas.h5'));s.tui.mesh.check()
        volume=s.fields.solution_variable_data.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
        assert np.isfinite(volume).all() and volume.min()>0
        keys=[key for key in r['reports'] if key not in ['batch','elapsed_s']]
        values=reports(s,keys)
        difference=max(abs(value-r['reports'][key])/max(abs(r['reports'][key]),1e-5) for key,value in values.items())
        assert difference<2e-7,(folder.name,difference)
        rows.append({'case':folder.name,'cell_count':len(volume),'minimum_cell_volume_m3':float(volume.min()),
                     'maximum_relative_report_difference':difference,'native_reports_reproduced':True,
                     'case_sha256':hashlib.sha256((folder/'solution.cas.h5').read_bytes()).hexdigest(),
                     'data_sha256':hashlib.sha256((folder/'solution.dat.h5').read_bytes()).hexdigest()})
        write_json(ROOT/'native_cfd_readback.json',rows);print('NATIVE_VERIFIED',folder.name,flush=True)
finally:
    s.exit(timeout=20,wait=30);PRIVATE.unlink(missing_ok=True)
print('NATIVE_READBACK_FINISHED',flush=True)
