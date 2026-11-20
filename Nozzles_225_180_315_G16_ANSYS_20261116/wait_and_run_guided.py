import os
import runpy
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
print('WAITING_FOR_PRESSURE_CURVE_STAGE_TO_CLOSE',flush=True)
while not (ROOT/'stage_curves_finished.json').exists():
    time.sleep(5)
os.environ['CFD_CORES']='4'
os.environ['CFD_SCHEME']='Coupled'
sys.argv=[str(ROOT/'run_stage.py'),'stage_guided315.json']
runpy.run_path(str(ROOT/'run_stage.py'),run_name='__main__')
