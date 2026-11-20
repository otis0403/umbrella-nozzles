import json,time,importlib
import geometry as _geometry
importlib.reload(_geometry)
import numpy as np
from scipy.spatial import cKDTree
from geometry import ROOT,port,branch_grid,port_grid,reference_port
from build_adapter_mesh import build
from legacy_study import reports,surface
from network import loads

def run(s,job):
    if job.get('action')=='resume_nozzle':
        from resume_nozzle import resume
        return resume(s,job)
    if job.get('action')=='refresh_curves':
        from network import curves
        return curves()
    name=job['name'];height=job.get('height',120);neck=job.get('neck',46);fine=job.get('fine',False)
    out=ROOT/'cfd'/name;meta=build(name,height,neck,fine,job.get('reference',False))
    s.settings.file.read_mesh(file_name=str(out/'nozzle.msh'));s.tui.mesh.check();s.tui.mesh.quality()
    volumes=s.fields.solution_variable_data.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
    assert np.min(volumes)>0
    setup=s.settings.setup;setup.models.viscous.model='k-omega';setup.models.viscous.k_omega_model='sst'
    setup.materials.fluid['air'].density.value=1.2;setup.materials.fluid['air'].viscosity.value=1.8e-5
    s.tui.define.boundary_conditions.zone_type('inlet','pressure-inlet');inlet=setup.boundary_conditions.pressure_inlet['inlet']
    inlet.momentum.gauge_total_pressure.value=job.get('pressure',400);inlet.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
    inlet.turbulence.turbulent_intensity=.05;inlet.turbulence.hydraulic_diameter=.084
    conditions=loads(job['gap'],job.get('center',1.),job.get('side',1.2),job.get('friction',.04),job.get('bend',.5))
    for k,load in enumerate(conditions):
        s.tui.define.boundary_conditions.zone_type(f'load_{k}','porous-jump')
        bc=setup.boundary_conditions.porous_jump[f'load_{k}'].porous_jump
        bc.alpha=load['permeability_m2'];bc.dm=.001;bc.c2=load['c2_per_m']
        print('POROUS_LOAD',k,bc.get_state(),flush=True)
        outlet=setup.boundary_conditions.pressure_outlet[f'outlet_{k}'];outlet.momentum.gauge_pressure.value=0.
        outlet.momentum.prevent_reverse_flow=False;outlet.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
        outlet.turbulence.backflow_turbulent_intensity=.05;outlet.turbulence.backflow_hydraulic_diameter=.046
    defs={'pin':('surface-massavg','pressure','inlet'),'ptin':('surface-massavg','total-pressure','inlet'),'min':('surface-massflowrate',None,'inlet')}
    for k in range(3):defs[f'm{k}']=('surface-massflowrate',None,f'outlet_{k}')
    rd=s.settings.solution.report_definitions.surface
    for key,(typ,field,surf) in defs.items():
        if key not in rd:rd.create(key)
        rd[key].report_type=typ;rd[key].surface_names=[surf]
        if field:rd[key].field=field
    for eq in s.settings.solution.monitor.residual.equations:s.settings.solution.monitor.residual.equations[eq].absolute_criteria=1e-5
    schemes=s.settings.solution.methods.spatial_discretization
    schemes.discretization_scheme={'mom':'first-order-upwind','k':'first-order-upwind','omega':'first-order-upwind','pressure':'standard'}
    s.settings.solution.initialization.hybrid_initialize()
    if job.get('warm'):
        src=np.load(ROOT/'cfd'/job['warm']/'cell_fields.npz');target=s.fields.solution_variable_data.get_data(variable_name='SV_CENTROID',zone_names=['fluid'])['fluid'].reshape(-1,3)
        dist,idx=cKDTree(src['SV_CENTROID'].reshape(-1,3)).query(target,k=8);weight=1/np.maximum(dist,1e-12)**2;weight/=weight.sum(1)[:,None]
        for var in ['SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']:
            s.fields.solution_variable_data.set_data(variable_name=var,zone_names_to_data={'fluid':np.sum(src[var][idx]*weight,axis=1)})
        schemes.discretization_scheme={'mom':'second-order-upwind','k':'second-order-upwind','omega':'second-order-upwind','pressure':'second-order'}
    history=[];start=time.time();passing_batches=0
    for batch in range(job.get('batches',7)):
        if batch==2:schemes.discretization_scheme={'mom':'second-order-upwind','k':'second-order-upwind','omega':'second-order-upwind','pressure':'second-order'}
        s.settings.solution.run_calculation.iterate(iter_count=40);r=dict(batch=batch+1,elapsed_s=time.time()-start,**reports(s,list(defs)))
        history.append(r);(out/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8');print('CASE_PROGRESS',name,json.dumps(r),flush=True)
        from convergence_control import ready
        passing_batches=passing_batches+1 if ready(history,['m0','m1','m2']) else 0
        if passing_batches>=2:
            print('ENGINEERING_CRITERIA_STABLE',name,flush=True);break
    # A porous jump acts on local velocity, whereas pipe resistance uses mean
    # flow. Calibrate its coefficient against the upstream mean TOTAL pressure
    # so nonuniform outlet profiles do not silently bias the network model.
    curve=json.loads((ROOT/'nozzle_pressure_curves.json').read_text())[str(int(job['gap']))]
    from network import A46,RHO
    calibration=[]
    for correction in range(7):
        cells={var:s.fields.solution_variable_data.get_data(variable_name=var,zone_names=['fluid'])['fluid'] for var in ['SV_CENTROID','SV_VOLUME','SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']}
        assert all(np.isfinite(v).all() for v in cells.values())
        xyz=cells['SV_CENTROID'].reshape(-1,3)*1000;vel=np.c_[cells['SV_U'],cells['SV_V'],cells['SV_W']];pt=cells['SV_P']+.6*(vel*vel).sum(1)
        q=np.array([-history[-1][f'm{k}']/1.2*60 for k in range(3)]);assert q.min()>0
        port_pressures=[];virtual=np.zeros(len(xyz),bool)
        for k in range(3):
            E,D=reference_port(k) if job.get('reference') else port(k,height);dist=(xyz-E)@D;radial=np.linalg.norm(xyz-E-dist[:,None]*D,axis=1)
            mask=(dist>22.5)&(dist<24.9)&(radial<23.001);weights=cells['SV_VOLUME'][mask]*np.maximum(vel[mask]@D,0)
            port_pressures.append(float(np.average(pt[mask],weights=weights)));virtual|=(dist>25)&(radial<23.001)
        speed=q/60/A46;dynamic=.5*RHO*speed**2
        target=curve['a_Pa_per_Q2']*q*q+curve['b_Pa_per_Q']*q+dynamic*np.array([v['hose_K_referred_to_port']+v['joint_K_assumed'] for v in conditions])
        errors=100*(np.asarray(port_pressures)/target-1)
        calibration.append(dict(iteration=correction,Q_m3_min=q.tolist(),target_total_pressure_Pa=target.tolist(),actual_total_pressure_Pa=port_pressures,error_pct=errors.tolist()))
        print('NETWORK_CALIBRATION',name,json.dumps(calibration[-1]),flush=True)
        stable=max(abs(history[-1][f'm{k}']/history[-2][f'm{k}']-1) for k in range(3))<.005
        if (max(abs(errors))<2. and stable) or correction==6:break
        if max(abs(errors))>=2.:
            for k in range(3):
                factor=float(np.clip((target[k]-dynamic[k])/max(port_pressures[k]-dynamic[k],1),.5,2))
                factor=1+.7*(factor-1);bc=setup.boundary_conditions.porous_jump[f'load_{k}'].porous_jump;bc.c2=float(bc.c2())*factor
        s.settings.solution.run_calculation.iterate(iter_count=40);history.append(dict(batch=len(history)+1,elapsed_s=time.time()-start,**reports(s,list(defs))))
        (out/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
    np.savez_compressed(out/'cell_fields.npz',**cells)
    inside=~virtual;negative=inside&(cells['SV_W']<-.01)
    paths=[];tangents=[]
    for k in range(3):
        if job.get('reference'):
            from geometry import reference_branch_grid,reference_port_grid
            points=np.array([reference_branch_grid(k,t,2,2)[1,1] for t in np.linspace(0,1,61)]+[reference_port_grid(k,d,2,2)[1,1] for d in np.linspace(.5,25,26)])
        else:points=np.array([branch_grid(k,t,height,2,2,neck=neck)[1,1] for t in np.linspace(0,1,61)]+[port_grid(k,d,height,2,2)[1,1] for d in np.linspace(.5,25,26)])
        tangent=np.gradient(points,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None];paths.extend(points);tangents.extend(tangent)
    _,nearest=cKDTree(paths).query(xyz);direction=np.array(tangents)[nearest];direction[xyz[:,2]<(40 if job.get('reference') else 30)]=[0,0,1]
    local_reverse=inside&(np.sum(vel*direction,axis=1)<-.01)
    final=history[-1];change=max(100*abs(final[f'm{k}']/history[-2][f'm{k}']-1) for k in range(3))
    result=dict(name=name,conditions=job,equivalent_loads=conditions,actual_fan_curve_used=False,reports=final,
        branch_flow_m3_min=q.tolist(),total_flow_m3_min=float(q.sum()),branch_share_pct=(q/q.sum()*100).tolist(),balance_error_pct=float(max(abs(q/q.mean()-1))*100),
        physical_port_total_pressure_Pa=port_pressures,adapter_total_pressure_loss_Pa=final['ptin']-float(np.average(port_pressures,weights=q)),
        mass_imbalance_pct=100*abs(final['min']+sum(final[f'm{k}'] for k in range(3)))/abs(final['min']),last_flow_change_pct=change,
        last_pressure_change_pct=100*abs(final['pin']/history[-2]['pin']-1),internal_negative_global_Z_volume_pct=100*float(cells['SV_VOLUME'][negative].sum()/cells['SV_VOLUME'][inside].sum()),
        internal_negative_local_flow_volume_pct=100*float(cells['SV_VOLUME'][local_reverse].sum()/cells['SV_VOLUME'][inside].sum()),
        native_minimum_cell_volume_m3=float(volumes.min()),network_calibration=calibration,network_load_consistency_pass=bool(max(abs(errors))<2.))
    planes=s.settings.results.surfaces.plane_surface
    if 'adapter_cut' not in planes:planes.create('adapter_cut')
    planes['adapter_cut'].method='zx-plane';planes['adapter_cut'].y=.001;surface(s,'adapter_cut',out/'cut_fields.npz')
    (out/'boundary_conditions.json').write_text(json.dumps(dict(pressure_inlet_total_Pa=job.get('pressure',400),pressure_outlets=list(setup.boundary_conditions.pressure_outlet.get_object_names()),
        porous_jumps={f'load_{k}':setup.boundary_conditions.porous_jump[f'load_{k}'].porous_jump.get_state() for k in range(3)}),indent=2),encoding='utf-8')
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');s.settings.file.write_case_data(file_name=str(out/'solution.cas.h5'))
    print('CASE_COMPLETE',name,json.dumps(result),flush=True)

def verify(s,cases):
    rows=[]
    for name in cases:
        p=ROOT/'cfd'/name;r=json.loads((p/'results.json').read_text());s.settings.file.read_case_data(file_name=str(p/'solution.cas.h5'))
        names=['pin','ptin','min']+([f'm{k}' for k in range(3)] if 'branch_flow_m3_min' in r else ['mout'])
        values=reports(s,names);err=max(abs(values[k]-r['reports'][k])/max(abs(r['reports'][k]),1e-8) for k in names);assert err<1e-8
        rows.append(dict(case=name,native_case_data_reopened=True,maximum_relative_error=err))
    (ROOT/'native_reopen_checks.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
