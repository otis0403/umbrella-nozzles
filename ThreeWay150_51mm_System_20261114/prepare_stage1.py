import json
from geometry import ROOT
jobs=[];previous=None
for gap in [4,6,8,12]:
    for q in [1.,1.8]:
        name=f'curve_g{gap}_q{q:g}'
        jobs.append(dict(kind='nozzle',name=name,gap=gap,q=q,batches=6,warm=previous));previous=name
(ROOT/'plan_1.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
