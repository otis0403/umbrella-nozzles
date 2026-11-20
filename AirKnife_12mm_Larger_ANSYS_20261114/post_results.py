"""Compare real Fluent exports; all working-distance metrics have explicit regions."""
import csv,json,re
import numpy as np
from scipy.interpolate import LinearNDInterpolator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.font_manager import fontManager
from geometry import ROOT
fontManager.addfont(r'C:\Windows\Fonts\msjh.ttc')
plt.rcParams.update({'font.family':'Microsoft JhengHei','axes.unicode_minus':False})
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def csvout(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def residuals():
    raw=(ROOT/'fluent_study.log').read_bytes();text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    pat=re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+')
    records=[]
    for line in text.splitlines():
        match=pat.match(line)
        if match:records.append([int(match[1])]+[float(v) for v in match[2].split()])
        if 'CASE_COMPLETE ' not in line:continue
        name=line.split('CASE_COMPLETE ',1)[1].split()[0];folder=ROOT/'cfd'/name;r=read(folder/'results.json');hist=read(folder/'history.json')
        last=records[-1];dq=100*abs(hist[-1]['min']/hist[-2]['min']-1)
        checks={'last_iteration':last[0],'last_residuals':dict(zip(['continuity','Ux','Uy','Uz','k','omega'],last[1:])),
            'last_flow_change_pct':dq,'last_inlet_pressure_change_pct':r['last_pressure_change_pct'],
            'mass_imbalance_pct':r['mass_imbalance_pct'],
            'engineering_convergence_pass':last[1]<1e-4 and max(last[2:5])<1e-6 and max(last[5:])<1e-5 and dq<.5
                and r['last_pressure_change_pct']<.5 and r['mass_imbalance_pct']<.1,
            'strict_all_residuals_below_1e_minus_5':max(last[1:])<1e-5,
            'criteria':{'continuity':1e-4,'velocity':1e-6,'k_omega':1e-5,'last_pressure_and_flow_change_pct':.5,'mass_imbalance_pct':.1}}
        (folder/'convergence.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
        np.savetxt(folder/'residual_history.csv',np.array(records),delimiter=',',header='iteration,continuity,Ux,Uy,Uz,k,omega',comments='')
        print('CONVERGENCE',name,checks['engineering_convergence_pass'],last[1],flush=True);records=[]
def polyd(d,axes):
    return [d['vertices'][d['indices'][a:b]][:,axes]*1000 for a,b in zip(d['offsets'][:-1],d['offsets'][1:])]
def metrics(plots=True):
    rows=[];bodyrows=[]
    for case in sorted((ROOT/'cfd').iterdir()):
        if not case.is_dir() or not (case/'results.json').exists():continue
        r=read(case/'results.json');c=r['conditions'];span=c['span_mm'];h=c['height_mm']
        if not c['external_free_jet']:
            d=np.load(case/'outlet_fields.npz');y=d['centroids'][:,1];u=d['z-velocity'];areas=d['areas']
            means=[];spanareas=[];labels=np.round(y,7)
            for yy in np.unique(labels):
                mask=labels==yy;means.append(np.average(u[mask],weights=areas[mask]));spanareas.append(areas[mask].sum())
            weighted_mean=np.average(means,weights=spanareas)
            long_cv=np.sqrt(np.average((np.array(means)-weighted_mean)**2,weights=spanareas))/weighted_mean
            row={'case':case.name,'height_mm':h,'span_mm':span,'computed_Q_m3_min':r['nozzle_flow_m3_min'],
                'inlet_static_pressure_Pa':r['required_static_pressure_Pa'],'nozzle_total_pressure_loss_Pa':r['pressure_loss_to_domain_outlet_Pa'],
                'gap_averaged_span_CV_pct':100*float(long_cv),
                'internal_reverse_volume_pct':100*r['negative_uz_volume_fraction']}
            bodyrows.append(row);continue
        d=np.load(case/'slot_fields.npz');xy=d['centroids']*1000
        mask=(abs(xy[:,0])<=6.00001)&(abs(xy[:,1])<=span/2+1e-4)
        ar=d['areas'][mask];uz=d['z-velocity'][mask];pt=d['total-pressure'][mask]
        cells=np.load(case/'cell_fields.npz');z=cells['SV_CENTROID'].reshape(-1,3)[:,2];inside=z<h/1000
        stat={'slot_mean_uz_m_s':float(np.average(uz,weights=ar)),
            'slot_mass_average_total_pressure_Pa':float(np.average(pt,weights=ar*np.maximum(uz,0))),
            'internal_negative_uz_volume_fraction':float(cells['SV_VOLUME'][inside&(cells['SV_W']<-.01)].sum()/cells['SV_VOLUME'][inside].sum())}
        stat['nozzle_total_pressure_loss_Pa']=r['reports']['ptin']-stat['slot_mass_average_total_pressure_Pa']
        for distance in [30,50,80]:
            plane=np.load(case/f'plane_{distance}mm_fields.npz');xy=plane['centroids'][:,:2]*1000
            interp=LinearNDInterpolator(xy,plane['z-velocity']);yy=np.linspace(-100,100,101);v=interp(np.c_[yy*0,yy])
            ss=np.linspace(-(span-16)/2,(span-16)/2,121);vv=interp(np.c_[ss*0,ss]);assert np.isfinite(v).all() and np.isfinite(vv).all()
            roi=(abs(xy[:,0])<=40)&(abs(xy[:,1])<=160)
            stat[f'{distance}mm']={'common_200mm_line_mean_Uz_m_s':float(v.mean()),'covered_span_line_length_mm':span-16,
                'covered_span_line_mean_Uz_m_s':float(vv.mean()),'covered_span_line_p10_Uz_m_s':float(np.percentile(vv,10)),
                'covered_span_line_CV_pct':100*float(vv.std()/vv.mean()),
                'forward_momentum_window_N':float(np.sum(1.2*plane['areas'][roi]*np.maximum(plane['z-velocity'][roi],0)**2)),
                'momentum_window_mm':{'X':[-40,40],'Y':[-160,160]}}
            np.savetxt(case/f'profile_{distance}mm.csv',np.c_[ss,vv],delimiter=',',header='Y_mm,Uz_at_X0_m_s',comments='')
        r['free_jet_metrics']=stat;(case/'results.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
        row={'case':case.name,'height_mm':h,'span_mm':span,'hypothetical_inlet_total_pressure_Pa':400,
            'computed_Q_m3_min':r['nozzle_flow_m3_min'],'slot_mean_Uz_m_s':stat['slot_mean_uz_m_s'],
            'nozzle_total_pressure_loss_Pa':stat['nozzle_total_pressure_loss_Pa'],
            'at_80mm_common_200mm_line_mean_Uz_m_s':stat['80mm']['common_200mm_line_mean_Uz_m_s'],
            'at_80mm_covered_span_line_mean_Uz_m_s':stat['80mm']['covered_span_line_mean_Uz_m_s'],
            'at_80mm_covered_span_line_CV_pct':stat['80mm']['covered_span_line_CV_pct'],
            'at_80mm_momentum_window_N':stat['80mm']['forward_momentum_window_N'],
            'internal_reverse_volume_pct':100*stat['internal_negative_uz_volume_fraction']}
        rows.append(row)
        if plots:
            fig,axs=plt.subplots(1,2,figsize=(10,6),layout='constrained')
            for ax,name,axes,label in zip(axs,['long_cut','short_cut'],[[1,2],[0,2]],['Y (mm)','X (mm)']):
                dd=np.load(case/(name+'_fields.npz'));pc=PolyCollection(polyd(dd,axes),array=dd['z-velocity'],cmap='turbo',edgecolors='none',antialiased=False)
                ax.add_collection(pc);ax.autoscale_view();ax.set_aspect('equal');ax.set(xlabel=label,ylabel='Z (mm)')
                ax.axhline(h,color='black',lw=.6)
                for dz in [30,50,80]:ax.axhline(h+dz,color='white',ls='--',lw=.6)
                fig.colorbar(pc,ax=ax,label='Uz (m/s)',shrink=.8)
            fig.suptitle(f'{span:g}×12 mm｜整組長 {h:g} mm｜假設入口總壓 400 Pa\n此條件不代表已量測的風機工作點')
            fig.savefig(case/'flow.png',dpi=150);plt.close(fig)
        print('JET_METRICS',json.dumps(row),flush=True)
    if rows:csvout(ROOT/'jet_comparison.csv',rows)
    if bodyrows:csvout(ROOT/'body_comparison.csv',bodyrows)
    if plots and rows:
        fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
        for row in rows:
            if row['case'].endswith('_fine'):continue
            p=np.loadtxt(ROOT/'cfd'/row['case']/'profile_80mm.csv',delimiter=',',skiprows=1)
            ax.plot(p[:,0],p[:,1],label=f"{row['span_mm']} mm 寬／{row['height_mm']} mm 長")
        ax.set(xlabel='長邊 Y (mm)',ylabel='距出口 80 mm，X=0 的 Uz (m/s)',title='12 mm 出口：工作距離 8 cm 比較\n相同假設總壓 400 Pa，並非實機風量預測')
        ax.legend();ax.grid(alpha=.2);fig.savefig(ROOT/'images/CFD_80mm_profiles.png',dpi=160);plt.close(fig)
    return bodyrows,rows
if __name__=='__main__':
    residuals();metrics()
