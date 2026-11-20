"""Refresh the just-created prototype package after report-only updates."""
import json,subprocess,sys,zipfile,hashlib,shutil
from pathlib import PurePosixPath
from geometry import ROOT

state=json.loads((ROOT/'DELIVERY_COMPLETE.json').read_text(encoding='utf-8'))
from pathlib import Path
dest=Path(state['delivery_directory']).resolve();scope=(ROOT.parent/'集風罩').resolve()
assert dest.is_relative_to(scope) and dest.name.startswith('三路接頭與150mm風刀_51mm軟管_20261114') and dest.is_dir()
subprocess.run([sys.executable,'finalize_delivery.py'],cwd=ROOT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert (ROOT/'verification_matrix.csv').exists()
pack=ROOT/'ThreeWay_51mm_150x16_PrintPack.zip'
with zipfile.ZipFile(pack) as z:
    assert z.testzip() is None
    for name in z.namelist():
        p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
    assert 'verification_matrix.csv' in z.namelist()
    z.extractall(dest)
shutil.copyfile(pack,dest/pack.name);shutil.copyfile(ROOT/'package_checks.json',dest/'package_checks.json')
assert hashlib.sha256(pack.read_bytes()).digest()==hashlib.sha256((dest/pack.name).read_bytes()).digest()
state['report_refreshed_with_verification_matrix']=True
(ROOT/'DELIVERY_COMPLETE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print('DELIVERY_REFRESHED',json.dumps(state,ensure_ascii=True),flush=True)
