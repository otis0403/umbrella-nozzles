import json
from geometry import ROOT
from study import connect,reports
s=connect(launch=True,cleanup=True)
checks=[]
for name in ['H260','jet_g8','jet_g12','jet_g16','jet_check12']:
    folder=ROOT/'cfd'/name;r=json.loads((folder/'results.json').read_text())
    s.settings.file.read_case_data(file_name=str(folder/'solution.cas.h5'))
    fields=['pin','ptin','min','mout']
    if r['conditions']['external_free_jet']:fields.append('mambient')
    actual=reports(s,fields)
    error=max(abs(actual[k]-r['reports'][k])/max(abs(r['reports'][k]),1e-8) for k in fields)
    assert error<1e-8,(name,error)
    checks.append({'name':name,'case_and_data_reopened':True,'native_report_max_relative_error':error})
    (ROOT/'cfd'/'reopen_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('CASE_DATA_REOPENED',name,error,flush=True)
s.exit(timeout=15,wait=20)
print('STUDY_SOLVER_EXIT_REQUEST_COMPLETED',flush=True)
