import json
from pathlib import Path
from session import ROOT

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
cases={q:ROOT/'medium'/f'Q{q:.2f}' for q in [.5,1.,1.5]}
results={q:read(p/'results.json') for q,p in cases.items()}
conv={q:read(p/'convergence.json') for q,p in cases.items()}
coarse=read(ROOT/'coarse'/'Q1.00'/'results.json')
medium=results[1.]
fine=read(ROOT/'fine'/'Q1.00'/'results.json')
fine_conv=read(ROOT/'fine'/'Q1.00'/'convergence.json')
mesh={name:read(ROOT/name/'mesh_summary.json') for name in ['coarse','medium','fine']}
diff=lambda key:100*(medium[key]/coarse[key]-1)
diff_mf=lambda key:100*(fine[key]/medium[key]-1)
mesh_sensitivity={'flow_m3_min':1.,'coarse_cells':mesh['coarse']['cells'],'medium_cells':mesh['medium']['cells'],
    'inlet_static_pressure_change_pct':diff('required_inlet_static_pressure_Pa'),
    'total_pressure_loss_change_pct':diff('total_pressure_loss_Pa'),
    'outlet_mean_axial_velocity_change_pct':diff('outlet_mean_uz_m_s'),
    'outlet_full_area_CV_change_pct':diff('outlet_area_weighted_CV'),
    'fine_cells':mesh['fine']['cells'],
    'medium_to_fine_inlet_static_pressure_change_pct':diff_mf('required_inlet_static_pressure_Pa'),
    'medium_to_fine_total_pressure_loss_change_pct':diff_mf('total_pressure_loss_Pa'),
    'medium_to_fine_outlet_mean_velocity_change_pct':diff_mf('outlet_mean_uz_m_s'),
    'total_pressure_losses_coarse_medium_fine_Pa':[coarse['total_pressure_loss_Pa'],medium['total_pressure_loss_Pa'],fine['total_pressure_loss_Pa']],
    'reverse_volume_fractions_coarse_medium_fine':[coarse['reverse_volume_fraction_below_minus_0.01_m_s'],medium['reverse_volume_fraction_below_minus_0.01_m_s'],fine['reverse_volume_fraction_below_minus_0.01_m_s']],
    'note':'Three-grid sensitivity check; not a formal grid-convergence-index study. Tiny vane-tip recirculation is resolution-sensitive.'}
(ROOT/'mesh_sensitivity.json').write_text(json.dumps(mesh_sensitivity,indent=2),encoding='utf-8')
table=[]
checks=[]
for q,r in results.items():
    table.append(f"| {q:g} | {r['required_inlet_static_pressure_Pa']:.2f} | {r['total_pressure_loss_Pa']:.2f} | {r['outlet_mean_uz_m_s']:.2f} | {100*r['outlet_gap_averaged_long_axis_CV']:.2f}% | {100*r['reverse_volume_fraction_below_minus_0.01_m_s']:.6f}% |")
    c=conv[q]
    checks.append(f"| {q:g} | {c['iteration']} | {c['last_residuals']['continuity']:.2e} | {c['mass_imbalance_pct']:.3g}% | {c['last_report_interval_pressure_loss_change_pct']:.4g}% | {'通過' if c['engineering_convergence_pass'] else '未通過'} |")
