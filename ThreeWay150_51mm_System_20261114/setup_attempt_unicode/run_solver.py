import json,time,traceback
from geometry import ROOT,nozzle_height
from legacy_study import connect,solve
import ogrid_nozzle_mesh as nm
s=connect(launch=True,cleanup=True);completed=[];stage=1
try:
    while True:
        planfile=ROOT/f'plan_{stage}.json'
        while not planfile.exists():time.sleep(2)
        plan=json.loads(planfile.read_text(encoding='utf-8'))
        for job in plan['jobs']:
            name=job['name']
            if job['kind']=='nozzle':
                nm.CURRENT_LENGTH=job.get('length',120.);height=nozzle_height(nm.CURRENT_LENGTH)
                nm.build(name,height,job['gap'],external=job.get('external',False),fine=job.get('fine',False),reach=400 if job.get('fine') else 250,span=150,body=25)
                solve(s,name,q=job.get('q',1.),pressure=job.get('pressure'),batches=job.get('batches',6),warm=job.get('warm'))
            elif job['kind']=='adapter':
                from adapter_study import run
                run(s,job)
            elif job['kind']=='verify':
                from adapter_study import verify
                verify(s,job['cases'])
            completed.append(name)
        (ROOT/f'STAGE_{stage}_COMPLETE.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
        print('STAGE_COMPLETE',stage,flush=True)
        if plan.get('final'):break
        stage+=1
finally:
    (ROOT/'completed_cases.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
    s.exit(timeout=15,wait=20);print('OWNED_SOLVER_EXIT_COMPLETED',flush=True)
