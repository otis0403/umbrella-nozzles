import json
import numpy as np
from geometry import ROOT
for p in sorted((ROOT/'cfd').glob('*/results.json')):
    r=json.loads(p.read_text());d=np.load(p.parent/'outlet_fields.npz')
    key=np.round(d['centroids'][:,1],7)
    vals=[];areas=[]
    for y in np.unique(key):
        m=key==y;vals.append(np.average(d['z-velocity'][m],weights=d['areas'][m]));areas.append(d['areas'][m].sum())
    mean=np.average(vals,weights=areas)
    cv=np.sqrt(np.average((np.array(vals)-mean)**2,weights=areas))/mean
    r['outlet_gap_averaged_long_CV']=float(cv)
    p.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print(p.parent.name,'loss',r['pressure_loss_to_domain_outlet_Pa'],'reverse%',100*r['negative_uz_volume_fraction'],
          'long_CV%',100*cv,flush=True)
