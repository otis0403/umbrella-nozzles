"""Seven real Fluent solves in one explicitly owned local solver session."""
import json
from geometry import ROOT
from study import connect,solve,reports
s=connect(launch=True,cleanup=True)
completed=[]
try:
    for h,w in [(260,216),(320,252),(360,252)]:
        name=f'body_H{h}_W{w}';solve(s,name,q=3.,batches=6);completed.append(name)
    for h,w in [(260,216),(320,252),(360,252)]:
        name=f'jet_H{h}_W{w}';solve(s,name,pressure=400.,batches=6,warm=(str(ROOT.parent/'AirKnife_K1C_20261105/cfd/jet_g16') if h==260 else 'jet_H260_W216' if h==320 else 'jet_H320_W252'));completed.append(name)
    name='jet_H320_W252_fine'
    solve(s,name,pressure=400.,batches=6,warm='jet_H320_W252');completed.append(name)
    checks=[]
    for name in ['body_H320_W252','jet_H260_W216','jet_H320_W252','jet_H360_W252','jet_H320_W252_fine']:
        folder=ROOT/'cfd'/name;r=json.loads((folder/'results.json').read_text())
        s.settings.file.read_case_data(file_name=str(folder/'solution.cas.h5'))
        fields=['pin','ptin','min','mout']
        if r['conditions']['external_free_jet']:fields.append('mambient')
        actual=reports(s,fields)
        error=max(abs(actual[k]-r['reports'][k])/max(abs(r['reports'][k]),1e-8) for k in fields)
        assert error<1e-8,(name,error)
        checks.append({'case':name,'native_case_data_reopened':True,'max_relative_report_difference':error})
        (ROOT/'cfd/reopen_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
        print('NATIVE_CASE_DATA_REOPENED',name,error,flush=True)
finally:
    (ROOT/'cfd/completed_cases.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
    s.exit(timeout=15,wait=20)
    print('OWNED_SOLVER_EXIT_COMPLETED',flush=True)
