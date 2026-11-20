"""Bounded selection and validation; all flow fields come from real Fluent jobs."""
import json,time,math,sys,subprocess
from pathlib import Path
import numpy as np
from scipy.optimize import root,nnls
from geometry import ROOT
from analyze import convergence,jet_metrics
from network import loads,A46,RHO

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):Path(p).write_text(json.dumps(v,indent=2),encoding='utf-8')

class Stages:
    def __init__(self,stage):self.stage=stage
    def wait(self,stage):
        while not (ROOT/f'STAGE_{stage}_COMPLETE.json').exists():time.sleep(3)
    def run(self,jobs,final=False):
        for j in jobs:j.setdefault('reuse_verified',True)
        stage=self.stage;write(ROOT/f'plan_{stage}.json',dict(jobs=jobs,final=final));self.wait(stage);self.stage+=1
        print('COORDINATOR_STAGE_DONE',stage,[j['name'] for j in jobs],flush=True)
    def ensure(self,jobs):
        for attempt in range(3):
            cv=convergence();failed=[j for j in jobs if j.get('kind') in ['nozzle','adapter'] and not j.get('action') and not cv.get(j['name'],{}).get('engineering_convergence_pass')]
            if not failed:return
            if attempt==2:raise RuntimeError('Convergence unresolved: '+str([j['name'] for j in failed]))
            adapters=[j['name'] for j in failed if j['kind']=='adapter']
            if adapters:
                # The main controller is idle after its stage marker. Continue
                # the native files without resetting calibrated porous loads.
                log=f'fluent_native_continuation_{time.time_ns()}.log'
                subprocess.run([sys.executable,'run_logged.py',log,'resume_adapter.py',*adapters],cwd=ROOT,check=True)
                print('NATIVE_ADAPTER_CONTINUATION_DONE',adapters,log,flush=True)
            retries=[]
            for j in failed:
                if j['kind']=='nozzle':retries.append(dict(kind='adapter',action='resume_nozzle',name=j['name'],batches=5,reuse_verified=False))
            if retries:self.run(retries)

def rank(cases):
    base=read(ROOT/'base_nozzle_pressure_curves.json')['16'];ref=read(ROOT/'cfd/adapter_H110_g16_100_120/results.json');q0=np.array(ref['branch_flow_m3_min'])
    km=(400-np.array(ref['physical_port_total_pressure_Pa']))/q0.sum()**2
    ld=loads(16,1.,1.2);pipe=np.array([.5*RHO*(v['hose_K_referred_to_port']+v['joint_K_assumed'])/(60*A46)**2 for v in ld]);rows=[]
    for job in cases:
        p=ROOT/'cfd'/job['name'];r=read(p/'results.json');m=jet_metrics(job['name']);q=r['nozzle_flow_m3_min']
        with np.load(p/'cell_fields.npz') as cells:
            inside=cells['SV_CENTROID'].reshape(-1,3)[:,2]<r['conditions']['height_mm']/1000
            reverse=inside&(cells['SV_W']<-.01)
            reverse_pct=100*float(cells['SV_VOLUME'][reverse].sum()/cells['SV_VOLUME'][inside].sum())
        ratio=r['reports']['ptin']/(base['a_Pa_per_Q2']*q*q+base['b_Pa_per_Q']*q);a=base['a_Pa_per_Q2']*ratio;b=base['b_Pa_per_Q']*ratio
        ans=root(lambda x:km*x.sum()**2+(a+pipe)*x*x+b*x-400,q0);assert ans.success and min(ans.x)>0
        maximum_cv=max(m[f'{d}mm']['core_140mm_line_CV_pct'] for d in [30,50,80]);score=m['minimum_pressure_proxy_Pa']*(min(ans.x)/q)**2
        rows.append(dict(case=job['name'],length_mm=job['length'],shoulder_mm=job.get('shoulder',150),plenum_mm=job.get('plenum'),
            maximum_CV_pct=maximum_cv,uniformity_target_pass=maximum_cv<=10,reference_flow_m3_min=q,CFD_required_total_pressure_Pa=r['reports']['ptin'],
            estimated_system_branch_flow_m3_min=ans.x.tolist(),estimated_worst_patch_score_Pa=score,estimate_only_not_final_coupled_CFD=True,
            ambient_open_verified=True,physical_nozzle_reverse_volume_pct=reverse_pct))
    write(ROOT/'nozzle_shape_screening.json',rows);return rows

