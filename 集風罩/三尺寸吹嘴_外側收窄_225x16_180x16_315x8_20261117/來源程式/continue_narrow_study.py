"""Only the outer gap changes; keep the existing hose and other heads."""
import json
import os
import subprocess
import sys
import time
import traceback
import numpy as np
from scipy.optimize import nnls
from scipy.optimize import brentq
from design import ROOT,write_json

BASE=ROOT.parent/'Nozzles_225_180_315_G16_ANSYS_20261116'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def state(phase,**extra):
    write_json(ROOT/'pipeline_state.json',{'phase':phase,'time':time.time(),**extra})
    print('NARROW_STATE',phase,extra,flush=True)
def execute(script,args,log,scheme='SIMPLE'):
    state(script,args=args,log=log)
    env=os.environ.copy();env['CFD_CORES']='4';env['CFD_SCHEME']=scheme
    with (ROOT/log).open('w',encoding='utf-8') as stream:
        result=subprocess.run([sys.executable,'-B','-u',str(ROOT/script),*args],cwd=ROOT,env=env,
                              stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(f'{script} failed; inspect {log}')

try:
    state('waiting_for_baseline_native_solver_to_close')
    while read(BASE/'pipeline_state.json')['phase']!='raw_CFD_and_independent_native_readback_complete_report_pending':time.sleep(5)
    execute('run_stage.py',['stage_candidates.json'],'candidate_fluent.log')
    execute('analyze_cases.py',[],'candidate_analysis.log')
    baseline=read(BASE/'cfd/network_Ps460_hose60/results.json')
    available=baseline['physical_port_total_pressure_Pa'][2]
    baseline_curve=read(ROOT/'baseline_pressure_curves.json')['315']
    candidate_rows=[]
    from solve_network import downstream_pressure
    for gap in [10,8]:
        case=f'candidate_g{gap}_q3'
        result=read(ROOT/'cfd'/case/'results.json');metrics=read(ROOT/'cfd'/case/'profile_metrics.json')
        q=result['nozzle_flow_m3_min'];b=baseline_curve['b']
        a=(result['reports']['ptin']-b*q)/(q*q)
        trial=read(ROOT/'baseline_pressure_curves.json');trial['315'].update(a=a,b=b,gap_mm=gap)
        estimate=brentq(lambda x:downstream_pressure(np.array([x,x,x]),trial,[.6]*3,.04,.5)[2]-available,.1,6)
        candidate_rows.append({'gap_mm':gap,'case':case,'estimated_Q_at_baseline_port_Pt':estimate,
                               'estimated_area_mean_velocity_m_s':estimate/60/(315*gap*1e-6),
                               'ranking_uses_one_point_curve_and_baseline_linear_term':True,**metrics})
    acceptable=[row for row in candidate_rows if row['core_line_CV_pct']<35 and row['body_reverse_volume_pct']<15]
    assert acceptable,'Candidate flow fields need engineering review'
    chosen=max(acceptable,key=lambda row:row['estimated_area_mean_velocity_m_s'])
    gap=int(chosen['gap_mm']);primary=chosen['case']
    write_json(ROOT/'candidate_review.json',{'candidates':candidate_rows,'chosen_gap_mm':gap,
                                           'ranking_is_preliminary_pending_loaded_network':True})
    low={'name':f'selected_g{gap}_q2','width':315,'length':320,'gap':gap,'profile_kind':'ramp',
         'guided':True,'q':2,'warm':primary,'batches':25}
    write_json(ROOT/'stage_selected_curve.json',{'log':'selected_curve_fluent.log','jobs':[low]})
    execute('run_stage.py',['stage_selected_curve.json'],'selected_curve_fluent.log')
    curves=read(ROOT/'baseline_pressure_curves.json')
    points=[]
    for case in [low['name'],primary]:
        result=read(ROOT/'cfd'/case/'results.json');hist=read(ROOT/'cfd'/case/'history.json')
        pressure=np.array([r['ptin'] for r in hist[-8:]])
        points.append({'case':case,'Q_m3_min':result['nozzle_flow_m3_min'],'required_total_Pa':result['reports']['ptin'],
                       'late_iteration_pressure_range_pct':float(np.ptp(pressure)/pressure.mean()*100)})
    q=np.array([p['Q_m3_min'] for p in points]);p=np.array([p['required_total_Pa'] for p in points])
    coefficients,_=nnls(np.c_[q*q,q]/p[:,None],np.ones(len(q)))
    curves['315']={'a':float(coefficients[0]),'b':float(coefficients[1]),'gap_mm':gap,
                   'fit':'P_total = a Q^2 + b Q; Pa and m3/min','points':points,
                   'maximum_fit_error_pct':float(max(abs((coefficients[0]*q*q+coefficients[1]*q)/p-1))*100),
                   'includes_feed_elbow_R90':True,'inlet_ID_mm':51,'actual_fan_operating_point_verified':False}
    for width in ['225','180']:curves[width]['source_root']=str(BASE)
    write_json(ROOT/'selected_pressure_curves.json',curves)
    write_json(ROOT/'selection.json',{
        'inner':{'width_mm':225,'gap_mm':16,'length_mm':220,'height_mm':288,'case':'ramp_w225_L220','source_root':str(BASE)},
        'center':{'width_mm':180,'gap_mm':16,'length_mm':180,'height_mm':248,'case':'ramp_w180_L180','source_root':str(BASE)},
        'outer':{'width_mm':315,'gap_mm':gap,'length_mm':320,'height_mm':388,'case':primary,'source_root':str(ROOT),'guided':True,'guide_count':2},
        'printer_capacity_deferred':True,'hose_ID_mm':51,'outer_gap_reduction_authorized':True})
    execute('solve_network.py',['stage_network.json'],'network_fluent.log','Coupled')
    for case in ['network_narrow_Ps460_hose60','network_narrow_Ps460_hose50']:
        network=read(ROOT/'cfd'/case/'results.json')
        assert min(q)-.005<=network['branch_flow_m3_min'][2]<=max(q)+.005,'Add a bracketing outer flow point before using the fitted curve'
        assert network['slot_area_mean_velocity_m_s'][2]>baseline['slot_area_mean_velocity_m_s'][2],'Selected gap did not increase loaded outer speed'
    execute('analyze_cases.py',[],'final_analysis.log')
    execute('verify_native_cfd.py',[],'native_readback.log','Coupled')
    state('new_CFD_and_native_readback_complete_models_report_pending')
except Exception as error:
    state('error',error=str(error),traceback=traceback.format_exc());raise
