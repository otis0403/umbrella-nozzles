import time,json
from geometry import ROOT
from network import curves
while not (ROOT/'STAGE_1_COMPLETE.json').exists():time.sleep(3)
c=curves();print('NOZZLE_CURVES',json.dumps(c),flush=True)
from analyze import convergence
cv=convergence()
jobs=[dict(kind='adapter',action='resume_nozzle',name=n,batches=5) for n,v in cv.items() if not v['engineering_convergence_pass']]
jobs.append(dict(kind='adapter',action='refresh_curves',name='refresh_curves'))
previous=None
for gap in [4,6,8,12]:
    for center,side,label in [(1.,1.2,'100_120'),(.6,.8,'60_80'),(.5,.7,'50_70')]:
        name=f'adapter_H120_g{gap}_{label}'
        jobs.append(dict(kind='adapter',name=name,gap=gap,height=120,neck=46,center=center,side=side,warm=previous,batches=7));previous=name
(ROOT/'plan_2.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
print('STAGE_2_PLAN_WRITTEN',flush=True)
