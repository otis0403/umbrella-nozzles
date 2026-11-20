import time,json
from geometry import ROOT
while not (ROOT/'STAGE_11_COMPLETE.json').exists():time.sleep(3)
source='adapter_H120_g16_100_120';r=json.loads((ROOT/'cfd'/source/'results.json').read_text());assert r['network_load_consistency_pass']
q=min(r['branch_flow_m3_min'])
jobs=[dict(kind='adapter',name='adapter_H110_g16_100_120',height=110,neck=46,gap=16,center=1.,side=1.2,warm=source,batches=7),
      dict(kind='adapter',name='reference_old_layout_g16_100_120',height=155,neck=46,gap=16,center=1.,side=1.2,reference=True,batches=7),
      dict(kind='nozzle',name='jet_g16_L120_long_pipe',gap=16,q=q,length=120,external=True,batches=9,warm='curve_g16_q2.5'),
      dict(kind='nozzle',name='curve_g16_L80_q1',gap=16,q=1.,length=80,batches=7,warm='curve_g16_q1'),
      dict(kind='nozzle',name='curve_g16_L80_q2.5',gap=16,q=2.5,length=80,batches=7,warm='curve_g16_L80_q1')]
(ROOT/'plan_12.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
print('STAGE_12_PLAN_READY',q,flush=True)
