"""Prescribed-flow, steady incompressible SST nozzle comparison in Fluent."""
import argparse
import json
import time
import numpy as np
from session import ROOT,connect

def configure(s,level,q):
    setup=s.settings.setup
    setup.models.viscous.model='k-omega'
    setup.models.viscous.k_omega_model='sst'
    setup.materials.fluid['air'].density.value=1.2
    setup.materials.fluid['air'].viscosity.value=1.8e-5
    summary=json.loads((ROOT/level/'mesh_summary.json').read_text())
    inlet=setup.boundary_conditions.velocity_inlet['inlet']
    inlet.momentum.velocity_magnitude.value=q/60/summary['inlet_area_m2']
    inlet.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
    inlet.turbulence.turbulent_intensity=.05
    inlet.turbulence.hydraulic_diameter=.042
    outlet=setup.boundary_conditions.pressure_outlet['outlet']
    outlet.momentum.gauge_pressure.value=0.
    outlet.momentum.prevent_reverse_flow=False
    outlet.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
    outlet.turbulence.backflow_turbulent_intensity=.05
    outlet.turbulence.backflow_hydraulic_diameter=2*.216*.012/(.216+.012)
    for eq in s.settings.solution.monitor.residual.equations.get_object_names():
        s.settings.solution.monitor.residual.equations[eq].absolute_criteria=1e-5
    reports=s.settings.solution.report_definitions.surface
    defs={'pin':('surface-massavg','pressure','inlet'),
          'ptin':('surface-massavg','total-pressure','inlet'),
          'ptout':('surface-massavg','total-pressure','outlet'),
          'min':('surface-massflowrate',None,'inlet'),
          'mout':('surface-massflowrate',None,'outlet')}
    for name,(typ,field,surf) in defs.items():
        if name not in reports: reports.create(name)
        obj=reports[name]
        obj.report_type=typ
        obj.surface_names=[surf]
        if field: obj.field=field
    return summary

def main(a):
    s=connect()
    if a.read_mesh:
        s.settings.file.read_mesh(file_name=str(ROOT/a.level/'nozzle.msh'))
        s.tui.mesh.check()
        s.tui.mesh.quality()
    summary=configure(s,a.level,a.q)
    out=ROOT/a.level/f'Q{a.q:.2f}'
    out.mkdir(exist_ok=True)
    history=[]
    old=out/'history.json'
    if a.resume and old.exists(): history=json.loads(old.read_text())
    if a.interpolate_from:
        from scipy.spatial import cKDTree
        s.settings.solution.initialization.hybrid_initialize()
        original=np.load(ROOT/a.interpolate_from/'cell_fields.npz')
        target=s.fields.solution_variable_data.get_data(variable_name='SV_CENTROID',zone_names=['fluid'])['fluid'].reshape(-1,3)
        dist,idx=cKDTree(original['SV_CENTROID'].reshape(-1,3)).query(target,k=8)
        weight=1/np.maximum(dist,1e-12)**2
        weight/=weight.sum(axis=1,keepdims=True)
        for var in ['SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']:
            guess=np.sum(original[var][idx]*weight,axis=1)
            s.fields.solution_variable_data.set_data(variable_name=var,zone_names_to_data={'fluid':guess})
        print('INTERPOLATED_INITIAL_GUESS_ONLY',a.interpolate_from,flush=True)
    if a.scale_from is not None:
        original=np.load(ROOT/a.level/f'Q{a.scale_from:.2f}'/'cell_fields.npz')
        factor=a.q/a.scale_from
        for var,power in [('SV_U',1),('SV_V',1),('SV_W',1),('SV_P',2),('SV_K',2),('SV_O',1)]:
            s.fields.solution_variable_data.set_data(variable_name=var,
                zone_names_to_data={'fluid':original[var]*factor**power})
        print('SCALED_INITIAL_GUESS_ONLY',a.scale_from,a.q,flush=True)
    if not a.resume:
        s.settings.solution.methods.spatial_discretization.discretization_scheme={
            'mom':'first-order-upwind','k':'first-order-upwind','omega':'first-order-upwind','pressure':'standard'}
        s.settings.solution.initialization.hybrid_initialize()
    start=time.time()
    for batch in range(a.batches):
        if a.resume or batch>=2:
            s.settings.solution.methods.spatial_discretization.discretization_scheme={
                'mom':'second-order-upwind','k':'second-order-upwind','omega':'second-order-upwind','pressure':'second-order'}
        s.settings.solution.run_calculation.iterate(iter_count=a.batch_size)
        values=s.settings.solution.report_definitions.compute(report_defs=['pin','ptin','ptout','min','mout'])
        row={'batch':len(history)+1,'elapsed_s':time.time()-start,'reports':values}
        history.append(row)
        old.write_text(json.dumps(history,indent=2),encoding='utf-8')
        print('BATCH_RESULT',json.dumps(row),flush=True)
    s.settings.file.write_case_data(file_name=str(out/'solution.cas.h5'))
    (out/'conditions.json').write_text(json.dumps({'flow_m3_min':a.q,'rho_kg_m3':1.2,'mu_Pa_s':1.8e-5,
        'inlet_area_m2':summary['inlet_area_m2'],'outlet_area_m2':summary['outlet_area_m2'],
        'inlet_velocity_m_s':a.q/60/summary['inlet_area_m2'],'turbulence_intensity':.05,
        'model':'steady incompressible RANS SST k-omega; no energy; smooth walls',
        'scaled_initial_guess_from_flow_m3_min':a.scale_from,
        'interpolated_initial_guess_from':a.interpolate_from,
        'inlet':'uniform axial velocity; no blower swirl','outlet':'0 Pa gauge at nozzle lip; reversal allowed'},indent=2),encoding='utf-8')
    print('CASE_SAVED',str(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--level',default='coarse',choices=['coarse','medium','fine'])
    p.add_argument('--q',type=float,default=1.)
    p.add_argument('--batches',type=int,default=8)
    p.add_argument('--batch-size',type=int,default=50)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--read-mesh',action='store_true')
    p.add_argument('--scale-from',type=float)
    p.add_argument('--interpolate-from')
    main(p.parse_args())
