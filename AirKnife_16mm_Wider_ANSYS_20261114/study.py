"""Real Fluent runs. Prescribed-flow body screening, then free-jet cases.
Pressure-driven cases are explicitly hypothetical total-pressure conditions,
not the fan's unknown pressure-flow characteristic.
"""
import argparse,json,tempfile,time
from pathlib import Path
import numpy as np
import ansys.fluent.core as pf
from ansys.fluent.core.fields.field_data import SurfaceFieldDataRequest,ScalarFieldDataRequest,SurfaceDataType
from geometry import ROOT

PRIVATE=Path(tempfile.gettempdir())/'umbrella_airknife_connection_20261114_gap16.json'

def connect(launch=False,cleanup=False):
    if not launch:
        return pf.connect_to_fluent(**json.loads(PRIVATE.read_text()),cleanup_on_exit=cleanup,
            start_watchdog=False,start_transcript=True)
    s=pf.launch_fluent(fluent_path=r'C:\Program Files\ANSYS Inc\ANSYS Student\v261\fluent\ntbin\win64\fluent.exe',
        dimension=3,precision='double',processor_count=4,ui_mode='no_gui',cwd=str(ROOT),
        cleanup_on_exit=cleanup,start_watchdog=False,start_timeout=120,start_transcript=True)
    p=s.connection_properties
    PRIVATE.write_text(json.dumps({'ip':p.ip,'port':p.port,'password':p.password}),encoding='utf-8')
    return s

def configure(s,q,summary,pressure=None):
    setup=s.settings.setup;setup.models.viscous.model='k-omega';setup.models.viscous.k_omega_model='sst'
    setup.materials.fluid['air'].density.value=1.2;setup.materials.fluid['air'].viscosity.value=1.8e-5
    if pressure is None:
        if 'inlet' not in setup.boundary_conditions.velocity_inlet:
            s.tui.define.boundary_conditions.zone_type('inlet','velocity-inlet')
        inlet=setup.boundary_conditions.velocity_inlet['inlet']
        inlet.momentum.velocity_magnitude.value=q/60/summary['inlet_area_m2']
        inlet.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
        inlet.turbulence.turbulent_intensity=.05;inlet.turbulence.hydraulic_diameter=.084
    else:
        s.tui.define.boundary_conditions.zone_type('inlet','pressure-inlet')
        inlet=setup.boundary_conditions.pressure_inlet['inlet']
        print('PRESSURE_INLET_STATE',inlet.get_state(),flush=True)
        inlet.momentum.gauge_total_pressure.value=pressure
        inlet.momentum.supersonic_or_initial_gauge_pressure.value=0.
        inlet.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
        inlet.turbulence.turbulent_intensity=.05;inlet.turbulence.hydraulic_diameter=.084
    for name in setup.boundary_conditions.pressure_outlet:
        o=setup.boundary_conditions.pressure_outlet[name]
        o.momentum.gauge_pressure.value=0.;o.momentum.prevent_reverse_flow=False
        o.turbulence.turbulence_specification='Intensity and Hydraulic Diameter'
        o.turbulence.backflow_turbulent_intensity=.05
        o.turbulence.backflow_hydraulic_diameter=.025
    for eq in s.settings.solution.monitor.residual.equations:
        s.settings.solution.monitor.residual.equations[eq].absolute_criteria=1e-5
    defs={'pin':('surface-massavg','pressure','inlet'),'ptin':('surface-massavg','total-pressure','inlet'),
          'ptout':('surface-massavg','total-pressure','outlet'),
          'min':('surface-massflowrate',None,'inlet'),'mout':('surface-massflowrate',None,'outlet')}
    if summary.get('external'):defs['mambient']=('surface-massflowrate',None,'ambient')
    rd=s.settings.solution.report_definitions.surface
    for name,(typ,field,surf) in defs.items():
        if name not in rd:rd.create(name)
        rd[name].report_type=typ;rd[name].surface_names=[surf]
        if field:rd[name].field=field
    return list(defs)

def reports(s,names):
    raw=s.settings.solution.report_definitions.compute(report_defs=names)
    return {k:v[0] for item in raw for k,v in item.items()}

def surface(s,name,path):
    fd=s.fields.field_data
    geo=fd.get_field_data(SurfaceFieldDataRequest(surfaces=[name],data_types=[SurfaceDataType.Vertices,
        SurfaceDataType.FacesConnectivity,SurfaceDataType.FacesCentroid]))[name]
    faces=geo.connectivity;vtx=geo.vertices
    data={'vertices':vtx,'centroids':geo.face_centroids,'indices':np.concatenate(faces),
          'offsets':np.r_[0,np.cumsum([len(v) for v in faces])]}
    for field in ['x-velocity','y-velocity','z-velocity','pressure','total-pressure']:
        data[field]=fd.get_field_data(ScalarFieldDataRequest(surfaces=[name],field_name=field,node_value=False,boundary_value=True))[name]
    areas=[]
    for face in faces:
        v=vtx[face];areas.append(sum(np.linalg.norm(np.cross(v[k]-v[0],v[k+1]-v[0]))/2 for k in range(1,len(v)-1)))
    data['areas']=np.array(areas)
    np.savez_compressed(path,**data)
    return data

