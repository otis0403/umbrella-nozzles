"""Scientific plots from actual Fluent exports; no simulated water removal."""
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

def polys(d,axes):
    return [d['vertices'][d['indices'][a:b]][:,axes]*1000 for a,b in zip(d['offsets'][:-1],d['offsets'][1:])]

def analyse_jets():
    rows=[];fig,ax=plt.subplots(figsize=(8,4))
    cases=sorted((ROOT/'cfd').glob('jet_g*'))
    if (ROOT/'cfd'/'jet_check12'/'results.json').exists():cases.append(ROOT/'cfd'/'jet_check12')
    for case in cases:
        if not (case/'results.json').exists():continue
        r=json.loads((case/'results.json').read_text());gap=r['conditions']['gap_mm'];h=r['conditions']['height_mm']
        slot=np.load(case/'slot_fields.npz')
        cc=slot['centroids']*1000;mask=(abs(cc[:,0])<gap/2+1e-4)&(abs(cc[:,1])<108+1e-4)
        weights=slot['areas'][mask]*np.maximum(slot['z-velocity'][mask],0)
        pt=np.average(slot['total-pressure'][mask],weights=weights)
        stats={'slot_mass_average_total_pressure_Pa':float(pt),'nozzle_total_pressure_loss_Pa':float(r['reports']['ptin']-pt),
            'slot_mean_axial_velocity_m_s':float(np.average(slot['z-velocity'][mask],weights=slot['areas'][mask]))}
        cells=np.load(case/'cell_fields.npz');xyz=cells['SV_CENTROID'].reshape(-1,3)
        internal=xyz[:,2]<h/1000
        stats['internal_negative_uz_volume_fraction']=float(cells['SV_VOLUME'][internal&(cells['SV_W']<-.01)].sum()/cells['SV_VOLUME'][internal].sum())
        stats['internal_min_uz_m_s']=float(cells['SV_W'][internal].min())
        for distance in [30,50,80]:
            d=np.load(case/f'plane_{distance}mm_fields.npz');c=d['centroids']*1000
            interp=LinearNDInterpolator(c[:,:2],d['z-velocity'])
            yy=np.linspace(-100,100,101);v=np.asarray(interp(np.c_[np.zeros(len(yy)),yy]))
            assert np.isfinite(v).all()
            roi=(abs(c[:,0])<=40)&(abs(c[:,1])<=130)
            momentum=float(np.sum(1.2*d['areas'][roi]*np.maximum(d['z-velocity'][roi],0)**2))
            stats[f'{distance}mm']={'central_200mm_line_mean_uz_m_s':float(v.mean()),
                'central_200mm_line_p10_uz_m_s':float(np.percentile(v,10)),
                'central_200mm_line_CV':float(v.std()/v.mean()),'forward_momentum_window_N':momentum,
                'momentum_window_mm':{'X':[-40,40],'Y':[-130,130]}}
            np.savetxt(case/f'profile_{distance}mm.csv',np.c_[yy,v],delimiter=',',header='Y_mm,Uz_at_X0_m_s',comments='')
            if distance==80 and case.name!='jet_check12':ax.plot(yy,v,label=f'{gap:g} mm 刀口')
        r['free_jet_metrics']=stats;(case/'results.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
        row={'gap_mm':gap,'hypothetical_total_pressure_Pa':400,
            'computed_nozzle_flow_m3_min':r['nozzle_flow_m3_min'],'slot_uz_m_s':stats['slot_mean_axial_velocity_m_s'],
            'at_30mm_mean_uz_m_s':stats['30mm']['central_200mm_line_mean_uz_m_s'],
            'at_50mm_mean_uz_m_s':stats['50mm']['central_200mm_line_mean_uz_m_s'],
            'at_80mm_mean_uz_m_s':stats['80mm']['central_200mm_line_mean_uz_m_s'],
            'at_80mm_momentum_N':stats['80mm']['forward_momentum_window_N'],
            'internal_reverse_volume_fraction':stats['internal_negative_uz_volume_fraction']}
        if case.name!='jet_check12':rows.append(row)
        f,axs=plt.subplots(1,2,figsize=(11,6),width_ratios=[2.3,1],layout='constrained')
        for a,name,axes,label in zip(axs,['long_cut','short_cut'],[[1,2],[0,2]],['長邊 Y (mm)','短邊 X (mm)']):
            d=np.load(case/(name+'_fields.npz'))
            pc=PolyCollection(polys(d,axes),array=d['z-velocity'],cmap='turbo',edgecolors='none',antialiased=False)
            a.add_collection(pc);a.autoscale_view();a.set_aspect('equal');a.set_xlabel(label);a.set_ylabel('流向 Z (mm)')
            for dis in [30,50,80]:a.axhline(h+dis,c='white',lw=.7,ls='--')
            a.axhline(h,c='black',lw=.7)
            f.colorbar(pc,ax=a,label='軸向速度 Uz (m/s)',shrink=.8)
        f.suptitle(f'{gap:g} mm 刀口 | 入口總壓假設 400 Pa | 含外部自由噴流\n此壓力條件不代表已確認的風機工作點')
        f.savefig(case/'flow_with_free_jet.png',dpi=170);plt.close(f)
        d=np.load(case/'plane_80mm_fields.npz')
        f,a=plt.subplots(figsize=(9,4),layout='constrained')
        pc=PolyCollection(polys(d,[1,0]),array=d['z-velocity'],cmap='turbo',edgecolors='none',antialiased=False)
        a.add_collection(pc);a.set(xlim=(-130,130),ylim=(-40,40),xlabel='長邊 Y (mm)',ylabel='短邊 X (mm)',
            title=f'距離出口 80 mm 的自由氣流 | {gap:g} mm 刀口 | 總壓假設 400 Pa')
        a.set_aspect('equal');f.colorbar(pc,ax=a,label='Uz (m/s)');f.savefig(case/'plane_80mm.png',dpi=170);plt.close(f)
    ax.set(xlabel='長邊 Y (mm)',ylabel='距離出口 80 mm、X=0 的軸向速度 (m/s)',
        title='工作距離 8 公分：三種刀口比較\n相同入口總壓假設 400 Pa；並非本機風量預測')
    ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(ROOT/'images'/'jet_80mm_comparison.png',dpi=170);plt.close(fig)
    if rows:
        with (ROOT/'free_jet_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=rows[0]);wr.writeheader();wr.writerows(rows)
    print(json.dumps(rows,indent=2),flush=True)

def convergence():
    pat=re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+')
    for logname in ['body_study.log','jet_study.log','jet_check.log']:
        if not (ROOT/logname).exists():continue
        raw=(ROOT/logname).read_bytes();text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
        records=[]
        for line in text.splitlines():
            match=pat.match(line)
            if match:records.append([int(match[1])]+[float(x) for x in match[2].split()])
            if 'CASE_COMPLETE ' in line:
                name=line.split('CASE_COMPLETE ',1)[1].split()[0]
                case=ROOT/'cfd'/name;r=json.loads((case/'results.json').read_text())
                hist=json.loads((case/'history.json').read_text())
                last=records[-1];deltaq=100*abs(hist[-1]['min']-hist[-2]['min'])/abs(hist[-1]['min'])
                checks={'last_iteration':last[0],'last_residuals':dict(zip(['continuity','Ux','Uy','Uz','k','omega'],last[1:])),
                    'last_flow_change_pct':deltaq,'last_inlet_pressure_change_pct':r['last_pressure_change_pct'],
                    'mass_imbalance_pct':r['mass_imbalance_pct'],
                    'engineering_convergence_pass':last[1]<1e-4 and max(last[2:5])<1e-6 and max(last[5:])<1e-5
                        and deltaq<.5 and r['last_pressure_change_pct']<.5 and r['mass_imbalance_pct']<.1,
                    'strict_all_residuals_below_1e_minus_5':max(last[1:])<1e-5,
                    'criteria':{'continuity':1e-4,'velocity':1e-6,'k_omega':1e-5,'pressure_and_flow_stability_pct':.5,'mass_imbalance_pct':.1}}
                (case/'convergence.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
                np.savetxt(case/'residual_history.csv',np.array(records),delimiter=',',header='iteration,continuity,Ux,Uy,Uz,k,omega',comments='')
                print('CONVERGENCE',name,checks['engineering_convergence_pass'],checks['last_residuals'],flush=True)
                records=[]

if __name__=='__main__':
    convergence();analyse_jets()
