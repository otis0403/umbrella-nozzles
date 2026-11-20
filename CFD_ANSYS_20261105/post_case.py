import argparse
import json
from pathlib import Path
import numpy as np
from session import ROOT,connect
from ansys.fluent.core.fields.field_data import SurfaceFieldDataRequest,ScalarFieldDataRequest,SurfaceDataType


def export(s,out):
    info=s.fields.solution_variable_info.get_variables_info(zone_names=['fluid'])
    available=info.solution_variables
    (out/'available_variables.json').write_text(json.dumps(available,indent=2),encoding='utf-8')
    wanted=['SV_CENTROID','SV_VOLUME','SV_U','SV_V','SV_W','SV_P','SV_K','SV_O','SV_TKE','SV_OMEGA']
    arrays={}
    for var in wanted:
        if var in available:
            arrays[var]=s.fields.solution_variable_data.get_data(variable_name=var,zone_names=['fluid'])['fluid']
    np.savez_compressed(out/'cell_fields.npz',**arrays)
    print('CELL_ARRAYS',{k:v.shape for k,v in arrays.items()},flush=True)
    summary={}
    if 'SV_W' in arrays and 'SV_VOLUME' in arrays:
        vol=arrays['SV_VOLUME'];uz=arrays['SV_W']
        summary['fluid_volume_m3']=float(vol.sum())
        summary['min_axial_velocity_m_s']=float(uz.min())
        for threshold in [0,.001,.01,.05]:
            mask=uz < -threshold
            summary[f'reverse_volume_fraction_below_minus_{threshold:g}_m_s']=float(vol[mask].sum()/vol.sum())
        mask=uz<-.01
        xyz=arrays['SV_CENTROID'].reshape(-1,3)
        summary['reverse_region_bounds_m']=[xyz[mask].min(0).tolist(),xyz[mask].max(0).tolist()] if mask.any() else None
    surfaces=['inlet','outlet','housing','long_vane','short_vane']
    # Off-centre cuts avoid cutting along a retained vane wall.
    planes=s.settings.results.surfaces.plane_surface
    for name,method,axis,val in [('long_cut','yz-plane','x',.003),('short_cut','zx-plane','y',.003),
                                 ('near_outlet','xy-plane','z',.198)]:
        if name not in planes:
            planes.create(name)
            planes[name].method=method
            setattr(planes[name],axis,val)
        surfaces.append(name)
    fd=s.fields.field_data
    for name in surfaces:
        geo=fd.get_field_data(SurfaceFieldDataRequest(surfaces=[name],data_types=[SurfaceDataType.Vertices,
            SurfaceDataType.FacesConnectivity,SurfaceDataType.FacesCentroid,SurfaceDataType.FacesNormal]))[name]
        vertices=geo.vertices
        faces=geo.connectivity
        data={'vertices':vertices,'face_centroids':geo.face_centroids,'face_normals':geo.face_normals}
        # Flatten variable polygon connectivity with offsets, avoiding pickled arrays.
        data['connectivity']=np.concatenate(faces)
        data['offsets']=np.r_[0,np.cumsum([len(x) for x in faces])]
        wall=name in ['housing','long_vane','short_vane']
        fields=['y-plus'] if wall else ['x-velocity','y-velocity','z-velocity','velocity-magnitude','pressure','total-pressure']
        for field in fields:
            data[field]=fd.get_field_data(ScalarFieldDataRequest(surfaces=[name],field_name=field,node_value=False,boundary_value=True))[name]
        np.savez_compressed(out/(name+'_fields.npz'),**data)
        if name=='outlet':
            areas=[]
            for face in faces:
                v=vertices[face]
                areas.append(sum(np.linalg.norm(np.cross(v[k]-v[0],v[k+1]-v[0]))/2 for k in range(1,len(v)-1)))
            area=np.array(areas);uz=data['z-velocity'];mean=np.average(uz,weights=area)
            summary['outlet_area_m2']=float(area.sum())
            summary['outlet_mean_uz_m_s']=float(mean)
            summary['outlet_face_min_uz_m_s']=float(uz.min())
            summary['outlet_face_max_uz_m_s']=float(uz.max())
            summary['outlet_area_weighted_CV']=float(np.sqrt(np.average((uz-mean)**2,weights=area))/mean)
            summary['outlet_reverse_flux_fraction']=float(np.sum(area*np.maximum(-uz,0))/np.sum(area*np.maximum(uz,0)))
            summary['outlet_area_integrated_flow_m3_min']=float(np.sum(area*uz)*60)
            data['areas_m2']=area
            np.savez_compressed(out/(name+'_fields.npz'),**data)
            xyz=geo.face_centroids
            np.savetxt(out/'outlet_face_values.csv',np.c_[xyz,area,uz,data['velocity-magnitude'],data['pressure'],data['total-pressure']],
                       delimiter=',',header='x_m,y_m,z_m,area_m2,uz_m_s,speed_m_s,static_pressure_Pa,total_pressure_Pa',comments='')
        if wall:
            vals=data['y-plus']
            summary[name+'_yplus_percentiles_0_50_95_100']=np.percentile(vals,[0,50,95,100]).tolist()
    values=s.settings.solution.report_definitions.compute(report_defs=['pin','ptin','ptout','min','mout'])
    merged={k:val[0] for item in values for k,val in item.items()}
    summary['reports_SI']=merged
    summary['total_pressure_loss_Pa']=merged['ptin']-merged['ptout']
    summary['required_inlet_static_pressure_Pa']=merged['pin']
    summary['mass_imbalance_pct']=abs(merged['min']+merged['mout'])/abs(merged['min'])*100
    summary['viscous_model']=s.settings.setup.models.viscous.get_state()
    summary['methods']=s.settings.solution.methods.get_state()
    (out/'solver_configuration.json').write_text(json.dumps({
        'viscous':summary['viscous_model'],'methods':summary['methods'],
        'air_material':s.settings.setup.materials.fluid['air'].get_state(),
        'inlet':s.settings.setup.boundary_conditions.velocity_inlet['inlet'].get_state(),
        'outlet':s.settings.setup.boundary_conditions.pressure_outlet['outlet'].get_state(),
        'residual_monitor':s.settings.solution.monitor.residual.get_state()},indent=2),encoding='utf-8')
    (out/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('POST_RESULTS',json.dumps(summary,indent=2),flush=True)
    # Include the postprocessing surfaces in the archived case.
    s.settings.file.write_case_data(file_name=str(out/'review.cas.h5'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--level',default='coarse')
    p.add_argument('--q',type=float,default=1.)
    a=p.parse_args()
    export(connect(),ROOT/a.level/f'Q{a.q:.2f}')
