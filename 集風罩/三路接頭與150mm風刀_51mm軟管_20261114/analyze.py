import json,re
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from geometry import ROOT

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')

def convergence():
    logs=sorted(ROOT.glob('fluent*.log'),key=lambda p:p.stat().st_mtime)
    text='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in logs);rows=[];result={}
    pattern=re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+')
    for line in text.splitlines():
        match=pattern.match(line)
        if match:rows.append([int(match[1])]+[float(v) for v in match[2].split()])
        if 'CASE_COMPLETE ' not in line:continue
        event_text=line.split('CASE_COMPLETE ',1)[1];name,_,payload=event_text.partition(' ');p=ROOT/'cfd'/name
        if not (p/'results.json').exists():rows=[];continue
        r=read(p/'results.json')
        if r.get('invalidated_for_free_jet_selection'):rows=[];continue
        # A newer log file can contain old completions followed by other cases.
        # Match the actual saved solution's reports, rather than file mtime.
        try:event=json.loads(payload)
        except json.JSONDecodeError:rows=[];continue
        if event.get('reports')!=r.get('reports'):rows=[];continue
        history=read(p/'history.json');last=rows[-1]
        dq=r.get('last_flow_change_pct',100*abs(history[-1]['min']/history[-2]['min']-1));dp=r['last_pressure_change_pct']
        value=dict(iteration=last[0],residuals=dict(zip(['continuity','Ux','Uy','Uz','k','omega'],last[1:])),last_flow_change_pct=dq,last_pressure_change_pct=dp,
            mass_imbalance_pct=r['mass_imbalance_pct'],engineering_convergence_pass=last[1]<1e-4 and max(last[2:5])<1e-6 and max(last[5:])<1e-5 and dq<.5 and dp<.5 and r['mass_imbalance_pct']<.1,
            strict_all_residuals_under_1e_minus_5=max(last[1:])<1e-5)
        write(p/'convergence.json',value);result[name]=value;rows=[]
    write(ROOT/'convergence_summary.json',result);return result

def jet_metrics(name):
    p=ROOT/'cfd'/name;r=read(p/'results.json');gap=r['conditions']['gap_mm'];result=dict(case=name,Q_m3_min=r['nozzle_flow_m3_min'],gap_mm=gap)
    assert not r.get('invalidated_for_free_jet_selection'),name
    if (p/'boundary_conditions.json').exists():assert read(p/'boundary_conditions.json')['ambient_open_verified'],name
    slot=np.load(p/'slot_fields.npz');xy=slot['centroids'][:,:2]*1000;mask=(abs(xy[:,0])<gap/2+.001)&(abs(xy[:,1])<75.001)
    result['slot_mean_Uz_m_s']=float(np.average(slot['z-velocity'][mask],weights=slot['areas'][mask]))
    weights=slot['areas'][mask]*np.maximum(slot['z-velocity'][mask],0)
    result['physical_slot_mass_weighted_total_pressure_Pa']=float(np.average(slot['total-pressure'][mask],weights=weights))
    result['nozzle_body_total_pressure_loss_Pa']=r['reports']['ptin']-result['physical_slot_mass_weighted_total_pressure_Pa']
    result['slot_net_Q_m3_min']=float(np.sum(slot['areas'][mask]*slot['z-velocity'][mask])*60)
    for d in [30,50,80]:
        data=np.load(p/f'plane_{d}mm_fields.npz');xy=data['centroids'][:,:2]*1000;f=LinearNDInterpolator(xy,data['z-velocity'])
        x=np.linspace(-10,10,81);y=np.linspace(-70,70,141);X,Y=np.meshgrid(x,y,indexing='ij');v=f(np.c_[X.ravel(),Y.ravel()]).reshape(X.shape);assert np.isfinite(v).all()
        pressure=.6*np.maximum(v,0)**2;mean=float(np.trapezoid(np.trapezoid(pressure,y/1000,axis=1),x/1000)/(140*20*1e-6))
        xx=np.linspace(-40,40,161);XX,YY=np.meshgrid(xx,y,indexing='ij');vv=f(np.c_[XX.ravel(),YY.ravel()]).reshape(XX.shape)
        momentum=float(np.trapezoid(np.trapezoid(1.2*np.maximum(vv,0)**2,y/1000,axis=1),xx/1000))
        line=f(np.c_[np.zeros(141),y]);cv=float(line.std()/line.mean()*100)
        result[f'{d}mm']=dict(same_140x20_patch_mean_normal_dynamic_pressure_Pa=mean,same_140x80_strip_momentum_N=momentum,
            core_140mm_line_CV_pct=cv,core_line_mean_Uz_m_s=float(line.mean()),patch_pressure_p10_Pa=float(np.percentile(pressure,10)))
        np.savetxt(p/f'profile_{d}mm.csv',np.c_[y,line],delimiter=',',header='Y_mm,Uz_m_s',comments='')
    result['minimum_pressure_proxy_Pa']=min(result[f'{d}mm']['same_140x20_patch_mean_normal_dynamic_pressure_Pa'] for d in [30,50,80])
    write(p/'performance_metrics.json',result);return result

def main():
    cv=convergence();print('CONVERGENCE',[(k,v['engineering_convergence_pass']) for k,v in cv.items()],flush=True)
    for p in (ROOT/'cfd').glob('*/results.json'):
        r=read(p)
        if r.get('conditions',{}).get('external_free_jet') and not r.get('invalidated_for_free_jet_selection'):print('JET_METRICS',json.dumps(jet_metrics(p.parent.name)),flush=True)

if __name__=='__main__':main()
