"""Wait for actual CFD completion, then build, independently verify and package."""
import json,os,subprocess,sys,time,zipfile,hashlib,shutil
from pathlib import Path,PurePosixPath
from geometry import ROOT

def run(log,args):
    env=os.environ.copy();env['PYTHONUTF8']='1'
    with (ROOT/log).open('w',encoding='utf-8') as out:
        result=subprocess.run(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,(log,result.returncode)
    print('DELIVERY_CHECK_FINISHED',log,flush=True)

while not (ROOT/'selected_shape_work.json').exists():time.sleep(5)
shape=json.loads((ROOT/'selected_shape_work.json').read_text())
s=dict(adapter_height_mm=110,neck_mm=46,nozzle_length_mm=shape['length_mm'],nozzle_shoulder_mm=shape['shoulder_mm'],nozzle_plenum_mm=shape.get('plenum_mm'))
args=[sys.executable,'build_cad.py','--height',str(s['adapter_height_mm']),'--neck',str(s['neck_mm']),
    '--gap','16','--length',str(s['nozzle_length_mm']),'--shoulder',str(s['nozzle_shoulder_mm'])]
if s.get('nozzle_plenum_mm') is not None:args+=['--plenum',str(s['nozzle_plenum_mm'])]
if '--reuse-cad' in sys.argv:
    assert json.loads((ROOT/'CAD_PREPARED_WAITING_CFD.json').read_text())==s
    geo=json.loads((ROOT/'cad/geometry_checks.json').read_text())
    for part in geo['parts']:
        path=ROOT/'print/STL'/(part['name']+'_mm.stl')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==part['sha256']
    assert json.loads((ROOT/'cad/native_reopen_checks.json').read_text())['native_blend_reopened']
    assert (ROOT/'cad/ThreeWay150_51mm_System.blend').exists()
    print('REUSED_VERIFIED_CAD_UNCHANGED',json.dumps(s),flush=True)
else:
    run('final_cad_build.log',args)
    run('final_print_readback.log',[sys.executable,'verify_print.py'])
    blender=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
    run('final_cad_render.log',[blender,'-b','-t','2','--python','render_cad.py'])
    assert (ROOT/'cad/airpath_checks.json').stat().st_mtime>=(ROOT/'cad/geometry_checks.json').stat().st_mtime
    run('final_native_blend.log',[blender,'-b','-t','1','--python','verify_native_blend.py'])
    assert (ROOT/'cad/native_reopen_checks.json').stat().st_mtime>=(ROOT/'cad/ThreeWay150_51mm_System.blend').stat().st_mtime
    (ROOT/'CAD_PREPARED_WAITING_CFD.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
    print('CAD_READY_AWAITING_FINAL_CFD',json.dumps(s),flush=True)
while not (ROOT/'CFD_VALIDATION_FINISHED.json').exists():time.sleep(5)
final=json.loads((ROOT/'final_selection.json').read_text())
assert all(final[k]==v for k,v in s.items()),'Final CFD geometry differs from prepared CAD'
run('final_report_package.log',[sys.executable,'finalize_delivery.py'])
base=ROOT.parent/'集風罩'/'三路接頭與150mm風刀_51mm軟管_20261114';dest=base;index=2
while dest.exists():dest=base.with_name(base.name+f'_v{index}');index+=1
dest.mkdir(parents=True)
pack=ROOT/'ThreeWay_51mm_150x16_PrintPack.zip'
with zipfile.ZipFile(pack) as z:
    assert z.testzip() is None
    for name in z.namelist():
        p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
    z.extractall(dest)
shutil.copyfile(pack,dest/pack.name);shutil.copyfile(ROOT/'package_checks.json',dest/'package_checks.json')
assert hashlib.sha256(pack.read_bytes()).digest()==hashlib.sha256((dest/pack.name).read_bytes()).digest()
acceptance=json.loads((ROOT/'design_acceptance.json').read_text(encoding='utf-8'))
(ROOT/'DELIVERY_COMPLETE.json').write_text(json.dumps(dict(delivery_directory=str(dest),zip=str(dest/pack.name),artifact_integrity_checks_passed=True,
    all_nozzle_mesh_sensitivity_targets_met=acceptance['all_nozzle_mesh_sensitivity_targets_met'],release_status=acceptance['release_status']),ensure_ascii=False,indent=2),encoding='utf-8')
print('DELIVERY_COMPLETE',str(dest),flush=True)
