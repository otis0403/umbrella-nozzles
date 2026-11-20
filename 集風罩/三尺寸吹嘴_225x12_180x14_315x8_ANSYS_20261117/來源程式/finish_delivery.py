import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
while True:
    try:state=json.loads((ROOT/'pipeline_state.json').read_text())
    except (OSError,json.JSONDecodeError):time.sleep(5);continue
    if state['phase']=='error':raise RuntimeError(state['error'])
    if state['phase']=='CFD_and_native_readback_complete_models_report_pending':break
    time.sleep(5)
blender=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
for script,use_blender in [('build_selected_models.py',False),('build_native_models.py',True),('draw_dimensions.py',False),('package_delivery.py',False)]:
    command=[blender,'--background','--python',str(ROOT/script)] if use_blender else [sys.executable,'-B','-u',str(ROOT/script)]
    with (ROOT/(script.removesuffix('.py')+'.log')).open('w',encoding='utf-8') as stream:
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(f'{script} failed')
    if use_blender:
        check=json.loads((ROOT/'cad/native_geometry_checks.json').read_text());assert check['native_reopened'] and len(check['records'])==3
    print('FINALIZATION_COMPLETE',script,flush=True)
print('PACKAGE_READY_FOR_VISUAL_REVIEW',flush=True)
