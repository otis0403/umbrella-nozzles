import json
from build_mesh import build
from geometry import ROOT
cases=[]
for h,w,b in [(260,216,200),(320,252,200),(360,252,200)]:
    for external,prefix in [(False,'body'),(True,'jet')]:
        name=f'{prefix}_H{h}_W{w}'
        build(name,h,16,external=external,span=w,body=b)
        cases.append({'name':name,'height_mm':h,'span_mm':w,'gap_mm':16,'body_height_mm':b,'external':external})
build('jet_H320_W252_fine',320,16,external=True,fine=True,reach=400,span=252,body=200)
cases.append({'name':'jet_H320_W252_fine','height_mm':320,'span_mm':252,'gap_mm':16,'body_height_mm':200,'external':True})
(ROOT/'case_matrix.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
print('ALL_STUDY_MESHES_READY',flush=True)
