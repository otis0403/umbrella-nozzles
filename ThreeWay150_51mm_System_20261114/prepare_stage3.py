import time,json
from geometry import ROOT
from analyze import convergence
while not (ROOT/'STAGE_2_COMPLETE.json').exists():time.sleep(3)
cv=convergence();jobs=[];previous=None
for gap in [4,6,8,12]:
    source=f'adapter_H120_g{gap}_100_120';r=json.loads((ROOT/'cfd'/source/'results.json').read_text())
    assert r['network_load_consistency_pass'],(source,r['network_calibration'][-1])
    q=min(r['branch_flow_m3_min']);name=f'jet_g{gap}_long_pipe'
    jobs.append(dict(kind='nozzle',name=name,gap=gap,q=q,length=120,external=True,batches=8,warm=previous or f'curve_g{gap}_q1'))
    previous=name
(ROOT/'plan_3.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
print('STAGE_3_PLAN_READY',[(j['name'],j['q']) for j in jobs],flush=True)
