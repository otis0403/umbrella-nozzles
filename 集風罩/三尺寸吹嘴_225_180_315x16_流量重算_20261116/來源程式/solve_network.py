"""Fluent three-way flow split with independently calculated downstream loads."""
import argparse
import json
import os
import time
import hashlib
import shutil
import numpy as np

from design import ROOT, MAPPING, write_json
from adapter_mesh import build
from cfd_solver import connect, reports, surface, PRIVATE

RHO = 1.2
A46 = np.pi*.046**2/4
A51 = np.pi*.051**2/4


def downstream_pressure(q, curves, lengths, friction, bend):
    result = []
    for k in range(3):
        curve = curves[str(MAPPING[k])]
        nozzle = curve['a']*q[k]**2 + curve['b']*q[k]
        hose = .5*RHO*(q[k]/60/A51)**2*(friction*max(0,lengths[k]-.05)/.051 + bend)
        joint = .5*RHO*(q[k]/60/A46)**2*.15
        result.append(nozzle+hose+joint)
    return np.asarray(result)


def run(session, job, curves):
    name = job['name']
    folder = ROOT/'cfd'/name
    template=ROOT/'cfd/adapter_network_template'
    if not job.get('fine',False) and (template/'template_integrity.json').exists():
        cached=json.loads((template/'template_integrity.json').read_text())
        assert cached['mesh_sha256']==hashlib.sha256((template/'nozzle.msh').read_bytes()).hexdigest()
        assert cached['physical_port_lengths_mm']==[25,35,25]
        folder.mkdir(parents=True,exist_ok=True)
        shutil.copy2(template/'nozzle.msh',folder/'nozzle.msh')
        summary=json.loads((template/'mesh_summary.json').read_text())
        summary.update(name=name,template_mesh_sha256=cached['mesh_sha256'])
        write_json(folder/'mesh_summary.json',summary)
        print('MESH_READY',str(folder),summary['cells'],summary['nodes'],flush=True)
    else:
        summary = build(name, height=110, neck=46, fine=job.get('fine',False))
    session.settings.file.read_mesh(file_name=str(folder/'nozzle.msh'))
    session.tui.mesh.check()
    session.tui.mesh.quality()
    volume = session.fields.solution_variable_data.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
    assert volume.min() > 0
    setup = session.settings.setup
    setup.models.viscous.model = 'k-omega'
    setup.models.viscous.k_omega_model = 'sst'
    setup.materials.fluid['air'].density.value = RHO
    setup.materials.fluid['air'].viscosity.value = 1.8e-5
    total_flow=job.get('total_flow_m3_min')
    static_target=job.get('static_pressure')
    inlet_total=float(job.get('pressure',650 if static_target is not None else 400))
    if total_flow is not None:
        if 'inlet' not in setup.boundary_conditions.velocity_inlet:
            session.tui.define.boundary_conditions.zone_type('inlet','velocity-inlet')
        inlet=setup.boundary_conditions.velocity_inlet['inlet']
        inlet.momentum.velocity_magnitude.value=total_flow/60/summary['inlet_area_m2']
    else:
        session.tui.define.boundary_conditions.zone_type('inlet','pressure-inlet')
        inlet=setup.boundary_conditions.pressure_inlet['inlet']
        inlet.momentum.gauge_total_pressure.value=inlet_total
    inlet.turbulence.turbulence_specification = 'Intensity and Hydraulic Diameter'
    inlet.turbulence.turbulent_intensity = .05
    inlet.turbulence.hydraulic_diameter = .084
    outlet_pressure = np.zeros(3)
    for k in range(3):
        outlet = setup.boundary_conditions.pressure_outlet[f'outlet_{k}']
        outlet.momentum.gauge_pressure.value = 0
        outlet.momentum.prevent_reverse_flow = False
        outlet.turbulence.turbulence_specification = 'Intensity and Hydraulic Diameter'
        outlet.turbulence.backflow_turbulent_intensity = .05
        outlet.turbulence.backflow_hydraulic_diameter = .046
    definitions = {'pin':('surface-massavg','pressure','inlet'),
                   'ptin':('surface-massavg','total-pressure','inlet'),
                   'min':('surface-massflowrate',None,'inlet')}
    for k in range(3):
        definitions[f'm{k}'] = ('surface-massflowrate',None,f'outlet_{k}')
        definitions[f'pt{k}'] = ('surface-massavg','total-pressure',f'load_{k}')
    rd = session.settings.solution.report_definitions.surface
    for key,(kind,field,surf) in definitions.items():
        if key not in rd:
            rd.create(key)
        rd[key].report_type = kind
        rd[key].surface_names = [surf]
        if field:
            rd[key].field = field
    for eq in session.settings.solution.monitor.residual.equations:
        session.settings.solution.monitor.residual.equations[eq].absolute_criteria = 1e-5
    methods = session.settings.solution.methods
    methods.p_v_coupling.flow_scheme = 'Coupled'
    methods.high_order_term_relaxation.enable = True
    methods.high_order_term_relaxation.relaxation_factor = .25
    methods.high_order_term_relaxation.select_variables = 'all-variables'
    methods.spatial_discretization.discretization_scheme = {
        'mom':'first-order-upwind','k':'first-order-upwind','omega':'first-order-upwind','pressure':'standard'}
    session.settings.solution.initialization.hybrid_initialize()
    if job.get('warm'):
        warm_folder=ROOT/'cfd'/job['warm']
        if (warm_folder/'cell_fields.npz').exists():
            warm=np.load(warm_folder/'cell_fields.npz')
            target=session.fields.solution_variable_data.get_data(variable_name='SV_CENTROID',zone_names=['fluid'])['fluid']
            if target.shape==warm['SV_CENTROID'].shape and np.max(abs(target-warm['SV_CENTROID']))<1e-10:
                for variable in ['SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']:
                    session.fields.solution_variable_data.set_data(variable_name=variable,zone_names_to_data={'fluid':warm[variable]})
    start = time.time()
    history = []
    lengths = job.get('lengths', [.4459491605,.3183202283,.4156949245])
    friction = job.get('friction', .04)
    bend = job.get('bend', .5)
    passing = 0
    previous_q = None
    for outer in range(35):
        if outer == 2:
            methods.spatial_discretization.discretization_scheme = {
                'mom':'second-order-upwind','k':'second-order-upwind','omega':'second-order-upwind','pressure':'second-order'}
        session.settings.solution.run_calculation.iterate(iter_count=50)
        values = reports(session,list(definitions))
        q = np.asarray([-values[f'm{k}']/RHO*60 for k in range(3)])
        assert q.min() > 0, (name,q)
        target = downstream_pressure(q,curves,lengths,friction,bend)
        actual = np.asarray([values[f'pt{k}'] for k in range(3)])
        error = target-actual
        relative = abs(error)/np.maximum(target,1)*100
        dq = 100 if previous_q is None else float(np.max(abs(q/previous_q-1))*100)
        imbalance = abs(values['min']+sum(values[f'm{k}'] for k in range(3)))/abs(values['min'])*100
        static_error=0 if static_target is None else 100*abs(values['pin']-static_target)/max(abs(static_target),1)
        row = {'outer':outer+1,'elapsed_s':time.time()-start,**values,'Q':q.tolist(),
               'target_port_total_Pa':target.tolist(),'actual_port_total_Pa':actual.tolist(),
               'load_error_pct':relative.tolist(),'flow_change_pct':dq,'mass_imbalance_pct':imbalance,
               'outlet_static_pressure_Pa':outlet_pressure.tolist(),'inlet_static_target_error_pct':static_error}
        history.append(row)
        write_json(folder/'history.json',history)
        print('NETWORK_PROGRESS',name,json.dumps(row),flush=True)
        if max(relative)<1 and dq<.3 and imbalance<.1 and static_error<1 and outer>=6:
            passing += 1
        else:
            passing = 0
        if passing>=3:
            break
        if outer==34:
            break
        # These static pressures represent the truncated hose/nozzle system.
        # A negative gauge value can represent physical pressure recovery into
        # the much larger downstream slot; no porous energy source is used.
        outlet_pressure += np.clip(.35*error,-80,80)
        if static_target is not None:
            inlet_total+=float(np.clip(.35*(static_target-values['pin']),-80,80))
            inlet.momentum.gauge_total_pressure.value=inlet_total
        maximum_pressure=5000 if total_flow is not None else inlet_total-5
        outlet_pressure = np.clip(outlet_pressure,-3000,maximum_pressure)
        for k in range(3):
            setup.boundary_conditions.pressure_outlet[f'outlet_{k}'].momentum.gauge_pressure.value = float(outlet_pressure[k])
        previous_q = q
    fields = {v:session.fields.solution_variable_data.get_data(variable_name=v,zone_names=['fluid'])['fluid']
              for v in ['SV_CENTROID','SV_VOLUME','SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']}
    np.savez_compressed(folder/'cell_fields.npz',**fields)
    planes = session.settings.results.surfaces.plane_surface
    if 'adapter_cut' not in planes:
        planes.create('adapter_cut')
    planes['adapter_cut'].method = 'zx-plane'
    planes['adapter_cut'].y = .001
    surface(session,'adapter_cut',folder/'cut_fields.npz')
    result = {'name':name,'conditions':job,'reports':values,'branch_widths_mm':[225,180,315],
              'branch_flow_m3_min':q.tolist(),'total_flow_m3_min':float(q.sum()),
              'slot_area_mean_velocity_m_s':(q/60/(np.array([225,180,315])*16*1e-6)).tolist(),
              'pipe_cut_lengths_m':lengths,'pipe_friction_assumed':friction,'lower_bend_K_assumed':bend,
              'pressure_load_curve_source':curves,'physical_port_total_pressure_Pa':actual.tolist(),
              'adapter_total_pressure_loss_Pa':values['ptin']-float(np.average(actual,weights=q)),
              'load_consistency_error_pct':relative.tolist(),'network_load_consistency_pass':bool(max(relative)<1 and static_error<1),
              'equivalent_outlet_static_pressure_Pa':outlet_pressure.tolist(),
              'mass_imbalance_pct':imbalance,'last_flow_change_pct':dq,'actual_fan_curve_used':False,
              'hypothetical_inlet_total_pressure_Pa':job.get('pressure'),'prescribed_total_flow_m3_min':total_flow,
              'hypothetical_inlet_static_pressure_Pa':static_target,'inlet_static_target_error_pct':static_error,
              'required_inlet_static_pressure_Pa':values['pin'],'minimum_cell_volume_m3':float(volume.min())}
    write_json(folder/'results.json',result)
    session.settings.file.write_case_data(file_name=str(folder/'solution.cas.h5'))
    print('NETWORK_COMPLETE',name,json.dumps(result),flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plan')
    args = parser.parse_args()
    plan = json.loads((ROOT/args.plan).read_text())
    curves = json.loads((ROOT/'selected_pressure_curves.json').read_text())
    session = connect(launch=True,cleanup=True)
    try:
        for job in plan['jobs']:
            folder=ROOT/'cfd'/job['name']
            checkpoint=folder/'completed_checkpoint.json'
            signature=hashlib.sha256(json.dumps({'job':job,'curves':curves},sort_keys=True).encode()).hexdigest()
            reusable=False
            if checkpoint.exists() and (folder/'results.json').exists():
                saved=json.loads(checkpoint.read_text())
                reusable=saved.get('signature')==signature and saved.get('result_sha256')==hashlib.sha256((folder/'results.json').read_bytes()).hexdigest()
                reusable=reusable and all((folder/name).exists() and (folder/name).stat().st_size==size for name,size in saved.get('native_sizes',{}).items())
            if reusable:
                continue
            result=run(session,job,curves)
            assert result['network_load_consistency_pass'],f"Network load calibration incomplete: {job['name']}"
            write_json(checkpoint,{'signature':signature,'result_sha256':hashlib.sha256((folder/'results.json').read_bytes()).hexdigest(),
                                   'native_sizes':{name:(folder/name).stat().st_size for name in ['solution.cas.h5','solution.dat.h5']}})
    finally:
        session.exit(timeout=20,wait=30)
        PRIVATE.unlink(missing_ok=True)
        print('NETWORK_OWNED_SOLVER_CLOSED',flush=True)
