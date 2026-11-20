"""Mixed-gap prototype package; numerical scenarios are never fan measurements."""
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from design import ROOT,write_json

BASE=ROOT.parent/'Nozzles_225_180_315_G16_ANSYS_20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert read(ROOT/'pipeline_state.json')['phase']=='new_CFD_and_native_readback_complete_models_report_pending'
selection=read(ROOT/'selection.json');gap=selection['outer']['gap_mm']
OUT=ROOT.parent/'集風罩'/f'三尺寸吹嘴_外側收窄_225x16_180x16_315x{gap}_20261117'
OUT.mkdir(parents=True,exist_ok=True)
font=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=11)
def copy(src,rel):
    dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);return dst
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def csv_save(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

geometry=read(ROOT/'cad/selected_STL_checks.json');native_geometry=read(ROOT/'cad/native_geometry_checks.json')
assert len(geometry)==3 and native_geometry['native_reopened']
dimensions=[]
for i,(key,label) in enumerate([('inner','內側'),('center','中間'),('outer','外側')]):
    spec=selection[key];w=spec['width_mm'];g=spec['gap_mm'];L=spec['length_mm'];h=spec['height_mm']
    suffix='_guided' if key=='outer' else ''
    src=ROOT/'cad/full'/f'nozzle_W{w}_G{g}_L{L}_ramp{suffix}_mm.stl'
    dst=copy(src,Path('STL_完整件')/f'{label}_{w}x{g}_總長{h}_mm.stl')
    checked=geometry[i]
    assert checked['sha256']==hashlib.sha256(dst.read_bytes()).hexdigest()
    measured=next(row for row in native_geometry['records'] if abs(row['width_mm']-w)<.03)
    assert measured['gap_mm']==g and max(abs(v-g) for v in measured['gap_range_mm'])<.03
    if key!='outer':assert hashlib.sha256(src.read_bytes()).hexdigest()==hashlib.sha256((BASE/'cad/full'/src.name).read_bytes()).hexdigest()
    dimensions.append([label,f'{w} × {g}',h,f"{checked['size_mm'][1]:.1f} × {checked['size_mm'][0]:.1f} × {h}",2 if key=='outer' else 0])
copy(ROOT/'cad/three_complete_nozzles_horizontal.blend','CAD/三尺寸完整吹嘴_外側收窄_水平配置.blend')
for filename in ['CAD_three_nozzles_horizontal.png','CAD_315_guide_cutaway.png','three_nozzles_dimensions.png']:
    copy(ROOT/'images'/filename,Path('圖片')/filename)
for p in [ROOT/'cad/selected_STL_checks.json',ROOT/'cad/native_geometry_checks.json',ROOT/'native_cfd_readback.json',
          ROOT/'convergence_summary.json',ROOT/'candidate_review.json',ROOT/'selected_pressure_curves.json',ROOT/'selection.json']:
    copy(p,Path('檢查紀錄')/p.name)
copy(BASE/'native_cfd_readback.json','檢查紀錄/原16mm版_原生CFD重讀.json')
copy(BASE/'convergence_summary.json','檢查紀錄/原16mm版_收斂紀錄.json')

before=[read(BASE/'cfd'/f'network_Ps460_hose{length}'/'results.json') for length in [60,50]]
after=[read(ROOT/'cfd'/f'network_narrow_Ps460_hose{length}'/'results.json') for length in [60,50]]
points=read(ROOT/'selected_pressure_curves.json')['315']['points']
lo=min(p['Q_m3_min'] for p in points);hi=max(p['Q_m3_min'] for p in points)
for r in after:assert lo-.005<=r['branch_flow_m3_min'][2]<=hi+.005
assert after[0]['slot_area_mean_velocity_m_s'][2]>before[0]['slot_area_mean_velocity_m_s'][2]
flow_rows=[]
for label,results in [('原外側16mm',before),(f'新外側{gap}mm',after)]:
    for r in results:
        for k,pos in enumerate(['內側','中間','外側']):
            flow_rows.append({'version':label,'case':r['name'],'position':pos,'width_mm':[225,180,315][k],
                              'gap_mm':16 if label=='原外側16mm' or k<2 else gap,
                              'hose_cut_length_m':r['pipe_cut_lengths_m'][k],'branch_flow_m3_min':r['branch_flow_m3_min'][k],
                              'slot_mean_velocity_m_s':r['slot_area_mean_velocity_m_s'][k],'group_total_flow_m3_min':r['total_flow_m3_min'],
                              'actual_inlet_static_Pa':r['reports']['pin'],'hypothetical_static_target_Pa':460,
                              'load_error_pct':r['load_consistency_error_pct'][k],'measured_fan_point':False})
csv_save('新舊三路風量與風速_條件估算.csv',flow_rows)
candidate_cases=['control_g16_q3','candidate_g10_q3','candidate_g8_q3']
candidate_metrics=[read(ROOT/'cfd'/case/'profile_metrics.json') for case in candidate_cases]
csv_save('16_10_8mm_相同指定風量比較.csv',candidate_metrics)
conv=read(ROOT/'convergence_summary.json')
for case in candidate_cases+[f'selected_g{gap}_q2']+[r['name'] for r in after]:
    for filename in ['results.json','history.json','profile_metrics.json','mesh_summary.json','outlet_centerline.csv']:
        src=ROOT/'cfd'/case/filename
        if src.exists():copy(src,Path('ANSYS數值紀錄')/case/filename)

fig,axs=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
for ax,field,ylabel in zip(axs,['branch_flow_m3_min','slot_area_mean_velocity_m_s'],['每路風量（m³/min）','出口平均風速（m/s）']):
    x=np.arange(3)
    for j,(label,r) in enumerate([('原外側 16 mm',before[0]),(f'新外側 {gap} mm',after[0])]):
        bars=ax.bar(x+(j-.5)*.34,r[field],width=.32,label=label,color=['#aacbd2','#197f95'][j])
        ax.bar_label(bars,fmt='%.2f',fontsize=9)
    ax.set_xticks(x,['內側 225','中間 180','外側 315'],fontproperties=font)
    ax.set_ylabel(ylabel,fontproperties=font)
    ax.set_ylim(top=max(max(before[0][field]),max(after[0][field]))*1.35)
    ax.legend(prop=font,loc='upper left')
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
fig.suptitle('一組三路｜三管裁切長 60 cm，假設入口靜壓約 460 Pa，非實測風機工作點',fontproperties=font)
fig.savefig(OUT/'圖片/新舊三路風量風速比較.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,4.7),layout='constrained')
maximum_profile=0
for case,color in zip(candidate_cases,['#999999','#c07a32','#197f95']):
    d=np.loadtxt(ROOT/'cfd'/case/'outlet_centerline.csv',delimiter=',',skiprows=1)
    maximum_profile=max(maximum_profile,float(d[:,1].max()))
    g=read(ROOT/'cfd'/case/'results.json')['conditions']['gap_mm']
    ax.plot(d[:,0],d[:,1],label=f'{g:g} mm',color=color,lw=1.7)
ax.set_xlabel('沿 315 mm 長邊的位置（mm）',fontproperties=font);ax.set_ylabel('出口中央線軸向風速（m/s）',fontproperties=font)
ax.set_title('各自指定相同 3.024 m³/min 的形狀比較；此圖不是三路實際工作風量',fontproperties=font)
ax.set_ylim(top=maximum_profile*1.3)
ax.legend(prop=font,loc='upper left');ax.grid(alpha=.2)
fig.savefig(OUT/'圖片/外側16_10_8mm_指定流量風速分布.png',dpi=170);plt.close(fig)

comparison=[]
for k,label in enumerate(['內側','中間','外側']):
    comparison.append([label,f"{[225,180,315][k]} × {gap if k==2 else 16}",
                       f"{before[0]['branch_flow_m3_min'][k]:.3f}",f"{after[0]['branch_flow_m3_min'][k]:.3f}",
                       f"{before[0]['slot_area_mean_velocity_m_s'][k]:.2f}",f"{after[0]['slot_area_mean_velocity_m_s'][k]:.2f}"])
head_rows=[]
for m in candidate_metrics:
    head_rows.append([f"{m['gap_mm']:g}",f"{m['flow_m3_min']:.3f}",f"{m['inlet_total_pressure_Pa']:.1f}",
                      f"{m['total_pressure_loss_Pa']:.1f}",f"{m['core_line_CV_pct']:.1f}%",f"{m['body_reverse_volume_pct']:.1f}%",
                      '通過' if m['engineering_convergence_pass'] else '未全通過'])
pipe_rows=[]
for b,a in zip(before,after):
    pipe_rows.append([f"{a['pipe_cut_lengths_m'][0]*100:.0f}",f"{b['total_flow_m3_min']:.3f}",f"{a['total_flow_m3_min']:.3f}",
                      f"{b['slot_area_mean_velocity_m_s'][2]:.2f}",f"{a['slot_area_mean_velocity_m_s'][2]:.2f}",f"{a['reports']['pin']:.1f}"])
network_status=[]
for a in after:
    network_status.append([a['name'],f"{max(a['load_consistency_error_pct']):.3f}%",f"{a['mass_imbalance_pct']:.5f}%",
                           '通過' if conv.get(a['name'],{}).get('engineering_convergence_pass',False) else '未全通過'])
gain=100*(after[0]['slot_area_mean_velocity_m_s'][2]/before[0]['slot_area_mean_velocity_m_s'][2]-1)
qchange=100*(after[0]['branch_flow_m3_min'][2]/before[0]['branch_flow_m3_min'][2]-1)
total_change=100*(after[0]['total_flow_m3_min']/before[0]['total_flow_m3_min']-1)
stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M UTC+8')
report=f'''# 外側吹嘴收窄：維持 51 mm 管路

資料整理：{stamp}。依最新選擇，只允許外側出口間隙縮小。內側225×16、中間180×16維持；外側比較315×16、315×10、315×8後選用 **315×{gap} mm**。這次另存完整件，未以 K1C 容量限制尺寸，也未切分；既有外殼、分流接頭和管徑都未改造。

## 主要結果

在三條裁切長60cm、入口靜壓假設約460Pa的同一情境下，外側出口面積平均風速由 **{before[0]['slot_area_mean_velocity_m_s'][2]:.2f} 提高到 {after[0]['slot_area_mean_velocity_m_s'][2]:.2f} m/s（{gain:+.1f}%）**。外側風量變化 {qchange:+.1f}%，單組總風量變化 {total_change:+.1f}%。縮口使風量改變，以下比較已把這項影響納入。

{table(['位置','新版淨出口 mm','原風量 m³/min','新風量 m³/min','原平均風速 m/s','新平均風速 m/s'],comparison)}

以上均為單台鼓風機的一組三路，不是實測風機工作點。風機規格330W、11m³/min、460Pa尚缺完整P–Q曲線，無法據標示確定組裝後的實際風量。實際風機壓力隨總風量改變時，各路也會跟著改變。

![新舊條件比較](圖片/新舊三路風量風速比較.png)

## 完整件尺寸與接口

{table(['位置','淨出口 mm','軸向總長 mm','包絡 寬×厚×長 mm','導流片數'],dimensions)}

三者承口內徑仍為55.4mm、插入25mm，內流道51mm，沿用原R90接頭外徑55mm的插口。若直接套軟管，55.4mm承口是依先前估計軟管外徑54.6mm留隙；這兩種實物套合皆尚未驗證。名義殼厚2.4mm、出口唇部約2mm。外側兩片1.6mm導流片保留，前後端0.8mm，入口座標Z55到332mm，出口前56mm仍連通，中央軸線無阻塞。

內側與中間STL雜湊與前版一致。Blender內出風方向水平，寬面與地面平行；此檔為獨立吹嘴配置，尚未核對新長度在整機內的安裝碰撞、固定支撐或管路走向。

![三個完整件](圖片/CAD_three_nozzles_horizontal.png)
![尺寸](圖片/three_nozzles_dimensions.png)
![外側內部剖視](圖片/CAD_315_guide_cutaway.png)

## ANSYS 比較方式

Fluent2026R1、3D雙精度、定常不可壓縮空氣，密度1.2kg/m³、黏度1.8e-5Pa·s、SST k–ω，光滑無滑移壁，入口紊流強度5%。三個外側間隙使用相同網格拓撲與單元數，僅末端截面隨間隙縮放；這不是網格獨立性驗證。每個模型包含內徑51mm、中心線半徑90mm的上方進氣彎管，出口截面設大氣壓。未模擬外部射流與傘面。

先在指定Q=3.024m³/min下直接比較三種形狀；下表速度分布指標不能當作相同風機會自行產生的工作點。

{table(['外側間隙 mm','指定Q m³/min','所需入口總壓 Pa','彎管＋嘴總壓損 Pa','中央線CV','局部負軸速體積占比','方程收斂'],head_rows)}

CV沿出口厚度中央量測，長邊兩端各略去5mm。局部負軸速體積占比只統計吹嘴本體內軸向速度低於-0.01m/s的流體體積，不是鼓風機回流量或入口倒灌率。入口總壓與總壓損是不同物理量。

![相同指定風量的分布](圖片/外側16_10_8mm_指定流量風速分布.png)

初步候選排序使用單點阻力修正，最後選定版另算Q=2.000及3.024m³/min兩點，再擬合非負 `P_total=aQ²+bQ`，用於三路負載耦合。新版兩種管長的外側風量均落在這兩點範圍內。兩點擬合的誤差不能視為實物精度；原始壓力、末段振盪範圍及係數保留於檢查紀錄。內側、中間曲線沿用前版已重讀驗證的原生Fluent結果。

## 管長與分流計算

現有分流器的流體模型沿用82×88mm入口、三路ID46mm及中央插管比兩側長10mm的形狀。新吹嘴及R90上彎、軟管、下彎、接口負載一起計入，再迭代各路風量與壓力匹配。軟管ID51mm；裁切長扣除兩端插入共50mm；Darcy摩擦係數假設0.04，下彎K=0.5，接口K=0.15（以ID46速度計）。皺褶、實際彎曲與漏氣尚未量測。

{table(['三管裁切長 cm','原單組總Q','新單組總Q','原外側 m/s','新外側 m/s','新版實得入口靜壓 Pa'],pipe_rows)}

Q單位m³/min。50、60cm兩列都假設入口靜壓460Pa，方便比較管長。風機渦殼出口偏流、葉輪、失速及入口倒灌未建模。前版另做的強制總Q11m³/min試驗只反算所需壓力，不能當成風機實際流量；新版也不預設總Q為11。

## 驗證與限制

{table(['新版三路案例','最大下游負載誤差','質量不平衡','完整方程收斂'],network_status)}

完整方程門檻包含連續性1e-4、各速度1e-6、k與ω各1e-5、質量平衡及末段壓力變化。任何未全通過的案例均保留為定常原型估算，不能視為完整驗證。負載匹配通過僅代表三路截斷模型與下游阻力一致，不代表所有方程收斂。

新案例原生case/data已在新Fluent程序重讀，重新計算報表並核對正單元體積。STL已獨立重讀確認封閉網格、單一連通實體、正體積、面方向及非退化面；Blender重開後核對每嘴61點縫寬、淨長、承口內徑與中央通道。未做網格獨立性、瞬態統計、真實風機工作點、外部射流、列印、套管、整機安裝與乾燥時間驗證。依先前選擇交付原型與列明未達標項目的報告。

縮窄後應以相同風機轉速、管路、距離實測沿315mm長邊的風速分布、入口倒灌、脈動及乾燥時間，不能只比較中央最高風速。取得P–Q曲線或實測靜壓/總流量後，才能更新為實際工作點。

## 檔案

- `STL_完整件`：三個完整mm STL，未切分；`CAD`為Blender完整模型。
- `新舊三路風量與風速_條件估算.csv`：前後版、兩種管長、各路風量與面積平均風速。
- `16_10_8mm_相同指定風量比較.csv`：三種外側截面的直接CFD比較。
- `ANSYS數值紀錄`與`檢查紀錄`：結果、歷程、曲線與原生檔重讀。
- `來源程式`供核對幾何與算法；重跑需保留本工作資料夾及前版來源的目錄結構，並使用既有Python/Fluent環境。
'''
(OUT/'設計與ANSYS報告.md').write_text(report,encoding='utf-8')
for p in ROOT.glob('*.py'):copy(p,Path('來源程式')/p.name)
for p in ROOT.glob('stage_*.json'):copy(p,Path('來源程式')/p.name)
model_zip=OUT/'三尺寸完整吹嘴_外側收窄_模型與報告.zip'
files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='MANIFEST.sha256']
with zipfile.ZipFile(model_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in sorted(files):z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(model_zip) as z:
    assert z.testzip() is None and len([p for p in z.namelist() if p.startswith('STL_完整件/')])==3
native_zip=OUT/'ANSYS主要案例_case_data.zip'
native_cases=[(BASE,selection[k]['case']) for k in ['inner','center']]+[(ROOT,p['case']) for p in points]+[(ROOT,r['name']) for r in after]
with zipfile.ZipFile(native_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for source,case in native_cases:
        for filename in ['solution.cas.h5','solution.dat.h5']:z.write(source/'cfd'/case/filename,Path(case)/filename)
with zipfile.ZipFile(native_zip) as z:assert z.testzip() is None
manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(OUT).as_posix()
                   for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.sha256')
(OUT/'MANIFEST.sha256').write_text(manifest+'\n',encoding='utf-8')
write_json(ROOT/'DELIVERY_COMPLETE.json',{'delivery':str(OUT),'gap_mm':gap,'model_zip':str(model_zip),'native_zip':str(native_zip),
                                         'baseline_outer_speed_m_s':before[0]['slot_area_mean_velocity_m_s'][2],
                                         'new_outer_speed_m_s':after[0]['slot_area_mean_velocity_m_s'][2],'gain_pct':gain,
                                         'prototype_limitations_disclosed':True,'actual_fan_point_verified':False,'file_count':len(files)})
print('NARROW_DELIVERY_COMPLETE',str(OUT),flush=True)
