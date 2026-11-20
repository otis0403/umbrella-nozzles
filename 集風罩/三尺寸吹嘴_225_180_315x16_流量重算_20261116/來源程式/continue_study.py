"""Serial continuation of the requested flow study, with reviewable checkpoints."""
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def state(phase,**data):
    record={'phase':phase,'updated_unix_time':time.time(),**data}
    (ROOT/'pipeline_state.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('PIPELINE_STATE',json.dumps(record),flush=True)


def execute(script,arguments,log,scheme='SIMPLE'):
    state(script,arguments=arguments,log=log)
    env=os.environ.copy()
    env['CFD_CORES']='4'
    env['CFD_SCHEME']=scheme
    with (ROOT/log).open('w',encoding='utf-8') as stream:
        result=subprocess.run([sys.executable,'-B','-u',str(ROOT/script),*arguments],cwd=ROOT,env=env,
                              stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f'{script} failed; see {log}')


try:
    state('waiting_for_guided_315_comparison')
    while not (ROOT/'stage_guided315_finished.json').exists():
        time.sleep(5)
    finished=json.loads((ROOT/'stage_guided315_finished.json').read_text())
    assert len(finished['completed'])==3,'Guided 315 mm stage is incomplete'
    execute('analyze_cases.py',[],'analysis_guided_comparison.log')
    guided=json.loads((ROOT/'cfd/guide_w315_L320/profile_metrics.json').read_text())
    plain=json.loads((ROOT/'cfd/ramp_w315_L320/profile_metrics.json').read_text())
    assert guided['core_line_CV_pct']<plain['core_line_CV_pct'],'Guide geometry needs further engineering review'
    (ROOT/'refine315.hold').unlink(missing_ok=True)
    (ROOT/'use_guided315.flag').write_text('Guided 315 mm prototype selected after flow comparison',encoding='utf-8')
    execute('run_stage.py',['stage_high_flow.json'],'high_flow_fluent.log')
    execute('fit_curves.py',[],'curve_fit.log')
    execute('solve_network.py',['stage_network.json'],'network_fluent.log','Coupled')
    # The requested prototype needs head pressure/distribution and a loaded
    # three-way flow calculation. Far-field drying and transient validation
    # remain explicitly unverified, per the user's prototype/report preference.
    execute('analyze_cases.py',[],'analysis_final.log')
    execute('verify_native_cfd.py',[],'native_cfd_readback.log','Coupled')
    state('raw_CFD_and_independent_native_readback_complete_report_pending')
except Exception as error:
    state('error',error=str(error),traceback=traceback.format_exc())
    raise
