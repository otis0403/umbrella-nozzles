"""Prepare rendering and independent file verification inside this new folder."""
import shutil
from geometry import ROOT
SOURCE=ROOT.parent/'AirKnife_K1C_OnePieceBody_20261110'
text=(SOURCE/'blender_preview.py').read_text(encoding='utf-8')
text=text.replace('K1C_onepiece_body_airknife.blend','K1C_two_piece_airknife.blend')
old="ob.location.z+=45;ob.location.x+=-25 if ob.name.endswith('_back') else 25"
assert old in text;text=text.replace(old,'ob.location.z+=45')
(ROOT/'blender_preview.py').write_text(text,encoding='utf-8')
shutil.copyfile(SOURCE/'verify_delivery.py',ROOT/'verify_delivery.py')
text=(SOURCE/'verify_blend.py').read_text(encoding='utf-8')
text=text.replace('K1C_onepiece_body_airknife.blend','K1C_two_piece_airknife.blend')
old="assert len(col.objects)==(1 if name=='body' else 2),name"
assert old in text;text=text.replace(old,'assert len(col.objects)==1,name')
(ROOT/'verify_blend.py').write_text(text,encoding='utf-8')
print('TWO_PIECE_PREVIEW_SCRIPTS_READY',flush=True)
