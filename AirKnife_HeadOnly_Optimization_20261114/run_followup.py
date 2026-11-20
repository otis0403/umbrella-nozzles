"""Staged head-only jobs; a coordinator writes each next plan after reading results."""
import json,time
from geometry import ROOT,DESIGNS,activate
from build_mesh import build
from study import connect,solve,reports
while 'OWNED_SOLVER_EXIT_COMPLETED' not in (ROOT/'fluent_study.log').read_text(encoding='utf-8',errors='replace'):time.sleep(2)
s=connect(launch=True,cleanup=True);completed=[];checks=[];stage=1
try:
    while True:
        planfile=ROOT/f'followup_plan_{stage}.json'
        while not planfile.exists():time.sleep(2)
        plan=json.loads(planfile.read_text())
        for job in plan['jobs']:
            activate(job['design']);c=DESIGNS[job['design']]
            build(job['case'],c['height'],16,external=job.get('external',True),fine=job.get('fine',False),
                reach=400 if job.get('fine') else 250,span=c['span'],body=200)
            solve(s,job['case'],q=3.,pressure=job.get('pressure',400) if job.get('external',True) else None,
                batches=job.get('batches',7),warm=job.get('warm'));completed.append(job['case'])
            if job.get('verify',True):
                p=ROOT/'cfd'/job['case'];r=json.loads((p/'results.json').read_text());s.settings.file.read_case_data(file_name=str(p/'solution.cas.h5'))
                names=['pin','ptin','min','mout']+(['mambient'] if r['conditions']['external_free_jet'] else [])
                actual=reports(s,names);error=max(abs(actual[k]-r['reports'][k])/max(abs(r['reports'][k]),1e-8) for k in names)
                assert error<1e-8;checks.append({'case':job['case'],'native_case_data_reopened':True,'max_relative_error':error})
                (ROOT/'cfd/followup_reopen_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
        (ROOT/f'FOLLOWUP_STAGE_{stage}_COMPLETE.json').write_text(json.dumps({'completed':completed},indent=2),encoding='utf-8')
        print('FOLLOWUP_STAGE_COMPLETE',stage,flush=True)
        if plan.get('final',False):break
        stage+=1
finally:
    (ROOT/'cfd/followup_completed_cases.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
    s.exit(timeout=15,wait=20);print('OWNED_FOLLOWUP_SOLVER_EXIT_COMPLETED',flush=True)
