"""Comparable same-area blowing proxies from actual Fluent plane exports."""
import csv,json,re
from pathlib import Path
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from geometry import ROOT
OLD=ROOT.parent/'AirKnife_16mm_Wider_ANSYS_20261114'
REFERENCES={'ref216':OLD/'cfd/jet_H260_W216','ref252':OLD/'cfd/jet_H320_W252'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2),encoding='utf-8')
def convergence():
    text='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in [ROOT/'fluent_study.log',ROOT/'followup_study.log'] if p.exists())
    pat=re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+');rows=[]
    for line in text.splitlines():
        m=pat.match(line)
        if m:rows.append([int(m[1])]+[float(x) for x in m[2].split()])
        if 'CASE_COMPLETE ' not in line:continue
        name=line.split('CASE_COMPLETE ',1)[1].split()[0];p=ROOT/'cfd'/name;r=read(p/'results.json');h=read(p/'history.json');last=rows[-1]
        dq=100*abs(h[-1]['min']/h[-2]['min']-1)
        v={'last_iteration':last[0],'last_residuals':dict(zip(['continuity','Ux','Uy','Uz','k','omega'],last[1:])),
            'flow_change_pct':dq,'pressure_change_pct':r['last_pressure_change_pct'],'mass_imbalance_pct':r['mass_imbalance_pct'],
            'engineering_convergence_pass':last[1]<1e-4 and max(last[2:5])<1e-6 and max(last[5:])<1e-5 and dq<.5 and r['last_pressure_change_pct']<.5 and r['mass_imbalance_pct']<.1,
            'all_residuals_under_1e_minus_5':max(last[1:])<1e-5,
            'criteria':{'continuity':1e-4,'velocity':1e-6,'k_omega':1e-5,'flow_and_pressure_stability_pct':.5,'mass_imbalance_pct':.1}}
        save(p/'convergence.json',v);rows=[];print('CONVERGENCE',name,v['engineering_convergence_pass'],flush=True)
def integrate(values,x,y):
    return float(np.trapezoid(np.trapezoid(values,y*1e-3,axis=1),x*1e-3,axis=0))
def case_metrics(source,out):
    out.mkdir(parents=True,exist_ok=True);r=read(source/'results.json');c=r['conditions'];span=c['span_mm'];gap=c['gap_mm'];height=c['height_mm']
    d=np.load(source/'slot_fields.npz');xy=d['centroids'][:,:2]*1000
    m=(abs(xy[:,0])<=gap/2+1e-5)&(abs(xy[:,1])<=span/2+1e-4);a=d['areas'][m];u=d['z-velocity'][m]
    pt=float(np.average(d['total-pressure'][m],weights=a*np.maximum(u,0)))
    result={'computed_Q_m3_min':r['nozzle_flow_m3_min'],'slot_mean_Uz_m_s':float(np.average(u,weights=a)),
        'nozzle_total_pressure_loss_Pa':r['reports']['ptin']-pt,'total_pressure_Pa':c['hypothetical_inlet_total_pressure_Pa'],
        'span_mm':span,'gap_mm':gap,'height_mm':height}
    for distance in [30,50,80]:
        p=np.load(source/f'plane_{distance}mm_fields.npz');xy=p['centroids'][:,:2]*1000;f=LinearNDInterpolator(xy,p['z-velocity'])
        yy=np.linspace(-100,100,201);xx=np.linspace(-gap/2,gap/2,65);xg,yg=np.meshgrid(xx,yy,indexing='ij')
        field=np.asarray(f(np.c_[xg.ravel(),yg.ravel()])).reshape(xg.shape);assert np.isfinite(field).all()
        pressure=.6*np.maximum(field,0)**2;area=(xx[-1]-xx[0])*(yy[-1]-yy[0])*1e-6
        xfull=np.linspace(-40,40,161);xf,yf=np.meshgrid(xfull,yy,indexing='ij');full=np.asarray(f(np.c_[xf.ravel(),yf.ravel()])).reshape(xf.shape)
        assert np.isfinite(full).all()
        common_flux=integrate(1.2*np.maximum(full,0)**2,xfull,yy)
        line=np.asarray(f(np.c_[yy*0,yy]));covered=np.linspace(-(span-16)/2,(span-16)/2,121);cv=np.asarray(f(np.c_[covered*0,covered]));assert np.isfinite(cv).all()
        roi=(abs(xy[:,0])<=40)&(abs(xy[:,1])<=160)
        result[f'{distance}mm']={'same_200x16_patch_normal_dynamic_pressure_mean_Pa':integrate(pressure,xx,yy)/area,
            'same_200x16_patch_pressure_p10_Pa':float(np.percentile(pressure,10)),
            'same_200x80_strip_forward_momentum_N':common_flux,'common_200mm_line_mean_Uz_m_s':float(line.mean()),
            'covered_line_length_mm':span-16,'covered_line_mean_Uz_m_s':float(cv.mean()),'covered_line_CV_pct':100*float(cv.std()/cv.mean()),
            'full_320x80_window_momentum_N':float(np.sum(1.2*p['areas'][roi]*np.maximum(p['z-velocity'][roi],0)**2)),
            'patch_grid_points':[len(xx),len(yy)],'strip_grid_points':[len(xfull),len(yy)]}
        np.savetxt(out/f'profile_{distance}mm.csv',np.c_[covered,cv],delimiter=',',header='Y_mm,Uz_at_X0_m_s',comments='')
    save(out/'performance_metrics.json',result)
    return result
def main():
    convergence();results={}
    for name,source in REFERENCES.items():results[name]=case_metrics(source,ROOT/'references'/name)
    for p in sorted((ROOT/'cfd').glob('*/results.json')):
        if read(p)['conditions']['external_free_jet']:results[p.parent.name]=case_metrics(p.parent,p.parent)
    save(ROOT/'performance_summary.json',results)
    for name,r in results.items():print('PERFORMANCE',name,json.dumps(r['80mm']),flush=True)
if __name__=='__main__':main()
