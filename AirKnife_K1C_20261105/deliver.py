"""Generate the reviewable manufacturing and analysis hand-off from real exports."""
import csv,hashlib,json,math,subprocess,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager
from geometry import ROOT,section,HOLES

DATE='2026-11-06'
FONT=Path(r'C:\Windows\Fonts\msjh.ttc')
fontManager.addfont(str(FONT))
plt.rcParams.update({'font.family':'Microsoft JhengHei','axes.unicode_minus':False})

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def csvfile(path,rows):
    with (ROOT/path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def integrity():
    old=read('../CFD_ANSYS_20261105/source_integrity.json')
    records=[]
    for name,expected in old['source_folder_files'].items():
        p=ROOT.parent/name
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual==expected,name
        records.append({'file':name,'sha256':actual,'matches_previous_record':True})
    tracked=subprocess.run(['git','status','--short','--untracked-files=no'],cwd=ROOT.parent,
        check=True,capture_output=True,text=True).stdout
    assert not tracked.strip(),tracked
    write('source_integrity.json',{'verified_date':DATE,'original_files':records,
        'all_recorded_original_files_unchanged':True,'tracked_worktree_changes':tracked,
        'new_output_directory':ROOT.name})

def tables():
    geom=read('cad/geometry_checks.json');parts={r['name']:r for r in geom['parts']}
    bodies=[read(f'cfd/{n}/results.json') for n in ['legacy_Q3','H200','H260','H320']]
    rows=[]
    for r in bodies:
        rows.append({'case':r['name'],'height_mm':r['conditions']['height_mm'],
            'gap_mm':r['conditions']['gap_mm'],'flow_m3_min':r['nozzle_flow_m3_min'],
            'inlet_static_Pa':r['required_static_pressure_Pa'],
            'nozzle_total_pressure_loss_Pa':r['pressure_loss_to_domain_outlet_Pa'],
            'gap_averaged_span_CV_pct':r['outlet_gap_averaged_long_CV']*100,
            'internal_reverse_volume_pct':r['negative_uz_volume_fraction']*100})
    csvfile('body_comparison.csv',rows)
    jets=[read(f'cfd/jet_g{g}/results.json') for g in [8,12,16]]
    fine=read('cfd/jet_check12/results.json');base=jets[1]
    diff={}
    for k,a,b in [
        ('flow_m3_min',base['nozzle_flow_m3_min'],fine['nozzle_flow_m3_min']),
        ('slot_mean_uz_m_s',base['free_jet_metrics']['slot_mean_axial_velocity_m_s'],fine['free_jet_metrics']['slot_mean_axial_velocity_m_s']),
        ('at_80mm_center_line_uz_m_s',base['free_jet_metrics']['80mm']['central_200mm_line_mean_uz_m_s'],fine['free_jet_metrics']['80mm']['central_200mm_line_mean_uz_m_s']),
        ('at_80mm_momentum_N',base['free_jet_metrics']['80mm']['forward_momentum_window_N'],fine['free_jet_metrics']['80mm']['forward_momentum_window_N'])]:
        diff[k]={'baseline':a,'finer_longer_domain':b,'change_pct':100*(b/a-1)}
    meshbase=read('cfd/jet_g12/mesh_summary.json');meshfine=read('cfd/jet_check12/mesh_summary.json')
    sensitivity={'method':'Combined mesh refinement and downstream domain extension; not GCI',
        'baseline_case':'jet_g12','check_case':'jet_check12','baseline_mesh':meshbase,'check_mesh':meshfine,
        'baseline_external_reach_mm':250,'check_external_reach_mm':400,'metrics':diff,
        'all_listed_changes_below_5_pct':all(abs(v['change_pct'])<5 for v in diff.values())}
    assert sensitivity['all_listed_changes_below_5_pct'],sensitivity
    write('cfd/sensitivity_check.json',sensitivity)
    conv={name:read(f'cfd/{name}/convergence.json') for name in ['legacy_Q3','H200','H260','H320','jet_g8','jet_g12','jet_g16','jet_check12']}
    assert all(r['engineering_convergence_pass'] for r in conv.values())
    write('cfd/convergence_summary.json',conv)
    bom=[
        {'item':'M3 x 16 mm machine screw','quantity':12,'purpose':'8 body seam + 4 body/lip coupling'},
        {'item':'M3 x 30 mm machine screw','quantity':4,'purpose':'4 lip front/back clamps'},
        {'item':'M3 hex nut, nominal AF 5.5 mm','quantity':16,'purpose':'Captive pockets nominal AF 5.8 mm'},
        {'item':'M3 washer (optional)','quantity':16,'purpose':'Under screw heads; check bolt engagement'},
        {'item':'Printed alignment pin 2.8 x 6 mm','quantity':12,'purpose':'8 body + 4 lip; plate includes 16'},
        {'item':'Existing blower mounting screws','quantity':12,'purpose':'Reuse correct original sizes; do not substitute all with M3'},
        {'item':'External seam sealing tape','quantity':1,'purpose':'Seal outside only; keep mating hard stops clear'}]
    csvfile('BOM.csv',bom)
    dims=[]
    for r in geom['parts']:
        dims.append({'part':r['name'],'print_X_mm':r['print_size_mm'][0],
            'print_Y_mm':r['print_size_mm'][1],'print_Z_mm':r['print_size_mm'][2],
            'solid_volume_PLA_estimate_g':r['approx_PLA_mass_g'],
            'quantity_for_16mm_assembly':12 if r['name']=='alignment_pin_2p8x6' else
                1 if r['group'] in ['body','lip_16'] else 0})
    csvfile('part_dimensions.csv',dims)
    loss_drop=100*(1-bodies[2]['pressure_loss_to_domain_outlet_Pa']/bodies[0]['pressure_loss_to_domain_outlet_Pa'])
    assembly_names=['body_A','body_B','lip_16mm_front','lip_16mm_back']
    mass=sum(parts[n]['approx_PLA_mass_g'] for n in assembly_names)+12*parts['alignment_pin_2p8x6']['approx_PLA_mass_g']
    summary={'date':DATE,'recommended_first_test_gap_mm':16,'control_gap_mm':12,
        'experimental_optional_gap_mm':8,'height_mm':260,'clear_span_mm':216,
        'main_printed_parts_per_assembly':4,'nominal_section_wall_mm':2.4,
        'solid_volume_PLA_estimate_g':mass,'same_flow_loss_reduction_pct':loss_drop,
        'actual_blower_fan_curve_available':False,'actual_installed_flow_verified':False,
        'physical_print_verified':False,'actual_slicing_verified':False,'10_second_no_drip_verified':False,
        'working_distance_mm':[30,80],'sensitivity':diff,'CFD_cases':8,
        'all_engineering_convergence_checks_passed':True}
    write('design_summary.json',summary)
    return geom,parts,bodies,jets,sensitivity,conv,summary

def documentation(data):
    geom,parts,bodies,jets,sens,conv,summary=data
    br='\n'.join(f"| {r['name']} | {r['required_static_pressure_Pa']:.2f} | {r['pressure_loss_to_domain_outlet_Pa']:.2f} | {100*r['outlet_gap_averaged_long_CV']:.2f} | {100*r['negative_uz_volume_fraction']:.6f} |" for r in bodies)
    jr='\n'.join(f"| {r['conditions']['gap_mm']} | {r['nozzle_flow_m3_min']:.3f} | {r['free_jet_metrics']['slot_mean_axial_velocity_m_s']:.2f} | {r['free_jet_metrics']['30mm']['central_200mm_line_mean_uz_m_s']:.2f} | {r['free_jet_metrics']['50mm']['central_200mm_line_mean_uz_m_s']:.2f} | {r['free_jet_metrics']['80mm']['central_200mm_line_mean_uz_m_s']:.2f} | {r['free_jet_metrics']['80mm']['forward_momentum_window_N']:.3f} |" for r in jets)
    sr='\n'.join(f"| {k} | {v['baseline']:.5g} | {v['finer_longer_domain']:.5g} | {v['change_pct']:+.3f}% |" for k,v in sens['metrics'].items())
    cr='\n'.join(f"| {k} | {v['last_iteration']} | {v['last_residuals']['continuity']:.3g} | {v['mass_imbalance_pct']:.5g} | 通過 | {'是' if v['strict_all_residuals_below_1e_minus_5'] else '否'} |" for k,v in conv.items())
    dr='\n'.join(f"| {n} | {' × '.join(f'{v:.1f}' for v in parts[n]['print_size_mm'])} |" for n in ['body_A','body_B','lip_16mm_front','lip_16mm_back'])
    moment_gain=100*(jets[2]['free_jet_metrics']['80mm']['forward_momentum_window_N']/jets[1]['free_jet_metrics']['80mm']['forward_momentum_window_N']-1)
    readme=f'''# K1C 分件風刀試作版

交付日期：{DATE}。資料夾的 20261105 是開始工作的日期。

先試 **216 × 16 mm 出口**，保留 **216 × 12 mm** 作對照；兩者共用本體。總高 **260 mm**，本體兩半＋吹唇兩半，共四個主要列印件，另加定位銷與螺絲。內部沒有中央核心，也沒有十字導流片；補強放在外側。這是現有 150FLJ330W 鼓風機的獨立測試原型。

原始模型與原資料夾沒有覆寫；原版 16 個已記錄檔案重新核對雜湊均一致。新件保留原法蘭的 12 個孔位、孔徑與偏心位置。出口長邊沿原模型 Y，氣流沿 +Z，沒有 90 度流道轉彎。

**已完成：幾何檢查、Fluent 空氣流場比較、網格及外部域敏感度檢查。未完成：實際切片、實印、風機實測與濕傘測試。「3–8 cm、吹 10 秒後不滴水」仍是驗收目標。**

![組裝與分件](images/03_assembly_guide.png)

## 先列印哪些檔案

`print/plates` 是已擺放方向的通用 **模型 3MF**，沒有綁定材料、機器或 G-code。使用 K1C / 0.4 mm / PLA 或 PLA+ 設定匯入後再切片；保留方向與 100% 比例。一次只開一個盤檔，清空上一盤的模型。

1. `00_fit_test_and_16_pins.3mf`：先印配合測試塊與 16 根 2.8 × 6 mm 定位銷；每組用 12 根，餘 4 根備用。名義定位孔為 3.2 mm。
2. `01_body_A.3mf`、`02_body_B.3mf`：本體各印一盤。
3. `03_lip_16mm_pair.3mf`：先印 16 mm 吹唇一對。
4. `03_lip_12mm_pair.3mf`：需要比較時再印 12 mm 吹唇，沿用同一個本體。

`print/STL` 也有各件 STL，單位 mm，已轉成建議列印方向；`print/3MF` 是每件單獨的通用 3MF。8 mm 是額外實驗選項，不列為首選。不要把不同間隙的 front/back 混用。`cad/reference` 僅供組裝座標參考，勿直接拿來排版。

若銷太緊或太鬆，先去除孔口毛邊，再試獨立提供的 2.6 / 3.0 mm 銷；不要整體縮放模型，否則原法蘭孔位會改變。3.1 / 3.2 / 3.3 mm 測試孔用來辨識實際列印的孔徑偏差。

## 尺寸與列印方向

| 主要零件 | 已擺正的列印 X × Y × Z，mm |
|---|---:|
{dr}

裝好後含外側耳座的包絡約 **118 × 236 × 260 mm**；原法蘭 118 × 120 × 3 mm，入口淨尺寸 X × Y = 82 × 88 mm、圓角 R3，法蘭中心 X 偏移 +2 mm。名義截面壁厚 2.4 mm；傾斜面法向厚度會略有不同。出風淨長 216 mm，可換間隙 8 / 12 / 16 mm。吹唇本體軸向 60 mm，定位裙向下多伸 6 mm，所以單件列印側向長度約 66 mm。

K1C 的標稱成形空間為 220 × 220 × 250 mm；本機安裝的 K1C 0.4 設定檔也已唯讀核對。吹唇長邊直立列印，高 236 mm；模型與 5 mm 外擴 brim 的 XY 範圍均在平台內。[Creality K1C 官方規格](https://www.creality.com/products/k1c-carbon-3d-printer)

建議先從 0.20 mm 層高、6 道壁、5 mm brim、一般 PLA 預設材料溫度開始；厚耳座可用 20–30% 填充。這些是起始設定，並非已實印驗證的製程。高而薄的吹唇外壁先以約 60–80 mm/s 試印，依材料與機況調整。**兩片吹唇同盤時使用逐層列印，勿用逐物件順序列印。**

本體依原流向直立，吹唇長邊直立。切片預覽時檢查外側耳座、螺母袋及局部懸空面，必要時加可拆的局部支撐；避免在流道內留下不可移除的支撐。所有支撐與孔內毛邊要在合殼前清乾淨。尚未自動完成 Creality Print 切片；本機 7.3 的 CLI 嘗試未產生切片結果，因此此包沒有列印時間估計或已驗證 G-code。[對應的官方儲存庫問題回報](https://github.com/CrealityOfficial/CrealityPrint/issues/634)

依模型實體體積、PLA 密度 1.24 g/cm³估算，一組 16 mm 組裝件加 12 根銷約 **{summary['solid_volume_PLA_estimate_g']:.0f} g**；這是全實體體積估算，實際耗材會受耳座填充、支撐、brim 與切片路徑影響。

## 五金與組裝

| 零件 | 數量 | 用途 |
|---|---:|---|
| M3 × 16 mm 螺絲 | 12 | 本體兩半 8；吹唇接本體 4 |
| M3 × 30 mm 螺絲 | 4 | 吹唇前後半夾合 |
| M3 六角螺母 | 16 | 外側預留螺母袋；袋對邊 5.8 mm |
| M3 墊片 | 16，可選 | 放在螺絲頭下，仍須確認有效咬合長度 |
| 列印定位銷 2.8 × 6 mm | 12 | 本體 8；吹唇 4 |
| 原風機固定螺絲 | 沿用 12 支 | 原孔有 4.4 與 6.4 mm 兩種孔徑，依原配置使用 |
| 外貼密封膠帶 | 適量 | 僅貼外側接縫 |

1. 先試銷孔、螺母袋與螺絲通孔，去除毛邊。螺母應可座入袋內，勿靠強行鎖緊把 PLA 撐裂。
2. 本體兩半的 8 個定位位置放入銷，合攏後用 8 支 M3 × 16 螺絲均勻輕鎖；兩條外側縱向接縫可加膠帶密封。
3. 取同一尺寸的一對吹唇，放入 4 根銷，再用 4 支 M3 × 30 螺絲夾合。檢查兩端沒有錯台，216 mm 長縫中間保持全通。
4. 將吹唇的外定位裙套入本體，對準側面的避讓缺口，讓接合硬止面完全靠合。用 4 支 M3 × 16 螺絲接合本體與吹唇。外補強肋已留直徑 10 mm 工具孔，可從上方伸入工具鎖此四支螺絲；已用直徑 8 mm 工具柱核對空間。
5. **不要在接合硬止面之間夾厚墊片**，間隙與位置由硬止面決定。接合後再從外側貼膠帶密封。確認螺絲沒有伸入流道，出口多點間隙一致，再以原法蘭螺絲裝回風機。

建議先在獨立測試架固定風機與吹嘴。這版沒有驗證整台機器外殼的容納空間，也沒有更動原外殼。PLA 試作件未做耐熱試驗，本次設計以未加熱的空氣流比較為主。

## 為什麼先試 16 mm

同樣 3 m³/min、12 mm 出口比較，新 260 mm 無核心無導流片版本的不可逆總壓損由 **27.48 降至 12.92 Pa，約減少 {summary['same_flow_loss_reduction_pct']:.1f}%**；入口需要的靜壓由 **234.67 降至 219.26 Pa**。前者是損失，後者還包含把空氣加速所需的壓力，因此不能解讀成風速增加 53%。

在**相同、假設的入口總壓 400 Pa** 下，16 mm 與 12 mm 在 8 cm 的中央線風速接近，但 16 mm 的前向動量通量約多 **{moment_gain:.1f}%**。縮成 8 mm 沒有帶來明顯更快的工作距離風速，反而減少流量。因此先試 16 mm，再換 12 mm 比較濕傘。

400 Pa 是比較用總壓邊界，**不是把銘牌 460 Pa 靜壓直接當總壓，也不是實際風機工作點**。沒有完整 P–Q 曲線，不能宣稱實機會提供下面的流量。詳見 [CFD 模擬與限制](CFD_REPORT.md)。

## 10 秒不滴水：實測方式

先以 16 mm 在 3 / 5 / 8 cm 各測 3 次，再用 12 mm 重複。用同一把傘、同一供電及風機轉速、相同吹掃／旋轉方法；固定浸濕與預滴水時間，起始帶水質量盡量控制在 ±5%。記錄乾重、吹前重、吹 10 秒後重，以及停止吹風後 5 秒內的滴數。

若要整把傘都達標，測試時須固定傘的旋轉速度與吹掃路徑；216 mm 風刀一次只覆蓋局部，單點風速不能證明整把傘乾燥。用 `physical_test_template.csv` 記錄；同條件 3 次均不滴水、吸入口保持吸入且無明顯脈動，再判定該配置達標。出口風速、入口靜壓和實際風量如能量測也一起記錄。

空氣 CFD 沒有模擬水膜、布面接觸、傘的遮擋或瞬態風機失速，不能代替上述驗收。

## 其他檔案

- `cad/K1C_modular_airknife.blend`：可編輯 Blender 模型，預設顯示 16 mm；8 / 12 / 16 mm 各在獨立 collection。
- `images`：實際 STL 組裝渲染、分件圖、尺寸與模擬比較。
- `cad/*checks.json`、`print/plate_checks.json`：孔位、61 點縫寬、封閉網格、工具空間、排版邊界檢查。
- `BOM.csv`、`part_dimensions.csv`：五金與各件尺寸。
- `CFD_REPORT.md`、`body_comparison.csv`、`free_jet_comparison.csv`：模擬條件與結果。
- `cfd`：本機保存原生 case/data、網格與數據；列印 ZIP 只納入摘要、曲線、檢查及圖片，減少檔案大小。
- `source_integrity.json`：原始檔案保留紀錄；`MANIFEST.sha256`：列印包內檔案雜湊。

重建腳本放在此資料夾根目錄；依賴 Python、NumPy、SciPy、trimesh、manifold3d、matplotlib、Pillow、Blender；重新執行 CFD 另需 ansys-fluent-core 與可用 Fluent 授權。本次 Python 3.13、Blender 5.1.2、Fluent Student 2026 R1，幾何單位 mm，CFD 單位 m。
'''
    (ROOT/'README_列印與組裝.md').write_text(readme,encoding='utf-8')
    report=f'''# 風刀分件試作版：CFD 比較與驗證

日期：{DATE}。這是空氣單相工程比較；建議先試 16 mm，12 mm 作實機對照。尚無濕傘試驗，也沒有宣稱 10 秒乾燥已達成。

## 選型結論與適用範圍

在本次已比較的幾何中，選 260 mm 高、216 mm 淨長、可換吹唇。本體無核心、無內部導流片，外肋補強。選 260 mm 是為了讓各主件能以 K1C 分件列印，並兼顧流道內局部逆流與長度。此結果不是對所有幾何的全域最佳化證明。

原風機圖片提供 150FLJ330W、330 W、2800 rpm、11 m³/min、460 Pa 靜壓。完整 P–Q 曲線與各標示對應的測試工況未知。**11 m³/min 不能作為裝上任何吹嘴後都不變的實際流量；460 Pa 靜壓不能直接視為本次 400 Pa 總壓邊界。**

## 求解設定

ANSYS Fluent Student 2026 R1，3D、雙精度、4 CPU，穩態不可壓縮空氣、SST k–ω，ρ=1.2 kg/m³、μ=1.8×10⁻⁵ Pa·s。光滑無滑移壁面，無重力驅動、熱傳或水相；前 80 步一階，之後動量與紊流採二階迎風、壓力二階。敏感度案例以基準速度／壓力／紊流場插值作初猜，再以 Fluent 重新迭代。

入口紊流強度 5%、水力尺度 84 mm；這一輪新舊受控比較都採同設定。入口未建風機葉輪、蝸殼、旋流或實際非均勻速度分布。列印表面粗糙、接縫滲漏與裝配變形未建入。外補強肋遠離內部通道，CFD 保留 2.4 mm 出口端面，但沒有解析外肋附近的環境流動，屬自由射流近似。

## A. 同流量、12 mm 出口的流道比較

均設定名義入口 3 m³/min、出口表壓 0 Pa；新模型離散入口面積造成實際值約 2.9998 m³/min，差約 0.007%。這組用於比較壓損，不代表風機實際運轉流量。

| 案例 | 入口靜壓 Pa | 入口至出口總壓損 Pa | 沿長邊的間隙平均速度 CV % | 內部負軸向速度體積 % |
|---|---:|---:|---:|---:|
{br}

`legacy_Q3` 是原 200 mm、12 mm 無核心但仍保留薄十字支撐片的版本；H200 / H260 / H320 為新的無核心無內部片系列，最後 60 mm 為吹唇。這是整套幾何改動的比較，不能把結果單獨歸因於加長或移除支撐片。

H200 損失比 H260 低約 0.45 Pa，但負軸向速度體積比例約為 H260 的 16 倍；比例皆很小，只是本次的輔助指標，並非瞬態失速判準。H320 的改善有限、零件更長。因此選 H260。新 H260 的損失相對原型降低 {summary['same_flow_loss_reduction_pct']:.2f}%；入口靜壓僅降低約 6.57%，不能宣稱風速提高同樣百分比。長向均勻度未比原版更佳；表中已列出完整取捨。

## B. 自由射流：不同吹唇在假設相同總壓下比較

入口總表壓固定 400 Pa，周圍與遠場表壓 0 Pa、允許吸入環境空氣。外部計算區 X=±100 mm、Y=±200 mm，出口外延 250 mm。每個吹唇的實際通流量由求解得到；沒有加入假造風機曲線。

| 出口間隙 mm | 算得流量 m³/min | 出口面平均 Uz m/s | 3 cm 中央線 Uz | 5 cm 中央線 Uz | 8 cm 中央線 Uz | 8 cm 前向動量通量 N |
|---|---:|---:|---:|---:|---:|---:|
{jr}

中央線指 X=0、Y=−100…100 mm 上 101 點的平均軸向速度，接近射流核心，**不是整個工作平面的平均速度**。動量通量為距出口指定平面、X=±40、Y=±130 mm 視窗內的 ∫ρ max(Uz,0)²dA，單位 N；它不是對傘布的實測作用力。

同一總壓下，8 mm 減少流量，沒有顯著提高 3–8 cm 的核心速度；16 mm 在 8 cm 的中央線速度與 12 mm 幾乎相同，前向動量通量多 {moment_gain:.1f}%。這支持優先實測 16 mm，但真實風機在較大流量處可能提供較低壓力，所以本結果不能證明裝上現有風機後 16 mm 必然優於 12 mm。需要實際風機曲線或直接實測確認。

![8 cm 速度線比較](images/jet_80mm_comparison.png)

## C. 網格、域大小與收斂

六面體貼體網格，細胞體積均為正，每案節點與細胞皆低於 Student 100 萬限制。內部 H200 / H260 / H320 分別為 146304 / 188928 / 232704 cells；標準自由射流 425240 cells、448600 nodes。12 mm 驗證案改成 797840 cells、833829 nodes，並把外部長度由 250 增至 400 mm。

| 指標 | 標準網格／250 mm 域 | 加密網格／400 mm 域 | 差異 |
|---|---:|---:|---:|
{sr}

此為一次**網格與域長同時改動的敏感度檢查**，所有列出差異小於 5%；不是正式 GCI，也沒有把網格效應與域長效應分開。只對 12 mm 做了這項額外檢查；8 與 16 mm 沒有各自完成獨立網格研究。

工程收斂門檻：連續性 <10⁻⁴，三方向速度 <10⁻⁶，k / ω <10⁻⁵，最後兩批入口靜壓與流量變化各 <0.5%，質量不平衡 <0.1%。另列出是否全部殘差都小於 10⁻⁵，避免把工程收斂與嚴格殘差標準混為一談。

| 案例 | 最後迭代 | 連續性殘差 | 質量不平衡 % | 工程門檻 | 全部殘差 <10⁻⁵ |
|---|---:|---:|---:|---|---|
{cr}

`cfd/reopen_checks.json` 是另開 Fluent 後重讀原生 case/data 的檢查；H260、三款吹唇與加密案例重新計算入口靜／總壓及各邊界質量流率，與儲存紀錄比較。`convergence.json`、`history.json`、殘差 CSV 和原生 case/data 均保存於各案資料夾。

## 如何解讀回流與原始欄位

內部負 Uz 以各案例出口上游 z<H 且 Uz<−0.01 m/s 的 cell 體積計算；自由射流案例 H=260 mm。新系列仍有很小的局部負軸向速度，不能寫成完全零回流。自由射流周圍的環境入口發生吸入是射流捲吸；遠邊界局部流回也包含環境循環，不能稱為鼓風機吸入口倒吹。

外部案例原始 `results.json` 中的 `outlet` 是計算盒最遠端邊界，不是實體長縫。請使用 `free_jet_metrics` 的出口及工作距離數據；原始 `pressure_loss_to_domain_outlet_Pa` 包含環境捲吸與混合，不可當成吹嘴自身壓損。原始全域負 Uz 體積也包含外部空氣，與內部負 Uz 指標不同。

## 尚待實測的部分

本次沒有包含實際傘布、含水量、濕潤性、遮擋、轉傘路徑、蒸發熱傳、瞬態風機失速或進氣口流場，因此不能證明整把傘 10 秒後不滴水，也不能保證已排除實機吸入口倒吹。以 README 的 3 / 5 / 8 cm、12 / 16 mm、各 3 次測試矩陣驗證；記錄吸入口方向、脈動與吹後滴水。

幾何與製造檢查另見 `cad/geometry_checks.json`、`assembled_airpath_checks.json`、`assembly_interference_checks.json`；只有網格、尺寸、干涉與模型檔案通過檢查，不等同完成實印。
'''
    (ROOT/'CFD_REPORT.md').write_text(report,encoding='utf-8')

def illustrations():
    bg=(248,250,252);ink=(22,42,58);muted=(62,85,101)
    canvas=Image.new('RGB',(2000,1440),bg);d=ImageDraw.Draw(canvas)
    def txt(x,y,s,size=32,color=ink):d.text((x,y),s,font=ImageFont.truetype(str(FONT),size),fill=color)
    txt(55,30,'216 × 16 mm 風刀｜K1C 四件式試作版',48)
    txt(55,100,'本體兩半＋可替換吹唇兩半；內部無核心、無導流片',32,muted)
    for filename,x in [('01_assembled.png',30),('02_exploded.png',1010)]:
        im=Image.open(ROOT/'images'/filename).convert('RGB');im.thumbnail((960,1010))
        canvas.paste(im,(x+(960-im.width)//2,200))
    txt(55,156,'組裝外觀（預設 16 mm）',32)
    txt(1030,156,'分件示意（螺絲、定位銷未繪出）',32)
    txt(55,1240,'出口：216 mm 淨長 × 16 mm 間隙；另附 12 / 8 mm 吹唇',34)
    txt(55,1300,'總高 260 mm｜原法蘭 118 × 120 mm、12 孔位置保留',34)
    txt(55,1362,'列印前需切片檢查；10 秒不滴水仍待實測。',28,muted)
    canvas.save(ROOT/'images'/'03_assembly_guide.png')
    fig,axs=plt.subplots(1,3,figsize=(15,8),layout='constrained')
    z=np.linspace(0,260,401);ss=np.array([section(v,260,16) for v in z]);w,dpth=ss[:,0],ss[:,1]
    for ax,width,title in [(axs[0],w,'長邊方向 Y–Z'),(axs[1],dpth,'短邊方向 X–Z')]:
        ax.fill_betweenx(z,-width/2-2.4,-width/2,color='#277681')
        ax.fill_betweenx(z,width/2,width/2+2.4,color='#277681')
        ax.plot([-60,60],[0,0],lw=5,color='#374b60')
        ax.axhline(200,c='#a76c21',ls='--',lw=1);ax.text(0,204,'吹唇接合 Z=200',ha='center',fontsize=10)
        ax.annotate('',xy=(width[-1]/2,275),xytext=(-width[-1]/2,275),arrowprops={'arrowstyle':'<->'})
        ax.text(0,279,f'{width[-1]:g} mm 淨尺寸',ha='center',fontsize=11)
        ax.set(title=title,ylabel='Z：流向 (mm)',xlabel='Y (mm)' if ax is axs[0] else 'X (mm)',ylim=(-8,300))
        ax.set_aspect('equal');ax.grid(alpha=.15)
    ax=axs[2];ax.set_xlim(0,220);ax.set_ylim(0,275);ax.set_aspect('equal')
    ax.add_patch(plt.Rectangle((0,0),220,250,fill=False,ls='--',ec='#778899'))
    ax.add_patch(plt.Rectangle((10,0),118,200,fc='#859dad',alpha=.8))
    ax.text(69,95,'本體每半\n118 × 110.4 × 200',ha='center',fontsize=10)
    ax.add_patch(plt.Rectangle((165,0),28,236,fc='#65bdc1',alpha=.8))
    ax.text(181,245,'吹唇每半\n約 28 × 66 × 236',ha='right',fontsize=10)
    ax.set(title='列印高度比較（示意，非同盤）',xlabel='平台寬度 (mm)',ylabel='列印 Z (mm)')
    fig.suptitle('260 mm 試作版｜內流道截面與 K1C 列印方向\n截面示意不顯示外耳、接縫與法蘭孔；完整幾何以 STL 為準',fontsize=16)
    fig.savefig(ROOT/'images'/'04_dimensions_and_print.png',dpi=160);plt.close(fig)

if __name__=='__main__':
    integrity();data=tables();documentation(data);illustrations()
    print('HANDOFF_DOCUMENTS_AND_ILLUSTRATIONS_COMPLETE',flush=True)
