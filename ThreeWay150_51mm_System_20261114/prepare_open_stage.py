import json
from geometry import ROOT
q=1.8170393240860634
jobs=[]
for length,shoulder,warm in [(120,150,'jet_g16_L120_long_pipe'),(120,170,'jet_g16_L120_W170_screen'),(80,150,'jet_g16_L80_W150_screen'),(150,150,'jet_g16_L150_W150_screen')]:
    jobs.append(dict(kind='nozzle',name=f'open_L{length}_W{shoulder}',gap=16,q=q,length=length,shoulder=shoulder,external=True,batches=9,warm=warm,reuse_verified=True))
(ROOT/'plan_40.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
