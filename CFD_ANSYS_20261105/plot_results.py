"""Render exported Fluent polygon fields without bridging solid walls."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.font_manager import fontManager
from session import ROOT

fontManager.addfont(r'C:\Windows\Fonts\msjh.ttc')
plt.rcParams.update({'font.family':'Microsoft JhengHei','axes.unicode_minus':False,'figure.dpi':150})

def polygons(d,axes):
    vertices=d['vertices'][:,axes]*1000
    ix=d['connectivity'];off=d['offsets']
    return [vertices[ix[off[k]:off[k+1]]] for k in range(len(off)-1)]

def profile(d):
    # Each outlet U column has a constant Y centroid; integrate through the gap.
    y=d['face_centroids'][:,1]*1000
    key=np.round(y,7)
    yy=np.unique(key)
    avg=np.array([np.average(d['z-velocity'][key==v],weights=d['areas_m2'][key==v]) for v in yy])
    return yy,avg

def main():
    rows=[]
    cases=sorted(p.parent for p in ROOT.glob('medium/Q*/results.json'))
    if not cases: cases=sorted(p.parent for p in ROOT.glob('coarse/Q*/results.json'))
    if any(ROOT.glob('medium/Q*/results.json')):
        cases+=sorted(p.parent for p in ROOT.glob('fine/Q*/results.json'))
    fig,ax=plt.subplots(figsize=(8,4))
    for case in cases:
        q=json.loads((case/'conditions.json').read_text())['flow_m3_min']
        r=json.loads((case/'results.json').read_text())
        d=np.load(case/'outlet_fields.npz')
        yy,avg=profile(d)
        comparison_case=case.parent.name!='fine'
        if comparison_case: ax.plot(yy,avg,label=f'{q:g} m³/min')
        xs=np.linspace(-108,108,61)
        # Endpoint zero comes from the no-slip side wall, interior linear interpolation.
        vals=np.interp(xs,np.r_[-108,yy,108],np.r_[0,avg,0])
        np.savetxt(case/'outlet_long_axis_61_samples.csv',np.c_[xs,vals],delimiter=',',
                   header='y_mm,gap_averaged_axial_velocity_m_s_interpolated',comments='')
        area=d['areas_m2'];n=len(yy)
        col_area=np.array([area[np.round(d['face_centroids'][:,1]*1000,7)==v].sum() for v in yy])
        mean=np.average(avg,weights=col_area)
        r['outlet_gap_averaged_long_axis_CV']=float(np.sqrt(np.average((avg-mean)**2,weights=col_area))/mean)
        r['outlet_gap_averaged_peak_mean_ratio']=float(avg.max()/mean)
        (case/'results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        row={'Q_m3_min':q,'inlet_static_Pa':r['required_inlet_static_pressure_Pa'],
                     'total_pressure_loss_Pa':r['total_pressure_loss_Pa'],'outlet_mean_uz_m_s':float(mean),
                     'outlet_full_area_CV':r['outlet_area_weighted_CV'],
                     'outlet_long_axis_CV':r['outlet_gap_averaged_long_axis_CV'],
                     'reverse_volume_fraction_Uz_lt_minus_0p01_m_s':r.get('reverse_volume_fraction_below_minus_0.01_m_s'),
                     'mass_imbalance_pct':r['mass_imbalance_pct']}
        if comparison_case: rows.append(row)
        for field,label,filename in [('z-velocity','軸向速度 (m/s)','velocity_cuts.png'),
                                     ('pressure','靜壓 (Pa)','pressure_cuts.png')]:
            fg,axs=plt.subplots(1,2,figsize=(10,7),width_ratios=[2.5,1],layout='constrained')
            for a,name,axes,xlabel in zip(axs,['long_cut','short_cut'],[[1,2],[0,2]],['長邊方向 Y (mm)','短邊方向 X (mm)']):
                dd=np.load(case/(name+'_fields.npz'))
                vals=dd[field]
                pc=PolyCollection(polygons(dd,axes),array=vals,cmap='turbo',edgecolors='none',rasterized=True,antialiased=False)
                a.add_collection(pc);a.autoscale_view();a.set_aspect('equal')
                a.set_xlabel(xlabel);a.set_ylabel('流向 Z (mm)')
                a.set_title('X = 3 mm 切面' if name=='long_cut' else 'Y = 3 mm 切面')
                fg.colorbar(pc,ax=a,label=label,shrink=.7)
                if field=='z-velocity':
                    cent=dd['face_centroids']*1000
                    bad=vals<-.01
                    if bad.any(): a.scatter(cent[bad,axes[0]],cent[bad,2],s=2,c='magenta',label='Uz < -0.01 m/s')
                    sel=np.arange(0,len(vals),max(1,len(vals)//180))
                    sel=sel[(cent[sel,2]>5)&(cent[sel,2]<190)]
                    vec=dd['y-velocity'] if name=='long_cut' else dd['x-velocity']
                    norm=np.maximum(np.hypot(vec[sel],vals[sel]),1e-12)
                    a.quiver(cent[sel,axes[0]],cent[sel,2],vec[sel]/norm,vals[sel]/norm,
                             width=.003,scale=30,color='black',alpha=.55)
            fg.suptitle(f'Fluent SST | Q = {q:g} m³/min | 無核心、保留十字導流片')
            fg.savefig(case/filename,dpi=180);plt.close(fg)
        fg,a=plt.subplots(figsize=(11,2.6),layout='constrained')
        pc=PolyCollection(polygons(d,[1,0]),array=d['z-velocity'],cmap='turbo',edgecolors='none')
        a.add_collection(pc);a.autoscale_view();a.set_aspect('equal')
        a.set_xlabel('長邊 Y (mm)');a.set_ylabel('縫寬 X (mm)')
        a.set_title(f'216 × 12 mm 出口軸向速度 | Q={q:g} m³/min')
        fg.colorbar(pc,ax=a,label='Uz (m/s)',orientation='horizontal',shrink=.7,pad=.5)
        fg.savefig(case/'outlet_distribution.png',dpi=180);plt.close(fg)
        cell=np.load(case/'cell_fields.npz')
        cc=cell['SV_CENTROID'].reshape(-1,3)*1000
        uz=cell['SV_W'];vv=cell['SV_VOLUME'];mask=uz<-.01
        np.savetxt(case/'reverse_cells_Uz_lt_minus_0p01_m_s.csv',np.c_[cc[mask],uz[mask],vv[mask]],delimiter=',',
                   header='x_mm,y_mm,z_mm,uz_m_s,cell_volume_m3',comments='')
        fg,axs=plt.subplots(2,1,figsize=(9,7),layout='constrained')
        for a,ylim,title in zip(axs,[(-2,202),(130,150)],['全流道投影（包含入口附近）','導流片尾端放大']):
            if mask.any():
                sc=a.scatter(cc[mask,1],cc[mask,2],c=uz[mask],cmap='coolwarm',s=15,edgecolors='black',linewidths=.2)
                fg.colorbar(sc,ax=a,label='倒流單元 Uz (m/s)')
            a.axhline(134,c='gray',ls='--',label='短片尾端 Z=134 mm')
            a.axhline(144,c='black',ls=':',label='長片尾端 Z=144 mm')
            a.set(xlim=(-110,110),ylim=ylim,xlabel='長邊方向 Y (mm)',ylabel='流向 Z (mm)',title=title)
            a.legend(loc='lower center',fontsize=8)
        fg.suptitle(f'倒流單元投影（非切面）| Q={q:g} m³/min\nUz < -0.01 m/s 的體積占比 {100*vv[mask].sum()/vv.sum():.6f}%')
        fg.savefig(case/'recirculation_locations.png',dpi=180);plt.close(fg)
    ax.set(xlabel='出口長邊 Y (mm)',ylabel='跨 12 mm 縫寬平均的軸向速度 (m/s)',
           title='216 × 12 mm 無核心吹嘴：出口長邊速度分布')
    ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(ROOT/'outlet_profiles.png',dpi=180);plt.close(fig)
    if rows:
        with (ROOT/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
        print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
