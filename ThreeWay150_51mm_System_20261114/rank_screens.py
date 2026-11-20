"""Screen shape uniformity, then estimate operating flow for ranking only."""
import json,time
import numpy as np
from scipy.optimize import root
from geometry import ROOT
from analyze import convergence,jet_metrics
from network import A46,RHO,loads

def main():
    while not (ROOT/'STAGE_20_COMPLETE.json').exists():time.sleep(3)
    convergence();base=json.loads((ROOT/'nozzle_pressure_curves.json').read_text());baseline=base['16']
    (ROOT/'nozzle_curves_L120_W150.json').write_text(json.dumps(base,indent=2),encoding='utf-8')
    ref=json.loads((ROOT/'cfd/adapter_H110_g16_100_120/results.json').read_text());q0=np.array(ref['branch_flow_m3_min']);kt=(400-np.array(ref['physical_port_total_pressure_Pa']))/q0.sum()**2
    conditions=loads(16,1,1.2);pipe=np.array([.5*RHO*(v['hose_K_referred_to_port']+v['joint_K_assumed'])/(60*A46)**2 for v in conditions])
    cases=[('jet_g16_L120_long_pipe',120,150),('jet_g16_L150_W150_screen',150,150),('jet_g16_L80_W150_screen',80,150),('jet_g16_L120_W170_screen',120,170)]
    rows=[]
    for name,length,shoulder in cases:
        p=ROOT/'cfd'/name;r=json.loads((p/'results.json').read_text());m=jet_metrics(name);q=r['nozzle_flow_m3_min'];expected=baseline['a_Pa_per_Q2']*q*q+baseline['b_Pa_per_Q']*q
        ratio=r['reports']['ptin']/expected;a=baseline['a_Pa_per_Q2']*ratio;b=baseline['b_Pa_per_Q']*ratio
        answer=root(lambda x:kt*x.sum()**2+(a+pipe)*x*x+b*x-400,q0);assert answer.success and min(answer.x)>0
        cv=max(m[f'{d}mm']['core_140mm_line_CV_pct'] for d in [30,50,80]);score=m['minimum_pressure_proxy_Pa']*(min(answer.x)/q)**2
        rows.append(dict(case=name,length_mm=length,shoulder_mm=shoulder,maximum_CV_pct=cv,uniformity_target_pass=cv<=10,
            reference_flow_m3_min=q,CFD_required_total_pressure_Pa=r['reports']['ptin'],estimated_system_branch_flow_m3_min=answer.x.tolist(),
            estimated_worst_patch_score_Pa=score,estimate_only_not_final_coupled_CFD=True))
    (ROOT/'nozzle_shape_screening.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('SCREEN_RANKING',json.dumps(rows),flush=True)
    candidates=[r for r in rows if r['uniformity_target_pass']]
    if not candidates:
        (ROOT/'NEED_PROFILE_REVIEW.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');return
    best=max(r['estimated_worst_patch_score_Pa'] for r in candidates);near=[r for r in candidates if r['estimated_worst_patch_score_Pa']>=.97*best]
    selected=min(near,key=lambda r:(r['length_mm'],r['shoulder_mm']));(ROOT/'selected_shape_work.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    L=selected['length_mm'];W=selected['shoulder_mm'];jobs=[]
    for q,warm in [(1.,'curve_g16_q1'),(2.5,'curve_g16_q2.5')]:
        name=f'curve_selected_q{q:g}'
        jobs.append(dict(kind='nozzle',name=name,gap=16,q=q,length=L,shoulder=W,batches=8,warm=warm))
    (ROOT/'plan_21.json').write_text(json.dumps(dict(jobs=jobs,final=False),indent=2),encoding='utf-8')
    print('SELECTED_SHAPE_FOR_COUPLED_VALIDATION',json.dumps(selected),flush=True)

if __name__=='__main__':main()
