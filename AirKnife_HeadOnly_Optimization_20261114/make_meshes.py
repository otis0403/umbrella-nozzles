import json
from geometry import ROOT,DESIGNS,activate
from build_mesh import build
for name in ['short216','wide228','wide240','wide252']:
    activate(name);c=DESIGNS[name]
    build('screen_'+name,c['height'],16,span=c['span'],body=200)
(ROOT/'design_matrix.json').write_text(json.dumps(DESIGNS,indent=2),encoding='utf-8')
print('HEAD_ONLY_SCREEN_MESHES_READY',flush=True)
