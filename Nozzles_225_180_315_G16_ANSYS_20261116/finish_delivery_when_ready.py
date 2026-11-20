"""Wait for the owned serial solver workflow, then build the reviewed package."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
while True:
    try:
        state=json.loads((ROOT/'pipeline_state.json').read_text())
    except (OSError,json.JSONDecodeError):
        time.sleep(5);continue
    if state['phase']=='error':
        raise RuntimeError(state['error'])
    if state['phase']=='raw_CFD_and_independent_native_readback_complete_report_pending':break
    time.sleep(5)
for script in ['package_delivery.py']:
    result=subprocess.run([sys.executable,'-B','-u',str(ROOT/script)],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(f'{script} failed')
print('FINAL_PACKAGE_READY_FOR_VISUAL_AND_FLOW_REVIEW',flush=True)
