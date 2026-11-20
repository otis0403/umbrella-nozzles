"""Continue native adapter fields while preserving calibrated load boundaries."""
import json,time,sys
import numpy as np
from scipy.spatial import cKDTree
from geometry import ROOT,port,branch_grid,port_grid,reference_port,reference_branch_grid,reference_port_grid
from legacy_study import connect,reports,surface
from network import A46,RHO
from convergence_control import ready


def resume(s,job):
    name=job['name'];p=ROOT/'cfd'/name
    r=json.loads((p/'results.json').read_text());history=json.loads((p/'history.json').read_text())
    s.settings.file.read_case_data(file_name=str(p/'solution.cas.h5'))
    before={f'load_{k}':s.settings.setup.boundary_conditions.porous_jump[f'load_{k}'].porous_jump.get_state() for k in range(3)}
    control_group=s.settings.solution.controls
    active_controls=control_group.get_state()
    if 'under_relaxation' in active_controls:
        controls=control_group.under_relaxation
        relaxation_menu='under_relaxation'
    else:
        controls=control_group.pseudo_time_explicit_relaxation_factor.global_dt_pseudo_relax
        relaxation_menu='pseudo_time_explicit_relaxation_factor.global_dt_pseudo_relax'
    relaxation_before=controls.get_state()
    if r.get('continued_native_solution'):
        # Dampen iterative oscillations on a subsequent continuation. Physics,
        # second-order schemes, convergence limits and load BCs stay fixed.
        for equation,limit in [('pressure',.2),('mom',.5),('k',.5),('omega',.5)]:
            if equation in relaxation_before:controls[equation]=min(float(relaxation_before[equation]),limit)
    relaxation_after=controls.get_state()
    print('NATIVE_CONTINUATION_RELAXATION',name,json.dumps(dict(menu=relaxation_menu,before=relaxation_before,after=relaxation_after)),flush=True)
    pseudo_before=pseudo_after=None
    if r.get('continued_native_solution') and relaxation_menu!='under_relaxation':
        pseudo=s.settings.solution.run_calculation.pseudo_time_settings.time_step_method
        pseudo_before=pseudo.get_state()
        pseudo.time_step_size_scale_factor=min(float(pseudo.time_step_size_scale_factor()),.1)
        pseudo_after=pseudo.get_state()
        print('PSEUDO_TIME_STABILITY_CONTROLS',name,json.dumps(dict(before=pseudo_before,after=pseudo_after)),flush=True)
    names=['pin','ptin','min','m0','m1','m2'];start=time.time();elapsed=history[-1]['elapsed_s'];passing=0
    for step in range(job.get('batches',10)):
        s.settings.solution.run_calculation.iterate(iter_count=40)
        history.append(dict(batch=len(history)+1,elapsed_s=elapsed+time.time()-start,**reports(s,names)))
        (p/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
        print('CASE_PROGRESS',name,json.dumps(history[-1]),flush=True)
        passing=passing+1 if ready(history,['m0','m1','m2']) else 0
        if passing>=2:break
    cells={v:s.fields.solution_variable_data.get_data(variable_name=v,zone_names=['fluid'])['fluid'] for v in ['SV_CENTROID','SV_VOLUME','SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']}
    assert all(np.isfinite(v).all() for v in cells.values()) and cells['SV_VOLUME'].min()>0
    xyz=cells['SV_CENTROID'].reshape(-1,3)*1000;vel=np.c_[cells['SV_U'],cells['SV_V'],cells['SV_W']]
    total_pressure=cells['SV_P']+.6*(vel*vel).sum(1);last=history[-1];q=np.array([-last[f'm{k}']/RHO*60 for k in range(3)])
    assert q.min()>0
    height=r['conditions']['height'];neck=r['conditions']['neck'];reference=r['conditions'].get('reference',False)
    port_pressures=[];virtual=np.zeros(len(xyz),bool);paths=[];tangents=[]
    for k in range(3):
        E,D=reference_port(k) if reference else port(k,height)
        axial=(xyz-E)@D;radial=np.linalg.norm(xyz-E-axial[:,None]*D,axis=1)
        mask=(axial>22.5)&(axial<24.9)&(radial<23.001)
        weight=cells['SV_VOLUME'][mask]*np.maximum(vel[mask]@D,0)
        port_pressures.append(float(np.average(total_pressure[mask],weights=weight)));virtual|=(axial>25)&(radial<23.001)
        if reference:
            points=np.array([reference_branch_grid(k,t,2,2)[1,1] for t in np.linspace(0,1,61)]+[reference_port_grid(k,d,2,2)[1,1] for d in np.linspace(.5,25,26)])
        else:
            points=np.array([branch_grid(k,t,height,2,2,neck=neck)[1,1] for t in np.linspace(0,1,61)]+[port_grid(k,d,height,2,2)[1,1] for d in np.linspace(.5,25,26)])
        tangent=np.gradient(points,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None];paths.extend(points);tangents.extend(tangent)
    curve=json.loads((ROOT/'nozzle_pressure_curves.json').read_text())['16'];dynamic=.5*RHO*(q/60/A46)**2
    target=curve['a_Pa_per_Q2']*q*q+curve['b_Pa_per_Q']*q+dynamic*np.array([v['hose_K_referred_to_port']+v['joint_K_assumed'] for v in r['equivalent_loads']])
    errors=100*(np.array(port_pressures)/target-1);assert max(abs(errors))<2,errors
    _,nearest=cKDTree(paths).query(xyz);direction=np.array(tangents)[nearest];direction[xyz[:,2]<(40 if reference else 30)]=[0,0,1]
    inside=~virtual;local_negative=inside&((vel*direction).sum(1)<-.01);negative_z=inside&(cells['SV_W']<-.01)
    r.update(reports=last,branch_flow_m3_min=q.tolist(),total_flow_m3_min=float(q.sum()),branch_share_pct=(q/q.sum()*100).tolist(),
        balance_error_pct=float(max(abs(q/q.mean()-1))*100),physical_port_total_pressure_Pa=port_pressures,
        adapter_total_pressure_loss_Pa=last['ptin']-float(np.average(port_pressures,weights=q)),
        mass_imbalance_pct=100*abs(last['min']+sum(last[f'm{k}'] for k in range(3)))/abs(last['min']),
        last_flow_change_pct=max(100*abs(last[f'm{k}']/history[-2][f'm{k}']-1) for k in range(3)),
        last_pressure_change_pct=100*abs(last['pin']/history[-2]['pin']-1),
        internal_negative_global_Z_volume_pct=100*float(cells['SV_VOLUME'][negative_z].sum()/cells['SV_VOLUME'][inside].sum()),
        internal_negative_local_flow_volume_pct=100*float(cells['SV_VOLUME'][local_negative].sum()/cells['SV_VOLUME'][inside].sum()),
        network_load_consistency_pass=True,continued_native_solution=True)
    r['network_calibration'].append(dict(iteration='native_continuation_no_boundary_change',Q_m3_min=q.tolist(),target_total_pressure_Pa=target.tolist(),actual_total_pressure_Pa=port_pressures,error_pct=errors.tolist()))
    after={f'load_{k}':s.settings.setup.boundary_conditions.porous_jump[f'load_{k}'].porous_jump.get_state() for k in range(3)}
    assert before==after,'Continuation changed calibrated boundary conditions'
    np.savez_compressed(p/'cell_fields.npz',**cells);surface(s,'adapter_cut',p/'cut_fields.npz')
    (p/'results.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    (p/'continuation_boundary_integrity.json').write_text(json.dumps(dict(porous_jump_boundaries_unchanged=True,before=before,after=after,
        relaxation_menu=relaxation_menu,relaxation_before=relaxation_before,relaxation_after=relaxation_after,pseudo_time_before=pseudo_before,pseudo_time_after=pseudo_after,
        second_order_discretization_preserved=True),indent=2),encoding='utf-8')
    s.settings.file.write_case_data(file_name=str(p/'solution.cas.h5'))
    print('CASE_COMPLETE',name,json.dumps(r),flush=True)


if __name__=='__main__':
    solver=connect(launch=False,cleanup=False)
    for case in sys.argv[1:]:resume(solver,dict(name=case,batches=12))
    # Restore the original controller's iterative defaults for subsequent NEW
    # meshes, after saving each continued case with its actual controls.
    active=solver.settings.solution.controls.get_state()
    if 'global_dt_pseudo_relax' in active.get('pseudo_time_explicit_relaxation_factor',{}):
        solver.settings.solution.run_calculation.pseudo_time_settings.time_step_method.time_step_size_scale_factor=1.
        menu=solver.settings.solution.controls.pseudo_time_explicit_relaxation_factor.global_dt_pseudo_relax
        for equation in ['k','omega']:menu[equation]=.75
        print('CONTROLLER_DEFAULT_ITERATION_CONTROLS_RESTORED',flush=True)
    # This client does not own the solver; the main controller closes it.
