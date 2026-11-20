"""Matched reference/candidate CFD and complete prototype package."""
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

PRIOR=ROOT.parent/'Outer315_NarrowGap_ANSYS_20261117'
HEADS=ROOT.parent/'Nozzles_225_180_315_G16_ANSYS_20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert read(ROOT/'pipeline_state.json')['phase']=='CFD_and_native_readback_complete_models_report_pending'
OUT=ROOT.parent/'集風罩'/'三尺寸吹嘴_225x12_180x14_315x8_ANSYS_20261117'
OUT.mkdir(parents=True,exist_ok=True)
selection=read(ROOT/'selection.json');curves=read(ROOT/'selected_pressure_curves.json')
font=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=11)
def copy(src,rel):
    dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);return dst
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def save_csv(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

geometry=read(ROOT/'cad/selected_STL_checks.json');native_geometry=read(ROOT/'cad/native_geometry_checks.json')
assert native_geometry['native_reopened'] and len(geometry)==3
dimensions=[]
for key,label,checked in zip(['inner','center','outer'],['內側','中間','外側'],geometry):
    spec=selection[key];w=spec['width_mm'];g=spec['gap_mm'];L=spec['length_mm'];h=spec['height_mm']
    suffix='_guided' if key=='outer' else ''
    source=ROOT/'cad/full'/f'nozzle_W{w}_G{g}_L{L}_ramp{suffix}_mm.stl'
    target=copy(source,Path('STL_完整件')/f'{label}_{w}x{g}_總長{h}_mm.stl')
    assert hashlib.sha256(target.read_bytes()).hexdigest()==checked['sha256']
    measured=next(row for row in native_geometry['records'] if abs(row['width_mm']-w)<.03)
    assert measured['gap_mm']==g and max(abs(v-g) for v in measured['gap_range_mm'])<.03
    dimensions.append([label,f'{w} × {g}',h,f"{checked['size_mm'][1]:.1f} × {checked['size_mm'][0]:.1f} × {h}",2 if key=='outer' else 0])
copy(ROOT/'cad/three_complete_nozzles_horizontal.blend','CAD/三尺寸完整吹嘴_12_14_8mm_水平配置.blend')
for name in ['CAD_three_nozzles_horizontal.png','CAD_315_guide_cutaway.png','three_nozzles_dimensions.png']:
    copy(ROOT/'images'/name,Path('圖片')/name)
for p in [ROOT/'cad/selected_STL_checks.json',ROOT/'cad/native_geometry_checks.json',ROOT/'native_cfd_readback.json',
          ROOT/'convergence_summary.json',ROOT/'selected_pressure_curves.json',ROOT/'baseline_pressure_curves.json',ROOT/'selection.json']:
    copy(p,Path('檢查紀錄')/p.name)
copy(PRIOR/'native_cfd_readback.json','檢查紀錄/外側8mm_前次原生重讀.json')
copy(PRIOR/'convergence_summary.json','檢查紀錄/外側8mm_前次收斂紀錄.json')

reference=[read(ROOT/'cfd'/f'reference_16_16_8_hose{length}'/'results.json') for length in [60,50]]
candidate=[read(ROOT/'cfd'/f'candidate_12_14_8_hose{length}'/'results.json') for length in [60,50]]
for result in reference+candidate:
    assert result['network_load_consistency_pass'] and result['network_three_stable_batches_pass']
    assert abs(result['reports']['pin']-460)/460*100<.1
for result in candidate:
    for i,width in enumerate([225,180,315]):
        qs=[p['Q_m3_min'] for p in curves[str(width)]['points']]
        assert min(qs)-.005<=result['branch_flow_m3_min'][i]<=max(qs)+.005
rows=[]
for version,results in [('16/16/8參考',reference),('12/14/8候選',candidate)]:
    for r in results:
        for i,pos in enumerate(['內側','中間','外側']):
            rows.append({'version':version,'case':r['name'],'position':pos,'width_mm':[225,180,315][i],
                         'gap_mm':r['branch_gaps_mm'][i],'hose_cut_length_m':r['pipe_cut_lengths_m'][i],
                         'flow_m3_min':r['branch_flow_m3_min'][i],'slot_area_mean_velocity_m_s':r['slot_area_mean_velocity_m_s'][i],
                         'total_group_flow_m3_min':r['total_flow_m3_min'],'target_inlet_static_Pa':460,
                         'actual_inlet_static_Pa':r['reports']['pin'],'load_error_pct':r['load_consistency_error_pct'][i],
                         'actual_fan_operating_point_verified':False})
save_csv('三路風量風速_同條件ANSYS比較.csv',rows)
head_cases=[p.parent.name for p in (ROOT/'cfd').glob('*/completed_checkpoint.json') if p.parent.name.startswith(('inner','center'))]
head_metrics=[read(ROOT/'cfd'/case/'profile_metrics.json') for case in head_cases]
save_csv('新吹嘴指定流量_壓損分布與逆向區域.csv',head_metrics)
all_cases=head_cases+[r['name'] for r in reference+candidate]
for case in all_cases:
    for name in ['results.json','history.json','profile_metrics.json','mesh_summary.json','outlet_centerline.csv']:
        src=ROOT/'cfd'/case/name
        if src.exists():copy(src,Path('ANSYS數值紀錄')/case/name)

fig,axs=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
for ax,field,label in zip(axs,['branch_flow_m3_min','slot_area_mean_velocity_m_s'],['每路風量（m³/min）','出口面積平均風速（m/s）']):
    xx=np.arange(3)
    for j,(tag,r) in enumerate([('16 / 16 / 8 mm',reference[0]),('12 / 14 / 8 mm',candidate[0])]):
        bars=ax.bar(xx+(j-.5)*.34,r[field],width=.32,label=tag,color=['#aacbd2','#197f95'][j])
        ax.bar_label(bars,fmt='%.2f',fontsize=9)
    ax.set_xticks(xx,['內側 225','中間 180','外側 315'],fontproperties=font)
    ax.set_ylabel(label,fontproperties=font)
    ax.set_ylim(top=max(max(reference[0][field]),max(candidate[0][field]))*1.35)
    ax.legend(prop=font,loc='upper left');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
fig.suptitle('ANSYS 一組三路｜相同入口靜壓約460 Pa、每管裁切長60 cm，非實測風機工作點',fontproperties=font)
fig.savefig(OUT/'圖片/同條件三路風量風速比較.png',dpi=170);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
for ax,(oldcase,newcase,label,q) in zip(axs,[('ramp_w225_L220','inner225_g12_q2p16','內側225：16 → 12 mm',2.16),
                                          ('ramp_w180_L180','center180_g14_q1p728','中間180：16 → 14 mm',1.728)]):
    maximum=0
    for source,case,tag,color in [(HEADS,oldcase,'原16mm','#999999'),(ROOT,newcase,'新版','#197f95')]:
        data=np.loadtxt(source/'cfd'/case/'outlet_centerline.csv',delimiter=',',skiprows=1)
        maximum=max(maximum,float(data[:,1].max()))
        ax.plot(data[:,0],data[:,1],label=tag,color=color,lw=1.7)
    ax.set_title(f'{label}；各指定 Q={q:g} m³/min',fontproperties=font)
    ax.set_xlabel('沿長邊位置（mm）',fontproperties=font);ax.set_ylabel('出口中央線軸向風速（m/s）',fontproperties=font)
    ax.set_ylim(top=maximum*1.3);ax.legend(prop=font,loc='upper left');ax.grid(alpha=.2)
fig.suptitle('指定流量的截面分布比較；圖中不是三路自行產生的工作風量',fontproperties=font)
fig.savefig(OUT/'圖片/內側中間_指定流量分布比較.png',dpi=170);plt.close(fig)

comparison=[]
for i,pos in enumerate(['內側','中間','外側']):
    comparison.append([pos,f'{[225,180,315][i]} × {[12,14,8][i]}',
                       f"{reference[0]['branch_flow_m3_min'][i]:.3f}",f"{candidate[0]['branch_flow_m3_min'][i]:.3f}",
                       f"{reference[0]['slot_area_mean_velocity_m_s'][i]:.2f}",f"{candidate[0]['slot_area_mean_velocity_m_s'][i]:.2f}"])
pipe_rows=[]
for old,new in zip(reference,candidate):
    pipe_rows.append([f"{new['pipe_cut_lengths_m'][0]*100:.0f}",f"{old['total_flow_m3_min']:.3f}",f"{new['total_flow_m3_min']:.3f}",
                      f"{100*(new['total_flow_m3_min']/old['total_flow_m3_min']-1):+.2f}%",
                      f"{old['reports']['pin']:.2f}",f"{new['reports']['pin']:.2f}"])
conv=read(ROOT/'convergence_summary.json')
convergence_rows=[]
for r in reference+candidate:
    convergence_rows.append([r['name'],f"{max(r['load_consistency_error_pct']):.3f}%",f"{r['mass_imbalance_pct']:.5f}%",
                             '通過' if conv.get(r['name'],{}).get('engineering_convergence_pass') else '未全通過'])
head_rows=[]
for m in head_metrics:
    head_rows.append([f"{m['width_mm']} × {m['gap_mm']:g}",f"{m['flow_m3_min']:.3f}",f"{m['inlet_total_pressure_Pa']:.1f}",
                      f"{m['total_pressure_loss_Pa']:.1f}",f"{m['core_line_CV_pct']:.1f}%",f"{m['body_reverse_volume_pct']:.1f}%",
                      '通過' if m['engineering_convergence_pass'] else '未全通過'])
change=100*(candidate[0]['total_flow_m3_min']/reference[0]['total_flow_m3_min']-1)
speed_changes=100*(np.array(candidate[0]['slot_area_mean_velocity_m_s'])/np.array(reference[0]['slot_area_mean_velocity_m_s'])-1)
stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M UTC+8')
report=f'''# 225×12／180×14／315×8 mm 吹嘴：同條件ANSYS重算

整理時間：{stamp}。依使用者要求，重新以ANSYS比較內側225×12、中間180×14、外側315×8 mm。51mm管路、原有分流接頭與外殼維持；另存完整件，未受K1C容量限制，也未分件。

## 總風量少約5%，影響很多嗎？

前次「8.53降至8.11m³/min」是一維初估，約少4.9%、相當於每秒7公升。單看總風量比例不大，但不能換算成乾燥時間變慢4.9%。快乾仍取決於傘面位置的有效風速、覆蓋、脈動和實際水分移除，均尚未實測。

本次把現版16／16／8與候選12／14／8都放到相同入口靜壓及管長重新算。60cm裁切管的結果為 **{reference[0]['total_flow_m3_min']:.3f} → {candidate[0]['total_flow_m3_min']:.3f}m³/min（{change:+.2f}%）**。內側平均出口風速變化 {speed_changes[0]:+.1f}%，中間 {speed_changes[1]:+.1f}%，外側 {speed_changes[2]:+.1f}%。這是在假設壓力下，風量與風速的交換，不是乾燥效果已改善的證明。

{table(['位置','候選淨出口 mm','現版風量 m³/min','候選風量 m³/min','現版平均風速 m/s','候選平均風速 m/s'],comparison)}

候選三個出口的名義面積為內側2700、中間2520、外側2520mm²，比現版3600、2880、2520mm²更接近。三路供風相近時，平均風速也較接近；上表仍採各路實際計算風量除以出口面積，沒有假設三路風量相等。

全部數值均為單台鼓風機的一組三路。330W、11m³/min、460Pa的標示尚不是完整風壓—風量曲線，本次未用11m³/min當強制工作風量；入口靜壓460Pa是比較情境，實際風機工作點未知。

![同條件三路比較](圖片/同條件三路風量風速比較.png)

## 比較條件與管長

參考版和候選版使用相同原分流器三維流體網格。入口靜壓目標460Pa，容許誤差0.1%；下游壓力負載匹配誤差0.5%，流量變動0.15%、質量不平衡0.05%，連續三批通過才保存完整匹配檢查點。這些是負載耦合門檻，與方程殘差門檻分開。

{table(['三管裁切長 cm','現版總Q','候選總Q','總Q變化','現版實得入口靜壓 Pa','候選實得入口靜壓 Pa'],pipe_rows)}

Q單位m³/min。軟管內徑51mm，兩端插入共50mm從裁切長扣除。Darcy摩擦係數假設0.04，下彎K=0.5，接口K=0.15（以ID46截面速度計）。上方ID51、中心線半徑R90的90度彎管包含在各吹嘴CFD中。皺褶、漏氣與實際彎曲半徑尚未實測。

分流器入口82×88mm、三路ID46mm、實體插管長25／35／25mm，沿用中央較兩側長10mm的現有幾何。未模擬風機葉輪、渦殼原有偏流、風機失速或整機入口倒灌。

## 吹嘴直接CFD

Fluent2026R1，3D雙精度、定常不可壓縮空氣，密度1.2kg/m³、黏度1.8e-5Pa·s、SST k–ω、入口擾動5%，光滑無滑移壁。吹嘴出口截面設大氣壓，未包含外部射流或傘面。舊場只用於初始猜測，跨流量初始猜測按流量比縮放後，仍經實際Fluent迭代求解；交付結果沒有以縮放場替代計算。

內側與中間各算兩個指定流量點，擬合非負 `P_total=aQ²+bQ` 阻力曲線後耦合三路。所有候選各路的管路風量均落在各自曲線取樣範圍內。外側315×8mm幾何和曲線沿用前次已核對的結果。

{table(['新出口 mm','指定Q m³/min','所需入口總壓 Pa','上彎＋嘴總壓損 Pa','中央線CV','局部負軸速體積占比','完整收斂'],head_rows)}

入口總壓和總壓損意義不同。CV沿出口厚度中央計算，長邊兩端各略去5mm；完整截面CV另見CSV。局部負軸速體積占比只統計本體內軸向速度低於-0.01m/s的流體體積，不能當作鼓風機回流量。指定流量的形狀比較圖也不能當作三路管線自動產生的工作風量。

![指定流量分布](圖片/內側中間_指定流量分布比較.png)

每條新曲線只有兩個CFD取樣點，擬合誤差小不代表實際精度；分離、回流與瞬態脈動仍可能造成誤差。詳細曲線係數、末段壓力變化與殘差保存在檢查紀錄。

## 模型與接口

{table(['位置','淨出口 mm','軸向總長 mm','包絡 寬×厚×長 mm','導流片數'],dimensions)}

外側STL與前次315×8版雜湊一致。內側、中間只重建出口間隙，總長、入口及名義殼厚沿用：承口ID55.4mm、插入25mm、內流道51mm，殼厚約2.4mm、出口唇部約2mm。承口沿用原R90接頭OD55插口；若直接接軟管，原先估計外徑54.6mm，實物配合仍待確認。

外側保留兩片1.6mm導流片，自本體Z55至332mm，出口前56mm連通；內側、中間沒有新增中央核心或導流片。Blender出風軸水平、寬面平行地面，三個STL為完整件，尚未切分或驗證切片、整機碰撞與固定支撐。

![完整件](圖片/CAD_three_nozzles_horizontal.png)
![尺寸](圖片/three_nozzles_dimensions.png)
![沿用的外側內部剖視](圖片/CAD_315_guide_cutaway.png)

## 驗證狀態

{table(['三路案例','最大下游負載誤差','質量不平衡','完整方程收斂'],convergence_rows)}

完整方程門檻為連續性1e-4、速度1e-6、k與ω各1e-5，並核對末段壓力變化與質量平衡。未全通過的案例必須保留為定常原型估算。負載匹配通過不能取代完整方程收斂。

本次新案例原生case/data已在獨立Fluent程序重新讀入，重新計算報表並檢查正單元體積。STL重讀核對封閉網格、單一連通實體、面方向、正體積與非退化面；Blender重開後量測61點縫寬、淨長、接管內徑及中央開通。尚未完成網格獨立性、瞬態統計、外部射流、真實風機工作點、實物配合與乾燥時間驗證。依先前選擇交付原型及列明未達標項目的報告。

建議以相同轉速、管長、吹距及初始含水狀態，比較傘面風速分布、入口倒灌、脈動和乾燥時間，再決定是否把總量損失換取較高出口風速作為定案。

## 檔案

- `STL_完整件`與`CAD`：三個完整mm STL及Blender模型。
- `三路風量風速_同條件ANSYS比較.csv`、`新吹嘴指定流量_壓損分布與逆向區域.csv`：數值與條件。
- `ANSYS數值紀錄`、`檢查紀錄`：結果、歷程、曲線、殘差與原生檔重讀。
- `ANSYS原始案例_case_data.zip`：本次四個吹嘴點、四個三路案例，加上沿用的兩個外側8mm點。
- `來源程式`供核對算法；重跑需保留本工作資料夾、前版來源結構與既有Python/ANSYS環境。
'''
(OUT/'風量影響與ANSYS報告.md').write_text(report,encoding='utf-8')
for p in ROOT.glob('*.py'):copy(p,Path('來源程式')/p.name)
for p in ROOT.glob('stage_*.json'):copy(p,Path('來源程式')/p.name)
main_zip=OUT/'12_14_8mm完整吹嘴_模型與報告.zip'
files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='MANIFEST.sha256']
with zipfile.ZipFile(main_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in sorted(files):z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(main_zip) as z:
    assert z.testzip() is None and len([p for p in z.namelist() if p.startswith('STL_完整件/')])==3
native_zip=OUT/'ANSYS原始案例_case_data.zip'
cases=[(ROOT,case) for case in all_cases]+[(PRIOR,p['case']) for p in curves['315']['points']]
with zipfile.ZipFile(native_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for source,case in cases:
        for name in ['solution.cas.h5','solution.dat.h5']:z.write(source/'cfd'/case/name,Path(case)/name)
with zipfile.ZipFile(native_zip) as z:assert z.testzip() is None
(OUT/'MANIFEST.sha256').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(OUT).as_posix()
                                           for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.sha256')+'\n',encoding='utf-8')
write_json(ROOT/'DELIVERY_COMPLETE.json',{'delivery':str(OUT),'model_zip':str(main_zip),'native_zip':str(native_zip),
                                        'reference_total_Q60':reference[0]['total_flow_m3_min'],'candidate_total_Q60':candidate[0]['total_flow_m3_min'],
                                        'flow_change_pct':change,'reference_speeds60':reference[0]['slot_area_mean_velocity_m_s'],
                                        'candidate_speeds60':candidate[0]['slot_area_mean_velocity_m_s'],'speed_change_pct':speed_changes.tolist(),
                                        'prototype_limitations_disclosed':True,'actual_fan_point_verified':False})
print('DELIVERY_COMPLETE',str(OUT),flush=True)
