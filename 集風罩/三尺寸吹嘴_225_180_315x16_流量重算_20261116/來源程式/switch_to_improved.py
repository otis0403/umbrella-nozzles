"""Close the owned screening solver after a native checkpoint, then release the revised study."""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
import ansys.fluent.core as fluent

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('owned_launcher_pid', type=int)
args = parser.parse_args()
marker = 'CASE_COMPLETE screen_w225_L220 '
while marker not in (ROOT/'screen_fluent.log').read_text(encoding='utf-8',errors='replace'):
    time.sleep(2)
for name in ['screen_w180_L140','screen_w225_L180','screen_w225_L220']:
    folder = ROOT/'cfd'/name
    assert all((folder/file).exists() and (folder/file).stat().st_size>0
               for file in ['results.json','solution.cas.h5','solution.dat.h5'])
private = Path(tempfile.gettempdir())/'umbrella_threewidth_20261116_private.json'
connection = json.loads(private.read_text())
session = fluent.connect_to_fluent(**connection,cleanup_on_exit=False,start_watchdog=False,start_transcript=False)
session.exit(timeout=20,wait=30)
# This PID is the launcher of the screening job started in this chat. The
# Fluent session has already closed; stopping the launcher prevents it from
# starting additional superseded profile comparisons.
subprocess.run(['taskkill','/PID',str(args.owned_launcher_pid),'/T','/F'],
               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
private.unlink(missing_ok=True)
record={'completed':['screen_w180_L140','screen_w225_L180','screen_w225_L220'],
        'owned_solver_closed':True,'remaining_screen_profiles_superseded':True,
        'reason':'short-profile separation established; continue revised smooth-widening profiles'}
(ROOT/'stage_finished.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('SCREEN_CHECKPOINTS_SAVED_OWNED_SESSION_CLOSED',flush=True)
