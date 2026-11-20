"""Reuse the already checked CAD reader without touching the prior deliverable."""
import shutil
from geometry import ROOT
SOURCE=ROOT.parent/'AirKnife_K1C_20261105'
text=(SOURCE/'blender_preview.py').read_text(encoding='utf-8')
old="for ob in collections['body'].objects:ob.location.y+=-30 if ob.name.endswith('_B') else 30\n"
assert old in text
text=text.replace(old,'')
text=text.replace('K1C_modular_airknife.blend','K1C_onepiece_body_airknife.blend')
text=text.replace('scene.cycles.samples=32','scene.cycles.samples=24')
text=text.replace('scene.render.threads=2','scene.render.threads=6')
text=text.replace('resolution_x=1500','resolution_x=1200').replace('resolution_y=1300','resolution_y=1100')
(ROOT/'blender_preview.py').write_text(text,encoding='utf-8')
shutil.copyfile(SOURCE/'verify_delivery.py',ROOT/'verify_delivery.py')
text=(SOURCE/'verify_blend.py').read_text(encoding='utf-8')
text=text.replace('K1C_modular_airknife.blend','K1C_onepiece_body_airknife.blend')
text=text.replace("assert len(col.objects)==2,name","assert len(col.objects)==(1 if name=='body' else 2),name")
(ROOT/'verify_blend.py').write_text(text,encoding='utf-8')
print('PREVIEW_AND_READBACK_SCRIPTS_PREPARED',flush=True)
