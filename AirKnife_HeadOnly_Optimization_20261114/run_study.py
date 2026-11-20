"""Body-preserving optimization. Coordinator selects jet jobs after screening."""
import json,time
import numpy as np
from geometry import ROOT,DESIGNS,activate
from build_mesh import build
from study import connect,solve,reports
while True:
    import subprocess
    old=ROOT.parent/'AirKnife_Performance_Redesign_20261114'
    oldlog=old/'fluent_study.log'
    if oldlog.exists() and 'OWNED_SOLVER_EXIT_COMPLETED' in oldlog.read_text(encoding='utf-8',errors='replace'):break
    time.sleep(2)
s=connect(launch=True,cleanup=True);completed=[]
try:
    rows=[]
    for name in ['short216','wide228','wide240','wide252']:
        r=solve(s,'screen_'+name,q=3.,batches=6,warm=str(ROOT.parent/'AirKnife_16mm_Wider_ANSYS_20261114/cfd/body_H260_W216'));completed.append('screen_'+name)
        d=np.load(ROOT/'cfd'/('screen_'+name)/'outlet_fields.npz');key=np.round(d['centroids'][:,1],7);u=[];a=[]
        for y in np.unique(key):
            m=key==y;u.append(np.average(d['z-velocity'][m],weights=d['areas'][m]));a.append(d['areas'][m].sum())
        mean=np.average(u,weights=a);cv=100*np.sqrt(np.average((np.array(u)-mean)**2,weights=a))/mean
        rows.append({'design':name,'loss_Pa':r['pressure_loss_to_domain_outlet_Pa'],'outlet_span_CV_pct':float(cv),
            'internal_reverse_volume_pct':100*r['negative_uz_volume_fraction']})
        (ROOT/'screen_results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (ROOT/'SCREEN_COMPLETE.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('SCREEN_COMPLETE_WAITING_FOR_JET_PLAN',flush=True)
    while not (ROOT/'jet_plan.json').exists():time.sleep(2)
    plan=json.loads((ROOT/'jet_plan.json').read_text())
    for job in plan['jobs']:
        activate(job['design']);c=DESIGNS[job['design']]
        build(job['case'],c['height'],16,external=True,fine=job.get('fine',False),reach=400 if job.get('fine') else 250,span=c['span'],body=200)
        solve(s,job['case'],pressure=job.get('pressure',400),batches=job.get('batches',7),warm=job.get('warm'));completed.append(job['case'])
    checks=[]
    for name in plan['reopen_cases']:
        p=ROOT/'cfd'/name;r=json.loads((p/'results.json').read_text());s.settings.file.read_case_data(file_name=str(p/'solution.cas.h5'))
        fields=['pin','ptin','min','mout']+(['mambient'] if r['conditions']['external_free_jet'] else [])
        actual=reports(s,fields);error=max(abs(actual[k]-r['reports'][k])/max(abs(r['reports'][k]),1e-8) for k in fields)
        assert error<1e-8,(name,error);checks.append({'case':name,'native_case_data_reopened':True,'max_relative_error':error})
        (ROOT/'cfd/reopen_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8');print('NATIVE_CASE_DATA_REOPENED',name,error,flush=True)
finally:
    (ROOT/'cfd/completed_cases.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
    s.exit(timeout=15,wait=20);print('OWNED_SOLVER_EXIT_COMPLETED',flush=True)
