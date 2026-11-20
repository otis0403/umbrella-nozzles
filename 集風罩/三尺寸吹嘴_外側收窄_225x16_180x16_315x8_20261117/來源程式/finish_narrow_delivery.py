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
    if state['phase']=='new_CFD_and_native_readback_complete_models_report_pending':break
    time.sleep(5)
blender=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
jobs=[('build_selected_models.py',False),('build_native_models.py',True),('render_guided_cutaway.py',True),
      ('draw_dimensions.py',False),('package_narrow_delivery.py',False)]
for script,use_blender in jobs:
    command=[blender,'--background','--python',str(ROOT/script)] if use_blender else [sys.executable,'-B','-u',str(ROOT/script)]
    with (ROOT/(script.removesuffix('.py')+'.log')).open('w',encoding='utf-8') as stream:
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(f'{script} failed')
    if script=='build_native_models.py':
        record=json.loads((ROOT/'cad/native_geometry_checks.json').read_text())
        assert record['native_reopened'] and len(record['records'])==3
    print('FINALIZATION_STEP_COMPLETE',script,flush=True)
print('NARROW_PACKAGE_READY_FOR_VISUAL_REVIEW',flush=True)
