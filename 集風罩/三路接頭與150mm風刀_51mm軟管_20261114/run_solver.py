import json,time,traceback,sys,hashlib
from geometry import ROOT,nozzle_height
from legacy_study import connect,solve
import ogrid_nozzle_mesh as nm
s=connect(launch=True,cleanup=True);completed=[];stage=int(sys.argv[1]) if len(sys.argv)>1 else 1
try:
    while True:
        planfile=ROOT/f'plan_{stage}.json'
        while not planfile.exists():time.sleep(2)
        plan=json.loads(planfile.read_text(encoding='utf-8'))
        for job in plan['jobs']:
            name=job['name']
            casepath=ROOT/'cfd'/name;checkpoint=casepath/'completed_checkpoint.json'
            signature={k:v for k,v in job.items() if k not in ['warm','batches','reuse_verified']}
            if job['kind']=='adapter' and not job.get('action'):
                table=json.loads((ROOT/'nozzle_pressure_curves.json').read_text());signature['nozzle_curve']=table[str(int(job['gap']))]
            if job.get('reuse_verified') and checkpoint.exists():
                saved=json.loads(checkpoint.read_text());resultfile=casepath/'results.json'
                intact=resultfile.exists() and hashlib.sha256(resultfile.read_bytes()).hexdigest()==saved.get('result_sha256')
                intact=bool(intact and all((casepath/f).exists() and (casepath/f).stat().st_size==v for f,v in saved.get('native_sizes',{}).items()))
                cvfile=casepath/'convergence.json'
                intact=bool(intact and cvfile.exists() and json.loads(cvfile.read_text()).get('engineering_convergence_pass'))
                if intact and saved.get('signature')==signature:
                    print('REUSED_VERIFIED_NATIVE_CASE',name,flush=True);completed.append(name);continue
            if job['kind']=='nozzle':
                nm.CURRENT_LENGTH=job.get('length',120.);nm.CURRENT_SHOULDER=job.get('shoulder',150.);nm.CURRENT_PLENUM=job.get('plenum');height=nozzle_height(nm.CURRENT_LENGTH)
                nm.build(name,height,job['gap'],external=job.get('external',False),fine=job.get('fine',False),reach=400 if job.get('fine') else 250,span=150,body=25)
                solve(s,name,q=job.get('q',1.),pressure=job.get('pressure'),batches=job.get('batches',6),warm=job.get('warm'))
            elif job['kind']=='adapter':
                from adapter_study import run
                run(s,job)
            elif job['kind']=='verify':
                from adapter_study import verify
                verify(s,job['cases'])
            completed.append(name)
            if (casepath/'results.json').exists() and (casepath/'solution.dat.h5').exists():
                from analyze import convergence
                convergence()
                record=dict(signature=signature,result_sha256=hashlib.sha256((casepath/'results.json').read_bytes()).hexdigest(),native_sizes={f:(casepath/f).stat().st_size for f in ['solution.cas.h5','solution.dat.h5']})
                checkpoint.write_text(json.dumps(record,indent=2),encoding='utf-8')
        (ROOT/f'STAGE_{stage}_COMPLETE.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
        print('STAGE_COMPLETE',stage,flush=True)
        if plan.get('final'):break
        stage+=1
finally:
    (ROOT/'completed_cases.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
    s.exit(timeout=15,wait=20);print('OWNED_SOLVER_EXIT_COMPLETED',flush=True)
