"""Continue an existing native solution; never substitute a scaled field for a solve."""
import json,time
import numpy as np
from geometry import ROOT
from legacy_study import reports,surface

def resume(s,job):
    name=job['name'];p=ROOT/'cfd'/name;r=json.loads((p/'results.json').read_text());history=json.loads((p/'history.json').read_text())
    s.settings.file.read_case_data(file_name=str(p/'solution.cas.h5'))
    if job.get('flow_scheme'):
        methods=s.settings.solution.methods
        before=methods.get_state();methods.p_v_coupling.flow_scheme=job['flow_scheme']
        methods.pseudo_time_method.formulation.segregated_solver='off'
        controls=s.settings.solution.controls.under_relaxation
        state=controls.get_state()
        for equation,limit in [('pressure',.3),('mom',.5),('k',.5),('omega',.5)]:
            if equation in state:controls[equation]=min(float(state[equation]),limit)
        methods.high_order_term_relaxation.enable=True
        methods.high_order_term_relaxation.relaxation_factor=.25
        methods.high_order_term_relaxation.select_variables='all-variables'
        after=methods.get_state();assert before['spatial_discretization']==after['spatial_discretization']
        (p/'solver_method_adjustment.json').write_text(json.dumps(dict(before=before,after=after,
            second_order_schemes_and_physical_boundaries_unchanged=True,controls=s.settings.solution.controls.get_state()),indent=2),encoding='utf-8')
    names=['pin','ptin','ptout','min','mout']+(['mambient'] if r['conditions']['external_free_jet'] else [])
    start=time.time();base_elapsed=history[-1]['elapsed_s'];passing=0
    for step in range(job.get('batches',5)):
        s.settings.solution.run_calculation.iterate(iter_count=40)
        row=dict(batch=len(history)+1,elapsed_s=base_elapsed+time.time()-start,**reports(s,names));history.append(row)
        print('CASE_PROGRESS',name,json.dumps(row),flush=True)
        if job.get('adaptive'):
            from convergence_control import ready
            passing=passing+1 if ready(history,['mout','mambient']) else 0
            if passing>=2:break
    data=surface(s,'outlet',p/'outlet_fields.npz')
    if r['conditions']['external_free_jet']:
        for n in ['slot','long_cut','short_cut','plane_30mm','plane_50mm','plane_80mm']:surface(s,n,p/(n+'_fields.npz'))
    else:surface(s,'long_cut',p/'long_cut_fields.npz')
    cells={v:s.fields.solution_variable_data.get_data(variable_name=v,zone_names=['fluid'])['fluid'] for v in ['SV_CENTROID','SV_VOLUME','SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']}
    np.savez_compressed(p/'cell_fields.npz',**cells);a=data['areas'];u=data['z-velocity'];mean=float(np.average(u,weights=a));last=history[-1]
    r.update(name=name,reports=last,required_static_pressure_Pa=last['pin'],pressure_loss_to_domain_outlet_Pa=last['ptin']-last['ptout'],nozzle_flow_m3_min=last['min']/1.2*60,
        mass_imbalance_pct=100*abs(last['min']+last['mout']+last.get('mambient',0))/abs(last['min']),outlet_mean_axial_velocity_m_s=mean,
        outlet_full_area_CV=float(np.sqrt(np.average((u-mean)**2,weights=a))/mean),last_pressure_change_pct=100*abs(last['pin']/history[-2]['pin']-1),
        negative_uz_volume_fraction=float(cells['SV_VOLUME'][cells['SV_W']<-.01].sum()/cells['SV_VOLUME'].sum()),min_uz_m_s=float(cells['SV_W'].min()),continued_native_solution=True)
    (p/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8');(p/'results.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    s.settings.file.write_case_data(file_name=str(p/'solution.cas.h5'));print('CASE_COMPLETE',name,json.dumps(r),flush=True)
