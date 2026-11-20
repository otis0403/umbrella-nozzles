"""Run the revised profiles after the current owned Fluent session closes."""
import json
import os
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
print('WAITING_FOR_SCREEN_SESSION_TO_CLOSE', flush=True)
while not (ROOT/'stage_finished.json').exists():
    time.sleep(5)
plan = json.loads((ROOT/'stage_ramp.json').read_text())
plan['log'] = 'ramp_serial_fluent.log'
(ROOT/'stage_ramp_serial.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
os.environ['CFD_CORES'] = '4'
os.environ['CFD_SCHEME'] = 'SIMPLE'
sys.argv = [str(ROOT/'run_stage.py'), 'stage_ramp_serial.json']
runpy.run_path(str(ROOT/'run_stage.py'), run_name='__main__')
