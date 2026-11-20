"""New 12/14/8 heads and matched 16/16/8 reference, real serial Fluent runs."""
import json
import os
import subprocess
import sys
import time
import traceback
import numpy as np
from scipy.optimize import nnls
from design import ROOT,write_json

PRIOR=ROOT.parent/'Outer315_NarrowGap_ANSYS_20261117'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def state(phase,**extra):
    write_json(ROOT/'pipeline_state.json',{'phase':phase,'time':time.time(),**extra})
    print('STUDY_STATE',phase,extra,flush=True)
def execute(script,args,log,scheme='SIMPLE'):
    state(script,args=args,log=log)
    env=os.environ.copy();env['CFD_CORES']='4';env['CFD_SCHEME']=scheme
    with (ROOT/log).open('w',encoding='utf-8') as stream:
        result=subprocess.run([sys.executable,'-B','-u',str(ROOT/script),*args],cwd=ROOT,env=env,
                              stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(f'{script} failed; inspect {log}')
try:
    execute('run_stage.py',['stage_head_curves.json'],'head_curves_fluent.log')
    curves=read(ROOT/'baseline_pressure_curves.json')
    sources={225:(12,['inner225_g12_q2p16','inner225_g12_q3p2']),180:(14,['center180_g14_q1p728','center180_g14_q3p2'])}
    for width,(gap,names) in sources.items():
        points=[]
        for name in names:
            r=read(ROOT/'cfd'/name/'results.json');h=read(ROOT/'cfd'/name/'history.json')
            pressure=np.array([row['ptin'] for row in h[-8:]])
            points.append({'case':name,'Q_m3_min':r['nozzle_flow_m3_min'],'required_total_Pa':r['reports']['ptin'],
                           'late_iteration_pressure_range_pct':float(np.ptp(pressure)/pressure.mean()*100)})
        q=np.array([p['Q_m3_min'] for p in points]);p=np.array([p['required_total_Pa'] for p in points])
        ab,_=nnls(np.c_[q*q,q]/p[:,None],np.ones(len(q)))
        error=float(max(abs((ab[0]*q*q+ab[1]*q)/p-1))*100)
        assert error<2,'Two-point curve needs additional samples'
        curves[str(width)]={'a':float(ab[0]),'b':float(ab[1]),'gap_mm':gap,'points':points,
                            'fit':'P_total=aQ^2+bQ; Pa with Q in m3/min','maximum_fit_error_pct':error,
                            'includes_feed_elbow_R90':True,'inlet_ID_mm':51,'actual_fan_operating_point_verified':False,
                            'source_root':str(ROOT)}
    curves['315']['source_root']=str(PRIOR)
    write_json(ROOT/'selected_pressure_curves.json',curves)
    write_json(ROOT/'selection.json',{
        'inner':{'width_mm':225,'gap_mm':12,'length_mm':220,'height_mm':288,'case':'inner225_g12_q2p16','source_root':str(ROOT)},
        'center':{'width_mm':180,'gap_mm':14,'length_mm':180,'height_mm':248,'case':'center180_g14_q1p728','source_root':str(ROOT)},
        'outer':{'width_mm':315,'gap_mm':8,'length_mm':320,'height_mm':388,'case':'candidate_g8_q3','source_root':str(PRIOR),'guided':True,'guide_count':2},
        'hose_ID_mm':51,'printer_capacity_deferred':True,'user_authorized_new_ANSYS':True})
    execute('solve_network.py',['stage_network.json'],'network_fluent.log','Coupled')
    for length in [60,50]:
        candidate=read(ROOT/'cfd'/f'candidate_12_14_8_hose{length}'/'results.json')
        for i,width in enumerate([225,180,315]):
            qs=[p['Q_m3_min'] for p in curves[str(width)]['points']]
            assert min(qs)-.005<=candidate['branch_flow_m3_min'][i]<=max(qs)+.005,('Flow curve interpolation range exceeded',width)
    execute('analyze_cases.py',[],'analysis_final.log')
    execute('verify_native_cfd.py',[],'native_readback.log','Coupled')
    state('CFD_and_native_readback_complete_models_report_pending')
except Exception as error:
    state('error',error=str(error),traceback=traceback.format_exc());raise