max_back=max(100*r['reverse_volume_fraction_below_minus_0.01_m_s'] for r in results.values())
max_mass=max([c['mass_imbalance_pct'] for c in conv.values()]+[fine_conv['mass_imbalance_pct']])
notes='\n'.join(table)
checknotes='\n'.join(checks)
report=f'''# 最新無核心吹嘴：ANSYS Fluent 指定流量比較

本次已用本機 ANSYS Fluent 2026 R1 Student、3D 雙精度、4 核心實際求解。對象是 **200 mm、216×12 mm 橫向出口、無中央核心、保留十字導流片** 的現有版本。原始列印模型沒有修改。

在本次均勻入口的三個指定流量下，出口均為向外流動；內部倒流主要集中在導流片尾端附近的小區域，入口過渡圓角附近另見極小負速度。Uz < -0.01 m/s 的體積占比最高約 {max_back:.6f}%（三流量共同使用中網格）。這不等於風機吸入口不會回流：本模型沒有包含風機、葉輪或實際風機入口。

## 數值結果

| 假設流量 m³/min | 入口靜壓 Pa | 總壓損失 Pa | 出口平均軸向速度 m/s | 長邊分布 CV | 局部倒流體積占比 |
|---:|---:|---:|---:|---:|---:|
{notes}

入口靜壓以出口 0 Pa 表壓為基準，採入口質量加權平均。總壓損失為入口與出口的質量加權總壓差。入口靜壓包含流道收縮、加速與實際損失，不能把整個靜壓差都叫做壓損。

出口平均速度取整個出口面的軸向速度面積平均；長邊 CV 先跨 12 mm 縫寬平均，再沿 216 mm 長邊做面積加權統計。這和完整出口面的 CV 不同，後者也包含壁面附近的低速區。三個案例的出口反向通量比例皆為 {max(r['outlet_reverse_flux_fraction'] for r in results.values()):.3g}。

![出口長邊速度比較](outlet_profiles.png)

### 1.0 m³/min 的流場

![軸向速度及方向](medium/Q1.00/velocity_cuts.png)

切面刻意偏離導流片中心：長邊圖取 X=3 mm，短邊圖取 Y=3 mm。黑箭頭表示當地流向，不能用這兩個切面代表完整三維流場；倒流體積統計使用全體流體單元。

![完整出口分布](medium/Q1.00/outlet_distribution.png)

![倒流單元位置](medium/Q1.00/recirculation_locations.png)

倒流定義為全域軸向速度 Uz < -0.01 m/s；另外保留 0、-0.001、-0.05 m/s 門檻的統計於各案例 results.json。此門檻用於排除非常小的數值負速度。尾端放大圖之外也保留全流道投影，包含入口過渡圓角附近的小負速區；不能把局部小尾流區解讀為整個吹嘴向入口倒灌。各軸向區間的倒流占比見 results.json 的 reverse_volume_by_axial_region。

## 與這台鼓風機規格的關係

使用者提供的圖片標示 **150FLJ330W、330 W、1.6 A、2800 rpm、11 m³/min、靜壓 460 Pa、電容 5–6 µF**。圖片可讀的出口淨尺寸為 82×88 mm，與現有模型名義入口相符。

目前沒有本機型已確認的完整 P–Q 曲線，也沒有證據證明 11 m³/min 和 460 Pa 是同一測試工作點。因此沒有把這兩個數字連成假設風機曲線，也沒有對 CFD 強制輸入 11 m³/min。

216×12 mm 出口面積是 2592 mm²，為原 216×4 mm 的三倍。同一流量下，平均出口速度降至三分之一，理想出口動壓降至九分之一；裝機後實際流量會隨風機與阻力曲線改變，不能假設保持不變。

若硬把 11 m³/min 全通過這個 12 mm 出口，平均速度約 70.7 m/s、出口動壓約 3002 Pa。以均勻的現有入口、出口速度做理想不可壓縮能量估算，僅加速所需的入口至出口靜壓差就約 2598 Pa，尚未加上損失與分布修正。這說明標示風量不能直接當成裝上吹嘴後的風量；460 Pa 在此只作規格壓力量級參考，並未被認定為已確認的最大壓力。

**目前可以判斷：本版吹嘴在所測三個指定流量下，沒有出現大範圍的流道內倒流。仍不能據此保證裝回鼓風機後消除吸入口回流，也不能由這三點推算真實工作流量。**

## 模型與假設

- 流體域僅包含吹嘴內部 Z=0–200 mm，氣流沿 +Z 直通。出口長邊相對底座旋轉 90°，氣流沒有轉 90°彎。
- 入口 X×Y=82×88 mm，入口圓角 R3；出口 X×Y=12×216 mm。薄十字片保留，短片至 Z=134 mm，長片至 Z=144 mm，最後 56 mm 沒有分隔。
- 流體域依現有 geometry.py 重建，沒有把列印用實體 STL 誤當成流體。法蘭及螺絲孔屬於固體固定界面，未納入流體域。
- 空氣密度 1.2 kg/m³，黏度 1.8×10⁻⁵ Pa·s；定常、不可壓縮、等溫、SST k-ω RANS。
- 均勻軸向速度入口，無旋流；湍流強度 5%，入口水力直徑 42 mm。
- 出口在吹嘴端面，0 Pa 表壓，允許反向流動；回流湍流強度 5%，水力直徑約 22.74 mm。
- 光滑、靜止、無滑移壁面。未包含列印粗糙度、變形與裝配漏氣。
- 三個流量分別實際重新求解。其他流量採已求解流場的比例縮放作為初始猜測，再迭代，並未把比例換算值當成 CFD 結果。
- 額外細網格從中網格的已解流場插值作初始猜測，再以 Fluent 實際求解至收斂。

均勻無旋流入口通常會讓左右分布較理想。真實離心風機出口的非均勻速度與旋流可能改變分布與分離；較低流量的轉捩敏感性亦未在本次另做轉捩模型研究。定常 RANS 不用來判斷風機失速、喘振或隨時間變化的回流。

## 網格與收斂

| 網格 | 六面體單元 | 節點 | 與參數流道體積的差異 |
|---|---:|---:|---:|
| 粗 | {mesh['coarse']['cells']:,} | {mesh['coarse']['nodes']:,} | {mesh['coarse']['volume_error_pct']:.4f}% |
| 中（三流量共用） | {mesh['medium']['cells']:,} | {mesh['medium']['nodes']:,} | {mesh['medium']['volume_error_pct']:.4f}% |
| 細（1.0 m³/min 驗證） | {mesh['fine']['cells']:,} | {mesh['fine']['nodes']:,} | {mesh['fine']['volume_error_pct']:.4f}% |

三組均通過 Fluent 網格檢查，無負體積。實際品質輸出保留於求解紀錄；壁面 y+ 的中位數、95 百分位與最大值保留於各 results.json，未假設所有壁面均達 y+<1。

1.0 m³/min 的總壓損失，粗、中、細分別為 {coarse['total_pressure_loss_Pa']:.4f}、{medium['total_pressure_loss_Pa']:.4f}、{fine['total_pressure_loss_Pa']:.4f} Pa。粗→中差 {mesh_sensitivity['total_pressure_loss_change_pct']:.3f}%，中→細差 {mesh_sensitivity['medium_to_fine_total_pressure_loss_change_pct']:.3f}%。中→細的入口靜壓差 {mesh_sensitivity['medium_to_fine_inlet_static_pressure_change_pct']:.3f}%，出口面平均軸向速度差 {mesh_sensitivity['medium_to_fine_outlet_mean_velocity_change_pct']:.4f}%。額外細網格在本測點確認了入口壓力與壓損的穩定性；其他兩個流量未各自重做細網格，因此不能把此誤差直接套到所有工作點。三組加密方式包含不同的尾流解析度，本次未做正式 GCI 研究。

細網格的局部倒流體積占比為 {100*fine['reverse_volume_fraction_below_minus_0.01_m_s']:.6f}%，中網格為 {100*medium['reverse_volume_fraction_below_minus_0.01_m_s']:.6f}%。局部尾流的最小負速度與很小的體積數字仍受解析度影響，應著重區域位置與量級，不能把最後幾位數當成實測精度。

| 流量 m³/min | 累計迭代編號 | 最終連續方程殘差 | 質量不平衡 | 最後報告區間壓損變化 | 工程收斂檢查 |
|---:|---:|---:|---:|---:|---|
{checknotes}
| 1.0（細網格） | {fine_conv['iteration']} | {fine_conv['last_residuals']['continuity']:.2e} | {fine_conv['mass_imbalance_pct']:.3g}% | {fine_conv['last_report_interval_pressure_loss_change_pct']:.4g}% | {'通過' if fine_conv['engineering_convergence_pass'] else '未通過'} |

殘差監控的嚴格設定為 10⁻⁵。部分案例的連續方程殘差可能停留在約 10⁻⁵ 至數倍 10⁻⁵，因此沒有將它們寫成「全部殘差低於 10⁻⁵」。工程收斂另要求連續方程 <10⁻⁴、三速度殘差 <10⁻⁶、k/ω <10⁻⁵、最後報告區間入口靜壓及壓損變化 <0.5%、質量不平衡 <0.1%；實際數值及嚴格門檻是否通過均記錄在 convergence.json。最後質量不平衡最高為 {max_mass:.3g}%。

## 開啟與重查

1. 在 Fluent 3D Double Precision 中讀取 medium/Q1.00/review.cas.h5 及同目錄 review.dat.h5；0.5 與 1.5 案例位於各自 Q0.50、Q1.50 目錄。
2. review 案例含 inlet、outlet、housing、long_vane、short_vane 及 long_cut、short_cut、near_outlet 切面。
3. comparison.csv 是三流量總表；outlet_face_values.csv 是出口每面數值；outlet_long_axis_61_samples.csv 是 61 個長邊插值取樣（端點依無滑移設為 0），並非額外增加了網格解析度。
4. cell_fields.npz 保留完整流體單元的座標、體積、三速度與壓力；reverse_cells_Uz_lt_minus_0p01_m_s.csv 保留倒流單元。surface *_fields.npz 保留面連接與資料，圖由這些資料產生。
5. Fluent 求解紀錄、殘差歷程、report history、設定、網格生成與後處理程式皆保留於本資料夾。python_environment.txt 記錄此次 Python 套件版本。
6. 額外加密結果位於 fine/Q1.00，亦提供 review.cas.h5 及 review.dat.h5；它用於網格確認，三流量比較表仍使用同一組中網格。

交付前已在 Fluent 中逐一重新開啟三個中網格案例及細網格案例的 review 案例／資料配對，重算五項原生報告並與匯出前比對；四組均通過，詳見 reopen_verification.json。驗證後已正常關閉此次背景 Fluent，釋放授權。

source_integrity.json 核對來源 STL 與先前 SHA256 一致，並記錄來源資料夾檔案供分析前後比對。所有 CFD 產物另存在 CFD_ANSYS_20261105，未修改原始 STL、Blender 或整體設計。

後續實測應使用相同風機轉速與管路，對照無吹嘴及本版，量測入口靜壓、實際流量、吸入口是否向外吹與脈動。取得可信的本機 P–Q 曲線後，才能把吹嘴阻力與風機一起求實際工作點。

網格格式依 [ANSYS Fluent Mesh File Format](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/tgd_user_format_gridsect.html)；自動控制使用 [ANSYS PyFluent](https://fluent.docs.pyansys.com/version/stable/user_guide/session/launching_ansys_fluent.html)。數值結果來自本資料夾的本機求解紀錄。
'''
(ROOT/'README.md').write_text(report,encoding='utf-8')
print(json.dumps(mesh_sensitivity,indent=2))
assert all(c['engineering_convergence_pass'] for c in conv.values()) and fine_conv['engineering_convergence_pass'],'At least one case needs more iterations'
