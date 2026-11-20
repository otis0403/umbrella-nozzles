"""Package only selected complete nozzles, with measured and assumed data apart."""
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from design import ROOT, write_json

OUT=ROOT.parent/'集風罩'/'三尺寸吹嘴_225_180_315x16_流量重算_20261116'
FONT=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=11)
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def copy(source,relative):
    dest=OUT/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);return dest
def csv_write(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def md_table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])

assert read(ROOT/'pipeline_state.json')['phase']=='raw_CFD_and_independent_native_readback_complete_report_pending'
selection=read(ROOT/'selection.json');curves=read(ROOT/'selected_pressure_curves.json')
convergence=read(ROOT/'convergence_summary.json');native=read(ROOT/'native_cfd_readback.json')
geometry=read(ROOT/'cad/native_geometry_checks.json')
assert geometry['native_reopened']
OUT.mkdir(parents=True,exist_ok=True)
checks=[];heads=[];files=[]
for index,(key,label) in enumerate([('inner','內側'),('center','中間'),('outer','外側')]):
    spec=selection[key];width=spec['width_mm'];length=spec['length_mm'];h=spec['height_mm']
    suffix='_guided' if spec.get('guided') else ''
    src=ROOT/'cad/full'/f'nozzle_W{width}_G16_L{length}_ramp{suffix}_mm.stl'
    dest=copy(src,Path('STL_完整件')/f'{label}_{width}x16_總長{h}_mm.stl')
    mesh=trimesh.load_mesh(dest,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    assert len(mesh.split(only_watertight=False))==1 and mesh.area_faces.min()>1e-10
    checked=next(row for row in geometry['records'] if row['width_mm']>width-.1 and row['width_mm']<width+.1)
    assert checked.get('guide_count',0)==(2 if suffix else 0)
    checks.append({'position':label,'file':str(dest.relative_to(OUT)),'watertight':True,'single_connected_component':True,
                   'winding_consistent':True,'positive_solid_volume':True,'minimum_triangle_area_mm2':float(mesh.area_faces.min()),
                   'size_mm':mesh.extents.tolist(),'face_count':len(mesh.faces),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                   'gap_61_samples_range_mm':checked['gap_range_mm'],'net_width_measured_mm':checked['width_mm'],
                   'socket_ID_measured_mm':checked['socket_ID_mm'],'guide_count':2 if suffix else 0})
    heads.append(read(ROOT/'cfd'/spec['case']/'profile_metrics.json'))
    files.append([label,f'{width} × 16',h,f'{mesh.extents[1]:.1f} × {mesh.extents[0]:.1f} × {h}',2 if suffix else 0])
copy(ROOT/'cad/three_complete_nozzles_horizontal.blend','CAD/三尺寸吹嘴_完整件_水平配置.blend')
for file in ['CAD_three_nozzles_horizontal.png','CAD_315_guide_cutaway.png','three_nozzles_dimensions.png','ANSYS_internal_axial_velocity.png']:
    copy(ROOT/'images'/file,Path('圖片')/file)
for path in [ROOT/'cad/native_geometry_checks.json',ROOT/'native_cfd_readback.json',ROOT/'selected_pressure_curves.json',ROOT/'convergence_summary.json',ROOT/'selection.json']:
    copy(path,Path('檢查紀錄')/path.name)
write_json(OUT/'檢查紀錄/STL_獨立重讀檢查.json',checks)
network_names=['network_Ps460_hose60','network_Ps460_hose50','network_Q11_hose60']
networks=[read(ROOT/'cfd'/name/'results.json') for name in network_names]
flowrows=[]
for result in networks:
    for i,label in enumerate(['內側','中間','外側']):
        flowrows.append({'case':result['name'],'position':label,'net_width_mm':[225,180,315][i],
                         'gap_mm':16,'pipe_cut_length_m':result['pipe_cut_lengths_m'][i],
                         'branch_flow_m3_min':result['branch_flow_m3_min'][i],
                         'slot_area_mean_velocity_m_s':result['slot_area_mean_velocity_m_s'][i],
                         'total_group_flow_m3_min':result['total_flow_m3_min'],
                         'inlet_static_pressure_Pa':result['reports']['pin'],'inlet_total_pressure_Pa':result['reports']['ptin'],
                         'load_consistency_error_pct':result['load_consistency_error_pct'][i],
                         'actual_fan_operating_point_verified':False})
csv_write(OUT/'三路風量_假設條件.csv',flowrows)
csv_write(OUT/'吹嘴ANSYS截面比較.csv',heads)
curve_rows=[]
for width,curve in curves.items():
    curve_rows.append([width,'、'.join(f"{p['Q_m3_min']:.3f}" for p in curve['points']),
                       f"{curve['maximum_fit_error_pct']:.2f}%",f"{max(p['late_iteration_pressure_range_pct'] for p in curve['points']):.2f}%"])
for case in network_names+[selection[k]['case'] for k in ['inner','center','outer']]:
    for name in ['results.json','history.json','mesh_summary.json','profile_metrics.json','outlet_centerline.csv']:
        src=ROOT/'cfd'/case/name
        if src.exists(): copy(src,Path('ANSYS數值紀錄')/case/name)

fig,axs=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
colors=['#147d92','#ad6625','#5f62aa']
for ax,field,ylabel in zip(axs,['branch_flow_m3_min','slot_area_mean_velocity_m_s'],['每路風量（m³/min）','出口面積平均風速（m/s）']):
    xx=np.arange(3)
    for j,result in enumerate(networks[:2]):
        ax.bar(xx+(j-.5)*.32,result[field],width=.30,label=f'管長 {60-j*10} cm',color=['#247e95','#a8cbd4'][j])
    ax.set_xticks(xx,['內側 225 × 16','中間 180 × 16','外側 315 × 16'],fontproperties=FONT)
    ax.set_ylabel(ylabel,fontproperties=FONT);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    ax.legend(prop=FONT)
fig.suptitle('單台鼓風機的一組三路｜假設入口靜壓維持 460 Pa，並非已知風機工作點',fontproperties=FONT)
fig.savefig(OUT/'圖片/三路風量與風速_條件估算.png',dpi=170);plt.close(fig)

fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
for name,label,color in [('ramp_w315_L320','315 mm 未加導流片','#999999'),('guide_w315_L320','315 mm 加兩片導流片','#147d92')]:
    data=np.loadtxt(ROOT/'cfd'/name/'outlet_centerline.csv',delimiter=',',skiprows=1)
    ax.plot(data[:,0],data[:,1],label=label,color=color,lw=2)
ax.set_xlabel('沿出口長邊的位置（mm）',fontproperties=FONT);ax.set_ylabel('出口中央線軸向風速（m/s）',fontproperties=FONT)
ax.set_title('相同指定流量 3.024 m³/min｜315 mm 原型比較，定常殘差未全達標',fontproperties=FONT)
ax.grid(alpha=.2);ax.legend(prop=FONT)
fig.savefig(OUT/'圖片/315mm導流片_相同流量比較.png',dpi=170);plt.close(fig)

plain=read(ROOT/'cfd/ramp_w315_L320/profile_metrics.json');guided=heads[2]
condition_rows=[]
for result in networks:
    condition='假設入口靜壓 460 Pa、三管 '+('60' if 'hose60' in result['name'] else '50')+' cm' if result['name'].startswith('network_Ps') else '強制指定總風量 11 m³/min、三管 60 cm'
    condition_rows.append([condition,f"{result['total_flow_m3_min']:.3f}",*[f'{v:.3f}' for v in result['branch_flow_m3_min']],
                           f"{result['reports']['pin']:.1f}",f"{result['reports']['ptin']:.1f}"])
speed_rows=[[label,width,f"{networks[0]['slot_area_mean_velocity_m_s'][i]:.2f}",f"{networks[1]['slot_area_mean_velocity_m_s'][i]:.2f}"]
            for i,(label,width) in enumerate([('內側',225),('中間',180),('外側',315)])]
head_rows=[]
for label,row in zip(['內側','中間','外側'],heads):
    head_rows.append([label,f"{row['width_mm']} × 16",f"{row['flow_m3_min']:.3f}",f"{row['inlet_total_pressure_Pa']:.1f}",
                      f"{row['total_pressure_loss_Pa']:.1f}",f"{row['core_line_CV_pct']:.1f}%",f"{row['body_reverse_volume_pct']:.1f}%"])
conv_rows=[]
for key in ['inner','center','outer']:
    case=selection[key]['case'];item=convergence.get(case,{})
    conv_rows.append([case,'通過' if item.get('engineering_convergence_pass') else '未通過',
                      f"{item.get('mass_imbalance_pct',float('nan')):.4f}%",f"{item.get('last_total_pressure_change_pct',float('nan')):.3f}%"])
for item in networks:
    full_pass=convergence.get(item['name'],{}).get('engineering_convergence_pass',False)
    status=('下游負載匹配通過' if item['network_load_consistency_pass'] else '下游負載未匹配')+'；方程殘差'+('通過' if full_pass else '未全通過')
    conv_rows.append([item['name'],status,
                      f"{item['mass_imbalance_pct']:.4f}%",f"流量變動 {item['last_flow_change_pct']:.3f}%"])
report=f'''# 三尺寸完整吹嘴與風量重算

設計版本：2026-11-16；資料整理：{datetime.now().strftime('%Y-%m-%d %H:%M')}。本次只另存三個吹嘴，內側 225／中間 180／外側 315 mm，出口間隙都為 16 mm。依最新要求，未以 K1C 容量限制幾何，交付完整件，尚未分件或驗證切片。原外殼與既有分流接頭未改造。

## 尺寸與接口

{md_table(['位置','淨出口 mm','軸向總長 mm','最大包絡 寬×厚×長 mm','內部導流片'],files)}

三者皆維持外套式接管：承口內徑 55.4 mm、插入深度 25 mm；管內徑 51 mm。55.4 mm 依先前估計的軟管外徑 54.6 mm 預留間隙，尚未實物套合確認。入口含束環收縮槽。名義殼厚 2.4 mm，出口唇部約 2 mm。完整 STL 單位為 mm。Blender 配置為水平出風，三件依內側／中間／外側排列；不是整機安裝配置圖。

315 mm 版有兩片與外殼相連的導流片，名義厚 1.6 mm、前後緣 0.8 mm，自入口座標 Z=55 到 332 mm，出口前仍有 56 mm 無分隔流道。中央軸線保持開通。圖中的剖開外殼只是觀察內部；交付 STL 是封閉完整外殼。

![完整件](圖片/CAD_three_nozzles_horizontal.png)
![尺寸](圖片/three_nozzles_dimensions.png)
![315 mm 內部剖視](圖片/CAD_315_guide_cutaway.png)

## ANSYS 直接計算的吹嘴比較

Fluent 2026 R1，三維雙精度、定常不可壓縮空氣，密度 1.2 kg/m³、黏度 1.8e-5 Pa·s、SST k–ω、入口擾動強度 5%、光滑無滑移壁。每個吹嘴模型包含內徑 51 mm、中心線半徑 90 mm 的進氣彎管。出口截面設為大氣壓，未包含外部射流與傘面。

下表各自指定流量，使淨出口名義平均風速約 10 m/s，供形狀比較；不是同一台風機會自行產生的三路流量。入口總壓為這個邊界下所需的總壓；總壓損為入口與出口質量加權總壓差，兩者意義不同。

{md_table(['位置','出口 mm','指定 Q m³/min','所需入口總壓 Pa','彎管＋吹嘴總壓損 Pa','中央線風速 CV','局部負軸速體積占比'],head_rows)}

中央線 CV 取出口厚度中央，沿長邊兩端各略去 5 mm；完整截面面積加權 CV 另見 CSV。局部負軸速體積占比只統計吹嘴本體內軸向速度低於 -0.01 m/s 的流體體積，不能解讀成鼓風機回流風量或入口倒灌率。

315 mm 在相同指定 Q=3.024 m³/min 下，加導流片前後，中央線 CV 由 {plain['core_line_CV_pct']:.1f}% 降至 {guided['core_line_CV_pct']:.1f}%；局部負軸速體積占比由 {plain['body_reverse_volume_pct']:.1f}% 降至 {guided['body_reverse_volume_pct']:.1f}%。相應的總壓損由 {plain['total_pressure_loss_Pa']:.1f} 增至 {guided['total_pressure_loss_Pa']:.1f} Pa，所需入口總壓由 {plain['inlet_total_pressure_Pa']:.1f} 增至 {guided['inlet_total_pressure_Pa']:.1f} Pa。這是均勻度與損失的取捨，尚未消除全部逆向區域。導流片版採三通道網格，與無片版的網格數及拓撲也不同；兩者尚未完成網格獨立性檢查，這些差異目前只能作原型比較。

![同流量比較](圖片/315mm導流片_相同流量比較.png)

![ANSYS 內部截面軸向速度](圖片/ANSYS_internal_axial_velocity.png)

## 一組三路的風量重算

用各尺寸多組 Fluent 指定流量結果擬合 `入口總壓 = a Q² + b Q`，再以現有三路分流器的三維 Fluent 模型計算流量分配。下游負載含新吹嘴及 R90 上彎、51 mm 軟管、下彎與接頭。軟管長度指裁切總長，兩端插入共 50 mm，計算時扣除；Darcy 摩擦係數假設 0.04，下彎 K=0.5，接口 K=0.15（以 46 mm 截面速度計）。未實測的軟管粗糙度、皺褶、彎曲半徑及漏氣會改變結果。三維模型使用目前分流器中央插管較兩側長 10 mm 的接口形狀，未修改實體接頭。

{md_table(['淨寬 mm','曲線樣本 Q m³/min','樣本最大擬合誤差','末八批入口總壓範圍／均值最大值'],curve_rows)}

擬合誤差是對這些數值樣本的吻合程度，不能當成實際風量誤差；末段迭代範圍也不是物理瞬態的統計不確定度。

{md_table(['條件','單組總 Q','內側 Q','中間 Q','外側 Q','入口靜壓 Pa','入口總壓 Pa'],condition_rows)}

所有 Q 單位為 m³/min，以上均為單台風機的一組三路。若左右鏡像兩組、各用同樣的獨立風機，才可把整機總量相加。

同樣在假設入口靜壓 460 Pa 下，各路出口名義面積平均風速如下：

{md_table(['位置','淨寬 mm','60 cm 管 m/s','50 cm 管 m/s'],speed_rows)}

入口靜壓維持 460 Pa 是假設條件。規格標示 11 m³/min 與 460 Pa，尚無完整 P–Q 曲線，也沒有實測工作點，不能據此保證風機能同時維持這兩個數字。強制 11 m³/min 那一列的用途是反算管路所需壓力，不能當作預測風機實際可供應 11 m³/min。管長 50／60 cm 表格亦採相同假設入口靜壓，方便比較管路影響。

分流器入口未帶入實測渦殼出口的偏流與旋流；葉輪、風機失速及整機入口倒灌也不在此模型內。

![條件風量與風速](圖片/三路風量與風速_條件估算.png)

三個 16 mm 出口的總名義面積為 11520 mm²，比先前三個 150×16 mm 的 7200 mm² 增加 60%。在總風量固定且分布均勻時，合計面積平均風速為原來的 62.5%。因此加寬可增加覆蓋，不能直接承諾吹得更強；三條同徑管也不會自動按出口寬度比例分配流量。315 mm 那路需較大流量，才可達到與較窄吹嘴相同的平均風速。

## 驗證狀態與實際限制

{md_table(['案例','判定','質量不平衡','末段變化'],conv_rows)}

吹嘴定常殘差仍有振盪，完整收斂條件未全通過。收斂判斷包含連續性 1e-4、速度 1e-6、紊流量 1e-5、壓力漂移與質量平衡；詳細殘差見檢查紀錄。三路案例的「下游負載匹配通過」僅表示壓力負載與流量迭代相符，不等於所有方程殘差皆收斂。未做網格獨立性、瞬態統計、外部射流、實際風機葉輪或傘面乾燥驗證。依先前選擇，這次交付可供試作的幾何與列明未達標項目的原型報告。

STL 獨立重讀通過單一連通實體、封閉網格、正體積、面方向、非退化三角面檢查；Blender 重新開檔後量測每個出口 61 個位置的縫寬、淨長、接管內徑及中央開通。原生 Fluent case/data 重新讀入，報表數字與正單元體積也已核對。這些檔案檢查不代表實際列印、套管配合或乾燥效果已通過。

實測時以相同轉速和管路，比較三路出口風速分布、入口倒灌、脈動、靜壓及乾燥時間；取得風機 P–Q 曲線或實測總風量後，才能把條件估算換成實際工作點。315 mm 版的兩端與中間仍有差異，應沿長邊量測，不能只量中央最高風速。

## 檔案

- `STL_完整件`：三個完整 mm STL，未切分。
- `CAD`：可重開的 Blender 完整模型。
- `圖片`：實際 STL 外觀、尺寸與剖視、CFD 比較圖。
- `三路風量_假設條件.csv`：各路流量與出口平均風速，含條件及負載匹配誤差。
- `ANSYS數值紀錄`、`檢查紀錄`：結果、歷程、網格及原生檔重讀紀錄。
- `來源程式`：本次幾何與計算程式，單位及邊界可重查。完整原始 CFD case/data 保留於本工作資料夾，另有主要案例 ZIP。
'''
(OUT/'設計與ANSYS報告.md').write_text(report,encoding='utf-8')
for src in ROOT.glob('*.py'): copy(src,Path('來源程式')/src.name)
for filename in ['stage_guided315.json','stage_high_flow.json','stage_network.json','study_settings.json']:
    copy(ROOT/filename,Path('來源程式')/filename)
# Zip source files relative to the delivery root. Credentials, transcript temp
# files, abandoned print splits, and superseded candidates are excluded.
zip_path=OUT/'三尺寸完整吹嘴_模型與報告.zip'
entries=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='MANIFEST.sha256']
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in sorted(entries): z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if n.startswith('STL_完整件/')])==3
native_zip=OUT/'ANSYS主要案例_case_data.zip'
with zipfile.ZipFile(native_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for case in network_names+[selection[k]['case'] for k in ['inner','center','outer']]:
        for filename in ['solution.cas.h5','solution.dat.h5']:
            z.write(ROOT/'cfd'/case/filename,Path(case)/filename)
with zipfile.ZipFile(native_zip) as z: assert z.testzip() is None
manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(OUT).as_posix()
                   for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.sha256')
(OUT/'MANIFEST.sha256').write_text(manifest+'\n',encoding='utf-8')
write_json(ROOT/'DELIVERY_COMPLETE.json',{'delivery':str(OUT),'files':len(entries),'model_zip':str(zip_path),
                                         'native_zip':str(native_zip),'STL_count':3,'prototype_convergence_limitations_disclosed':True,
                                         'physical_fan_operating_point_verified':False,'completed_at':datetime.now().isoformat()})
print('DELIVERY_COMPLETE',str(OUT),flush=True)
