import json
from geometry import ROOT,DESIGNS,activate
from build_mesh import build
names=['retro80','area200d22','area220d22','area200d24']
for name in names:
    activate(name);c=DESIGNS[name]
    build('screen_'+name,c['height'],16,span=252,body=c['body'])
(ROOT/'design_matrix.json').write_text(json.dumps(DESIGNS,indent=2),encoding='utf-8')
print('SCREEN_MESHES_READY',flush=True)
