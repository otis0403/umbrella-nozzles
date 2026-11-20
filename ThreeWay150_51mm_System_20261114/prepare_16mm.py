import json,time
from geometry import ROOT
from analyze import convergence
from scipy.optimize import nnls
import numpy as np

jobs=[dict(kind='nozzle',name='curve_g16_q1',gap=16,q=1.,length=120,batches=7,warm='curve_g12_q1'),
      dict(kind='nozzle',name='curve_g16_q2.5',gap=16,q=2.5,length=120,batches=7,warm='curve_g16_q1')]
(ROOT/'plan_10.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
while not (ROOT/'STAGE_10_COMPLETE.json').exists():time.sleep(3)
points=[]
for n in ['curve_g16_q1','curve_g16_q2.5']:
    r=json.loads((ROOT/'cfd'/n/'results.json').read_text());points.append([r['nozzle_flow_m3_min'],r['reports']['ptin']])
a=np.array(points);coeff,_=nnls(np.c_[a[:,0]**2,a[:,0]],a[:,1]);data=json.loads((ROOT/'nozzle_pressure_curves.json').read_text())
data['16']=dict(a_Pa_per_Q2=float(coeff[0]),b_Pa_per_Q=float(coeff[1]),points=points,geometry_length_mm=120,max_fit_error_pct=float(np.max(abs((coeff[0]*a[:,0]**2+coeff[1]*a[:,0])/a[:,1]-1))*100))
(ROOT/'nozzle_pressure_curves.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
cv=convergence();jobs=[dict(kind='adapter',action='resume_nozzle',name=n,batches=5) for n in ['curve_g16_q1','curve_g16_q2.5'] if not cv[n]['engineering_convergence_pass']]
for center,side,label in [(1.,1.2,'100_120'),(.6,.8,'60_80'),(.5,.7,'50_70')]:
    jobs.append(dict(kind='adapter',name='adapter_H120_g16_'+label,gap=16,height=120,neck=46,center=center,side=side,batches=8,warm=None if label=='100_120' else 'adapter_H120_g16_'+('100_120' if label=='60_80' else '60_80')))
(ROOT/'plan_11.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
print('GAP16_NETWORK_PLAN_READY',json.dumps(data['16']),flush=True)