def choose(rows):
    good=[r for r in rows if r['uniformity_target_pass']]
    if not good:
        return min(rows,key=lambda r:(r['maximum_CV_pct'],-r['estimated_worst_patch_score_Pa']))
    best=max(r['estimated_worst_patch_score_Pa'] for r in good)
    return min([r for r in good if r['estimated_worst_patch_score_Pa']>=.97*best],key=lambda r:(r['length_mm'],r['shoulder_mm']))

def nozzle_job(name,shape,q,external=False,fine=False,warm=None):
    return dict(kind='nozzle',name=name,gap=16,q=float(q),length=shape['length_mm'],shoulder=shape['shoulder_mm'],plenum=shape.get('plenum_mm'),
        external=external,fine=fine,batches=10 if fine else 9,warm=warm)

def main():
    basepath=ROOT/'base_nozzle_pressure_curves.json'
    base=read(basepath) if basepath.exists() else read(ROOT/'nozzle_pressure_curves.json')
    if not basepath.exists():write(basepath,base)
    after_adapters=len(sys.argv)>1 and sys.argv[1]=='after-adapters'
    if after_adapters:
        stages=Stages(int(sys.argv[2]));stages.wait(stages.stage-1);shape=read(ROOT/'selected_shape_work.json')
    elif len(sys.argv)>1:
        refinement_stage=int(sys.argv[1]);stages=Stages(refinement_stage+1);stages.wait(refinement_stage)
        screens=read(ROOT/'plan_40.json')['jobs']+read(ROOT/'plan_43.json')['jobs']+read(ROOT/f'plan_{refinement_stage}.json')['jobs']
        stages.ensure(screens);rows=rank(screens)
    else:
        stages=Stages(41);stages.wait(40);screens=read(ROOT/'plan_40.json')['jobs'];stages.ensure(screens);rows=rank(screens)
        if not any(r['uniformity_target_pass'] for r in rows):
            more=[dict(kind='nozzle',name=f'open_L120_W150_P{d}',gap=16,q=1.8170393240860634,length=120,shoulder=150,plenum=d,external=True,batches=9,warm='open_L120_W150') for d in [20,30]]
            stages.run(more);stages.ensure(more);screens+=more;rows=rank(screens)
    if not after_adapters:
        shape=choose(rows);write(ROOT/'selected_shape_work.json',shape)
    print('SHAPE_SELECTED',json.dumps(shape),flush=True)
    curves=[nozzle_job(f"curve_selected_P{shape.get('plenum_mm') or 0:g}_q{q:g}",shape,q,warm='curve_g16_q1' if q==1 else 'curve_g16_q2.5') for q in [1.,2.5]]
    if not after_adapters:stages.run(curves)
    stages.ensure(curves)
    points=[]
    for job in curves:
        r=read(ROOT/'cfd'/job['name']/'results.json');points.append([r['nozzle_flow_m3_min'],r['reports']['ptin']])
    a=np.array(points);coef,_=nnls(np.c_[a[:,0]**2,a[:,0]],a[:,1]);table=dict(base)
    table['16']=dict(a_Pa_per_Q2=float(coef[0]),b_Pa_per_Q=float(coef[1]),points=points,geometry_length_mm=shape['length_mm'],geometry_shoulder_mm=shape['shoulder_mm'],
        geometry_plenum_mm=shape.get('plenum_mm'),source_cases=[j['name'] for j in curves],max_fit_error_pct=float(max(abs((coef[0]*a[:,0]**2+coef[1]*a[:,0])/a[:,1]-1))*100))
    write(ROOT/'nozzle_pressure_curves.json',table)
    height=110.;neck=46.;jobs=[];pipe_cases={};previous='adapter_H110_g16_100_120'
    for key,c,s in [('100_120',1.,1.2),('60_80',.6,.8),('50_70',.5,.7)]:
        name='final_adapter_'+key;pipe_cases[key]=name
        jobs.append(dict(kind='adapter',name=name,height=height,neck=neck,gap=16,center=c-.05,side=s-.05,physical_center=c,physical_side=s,batches=9,warm=previous));previous=name
    specifications=[('final_pressure200',dict(pressure=200)),('final_friction_low',dict(friction=.02)),('final_friction_high',dict(friction=.08)),
        ('final_short_pipe_more_bends',dict(center=.45,side=.65,physical_center=.5,physical_side=.7,bend=1.)),
        ('final_one_side_extra_bend',dict(bend=[1.,.5,.5])),('reference_final_old_layout',dict(reference=True,height=155.,batches=11))]
    for name,extra in specifications:
        j=dict(kind='adapter',name=name,height=height,neck=neck,gap=16,center=.95,side=1.15,physical_center=1.,physical_side=1.2,batches=9,warm=pipe_cases['100_120']);j.update(extra);jobs.append(j)
    if not after_adapters:stages.run(jobs)
    stages.ensure(jobs)
    for name in pipe_cases.values():
        r=read(ROOT/'cfd'/name/'results.json');assert r['network_load_consistency_pass']
    jets=[];jet_cases={};previous=shape['case']
    for key in ['100_120','60_80','50_70']:
        r=read(ROOT/'cfd'/pipe_cases[key]/'results.json');name='final_jet_'+key;jet_cases[key]=name
        jets.append(nozzle_job(name,shape,min(r['branch_flow_m3_min']),external=True,warm=previous));previous=name
    stages.run(jets);stages.ensure(jets)
    # Verify the external free-jet pressure requirement agrees with the network
    # load curve before using it as a system prediction.
    errors=[]
    for j in jets:
        r=read(ROOT/'cfd'/j['name']/'results.json');q=r['nozzle_flow_m3_min'];expected=coef[0]*q*q+coef[1]*q
        errors.append(100*(r['reports']['ptin']/expected-1))
    write(ROOT/'external_curve_consistency.json',dict(error_pct=errors,pass_under_3pct=bool(max(abs(np.array(errors)))<3)))
    assert max(abs(np.array(errors)))<3,('External nozzle load curve mismatch',errors)
    fine_adapter=dict(kind='adapter',name='final_adapter_fine',height=height,neck=neck,gap=16,center=.95,side=1.15,physical_center=1.,physical_side=1.2,fine=True,batches=10,warm=pipe_cases['100_120'])
    stages.run([fine_adapter]);stages.ensure([fine_adapter]);r=read(ROOT/'cfd/final_adapter_fine/results.json');assert r['network_load_consistency_pass']
    fine_jet=nozzle_job('final_jet_fine',shape,min(r['branch_flow_m3_min']),external=True,fine=True,warm=jet_cases['100_120'])
    stages.run([fine_jet]);stages.ensure([fine_jet])
    all_cases=[j['name'] for j in curves+jobs+jets+[fine_adapter,fine_jet]]
    metrics=[jet_metrics(n) for n in list(jet_cases.values())+[fine_jet['name']]]
    max_cv=max(m[f'{d}mm']['core_140mm_line_CV_pct'] for m in metrics for d in [30,50,80])
    selection=dict(date='2026-11-14',adapter_height_mm=height,neck_mm=neck,nozzle_gap_mm=16,nozzle_span_mm=150,nozzle_length_mm=shape['length_mm'],nozzle_shoulder_mm=shape['shoulder_mm'],
        nozzle_plenum_mm=shape.get('plenum_mm'),pipe_cases=pipe_cases,jet_cases=jet_cases,fine_adapter_case=fine_adapter['name'],fine_jet_case=fine_jet['name'],
        reference_case='reference_final_old_layout',sensitivity_cases=[n for n,_ in specifications if not n.startswith('reference')],validation_cases=all_cases,
        nozzle_uniformity_target_met=max_cv<=10,maximum_nozzle_CV_pct=max_cv,actual_fan_curve_used=False,hypothetical_reference_total_pressure_Pa=400,
        physical_testing_complete=False,physical_pipe_lengths_include_25mm_insertion_each_end=True)
    write(ROOT/'final_selection.json',selection)
    stages.run([dict(kind='verify',name='verify_selected_native_cases',cases=all_cases)],final=True)
    while 'OWNED_SOLVER_EXIT_COMPLETED' not in (ROOT/'fluent_final.log').read_text(encoding='utf-8',errors='replace'):time.sleep(2)
    write(ROOT/'CFD_VALIDATION_FINISHED.json',dict(selection=selection,owned_solver_exit_confirmed=True))
    print('CFD_ALL_SELECTED_CASES_VALIDATED',json.dumps(selection),flush=True)

if __name__=='__main__':main()