def solve(s,name,q=3.,pressure=None,legacy=False,batches=5,warm=None):
    out=ROOT/'cfd'/name;out.mkdir(parents=True,exist_ok=True)
    if legacy:
        source=ROOT.parent/'CFD_ANSYS_20261105'/'coarse'
        summary=json.loads((source/'mesh_summary.json').read_text());summary['external']=False
        mesh=source/'nozzle.msh'
    else:
        mesh=out/'nozzle.msh';summary=json.loads((out/'mesh_summary.json').read_text())
    s.settings.file.read_mesh(file_name=str(mesh));s.tui.mesh.check();s.tui.mesh.quality()
    names=configure(s,q,summary,pressure)
    methods=s.settings.solution.methods.spatial_discretization
    methods.discretization_scheme={'mom':'first-order-upwind','k':'first-order-upwind','omega':'first-order-upwind','pressure':'standard'}
    s.settings.solution.initialization.hybrid_initialize();history=[];start=time.time()
    if warm:
        from scipy.spatial import cKDTree
        src=np.load(ROOT/'cfd'/warm/'cell_fields.npz')
        src_xyz=src['SV_CENTROID'].reshape(-1,3)
        tgt=s.fields.solution_variable_data.get_data(variable_name='SV_CENTROID',zone_names=['fluid'])['fluid'].reshape(-1,3)
        dist,idx=cKDTree(src_xyz).query(tgt,k=8)
        weights=1/np.maximum(dist,1e-12)**2;weights/=weights.sum(axis=1,keepdims=True)
        mask=tgt[:,2]<=src_xyz[:,2].max()
        for var in ['SV_U','SV_V','SV_W','SV_P','SV_K','SV_O']:
            target=s.fields.solution_variable_data.get_data(variable_name=var,zone_names=['fluid'])['fluid']
            target[mask]=np.sum(src[var][idx[mask]]*weights[mask],axis=1)
            s.fields.solution_variable_data.set_data(variable_name=var,zone_names_to_data={'fluid':target})
        methods.discretization_scheme={'mom':'second-order-upwind','k':'second-order-upwind','omega':'second-order-upwind','pressure':'second-order'}
        print('INTERPOLATED_INITIAL_GUESS',warm,flush=True)
    for batch in range(batches):
        if batch==2:
            methods.discretization_scheme={'mom':'second-order-upwind','k':'second-order-upwind','omega':'second-order-upwind','pressure':'second-order'}
        s.settings.solution.run_calculation.iterate(iter_count=40)
        row={'batch':batch+1,'elapsed_s':time.time()-start,**reports(s,names)}
        history.append(row);(out/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
        print('CASE_PROGRESS',name,json.dumps(row),flush=True)
    final=history[-1]
    dat=surface(s,'outlet',out/'outlet_fields.npz')
    if summary.get('external'):
        # Physical slot is an internal section; export it and probe downstream.
        planes=s.settings.results.surfaces.plane_surface
        for pname,method,axis,val in [('slot','xy-plane','z',summary['height_mm']/1000+.00001),
                ('long_cut','yz-plane','x',.001),('short_cut','zx-plane','y',.001)]+[
                (f'plane_{d}mm','xy-plane','z',(summary['height_mm']+d)/1000) for d in [30,50,80]]:
            if pname not in planes:planes.create(pname)
            planes[pname].method=method;setattr(planes[pname],axis,val)
            surface(s,pname,out/(pname+'_fields.npz'))
    else:
        planes=s.settings.results.surfaces.plane_surface
        if 'long_cut' not in planes:planes.create('long_cut')
        planes['long_cut'].method='yz-plane';planes['long_cut'].x=.001
        surface(s,'long_cut',out/'long_cut_fields.npz')
    vi=s.fields.solution_variable_info.get_variables_info(zone_names=['fluid']).solution_variables
    cells={v:s.fields.solution_variable_data.get_data(variable_name=v,zone_names=['fluid'])['fluid']
           for v in ['SV_CENTROID','SV_VOLUME','SV_U','SV_V','SV_W','SV_P','SV_K','SV_O'] if v in vi}
    np.savez_compressed(out/'cell_fields.npz',**cells)
    assert all(np.isfinite(v).all() for v in cells.values())
    a=dat['areas'];uz=dat['z-velocity'];mean=float(np.average(uz,weights=a))
    mask=cells['SV_W']<-.01
    result={'name':name,'conditions':{'prescribed_Q_m3_min':q if pressure is None else None,
        'hypothetical_inlet_total_pressure_Pa':pressure,'actual_fan_curve_used':False,
        'height_mm':summary['height_mm'],'gap_mm':summary['gap_mm'],'span_mm':summary['span_mm'],'body_height_mm':summary['body_height_mm'],'lip_length_mm':summary['lip_length_mm'],'warm_start_source':warm,
        'vane_count':2 if legacy else 0,'external_free_jet':summary.get('external',False)},
        'reports':final,'required_static_pressure_Pa':final['pin'],
        'pressure_loss_to_domain_outlet_Pa':final['ptin']-final['ptout'],
        'nozzle_flow_m3_min':final['min']/1.2*60,
        'mass_imbalance_pct':abs(final['min']+final['mout']+final.get('mambient',0))/abs(final['min'])*100,
        'outlet_mean_axial_velocity_m_s':mean,
        'outlet_full_area_CV':float(np.sqrt(np.average((uz-mean)**2,weights=a))/max(mean,1e-12)),
        'negative_uz_volume_fraction':float(cells['SV_VOLUME'][mask].sum()/cells['SV_VOLUME'].sum()),
        'min_uz_m_s':float(cells['SV_W'].min()),
        'last_pressure_change_pct':100*abs(final['pin']-history[-2]['pin'])/max(abs(final['pin']),1e-9),
        'solver':'Fluent 2026 R1, 3D double, SST k-omega; steady incompressible; smooth walls'}
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    s.settings.file.write_case_data(file_name=str(out/'solution.cas.h5'))
    print('CASE_COMPLETE',name,json.dumps(result),flush=True)
    return result

if __name__=='__main__':
    raise SystemExit('Build with make_meshes.py, then execute run_study.py for the 16 mm comparison.')
