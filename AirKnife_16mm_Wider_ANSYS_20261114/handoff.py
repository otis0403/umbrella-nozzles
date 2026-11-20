"""Build the comparison report from actual solutions after all runs finish."""
import argparse,csv,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from geometry import ROOT
from post_results import read

def write(p,value):
    (ROOT/p).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def main(height):
    matrix=read(ROOT/'case_matrix.json');convergence={}
    for c in matrix:
        p=ROOT/'cfd'/c['name'];r=read(p/'results.json');v=read(p/'convergence.json')
        assert r['conditions']['gap_mm']==16 and v['engineering_convergence_pass'],(c['name'],v)
        convergence[c['name']]=v
    reopened=read(ROOT/'cfd/reopen_checks.json')
    assert len(reopened)==5 and all(v['native_case_data_reopened'] and v['max_relative_report_difference']<1e-8 for v in reopened)
    assert len(read(ROOT/'cfd/completed_cases.json'))==7
    write('cfd/convergence_summary.json',convergence)
    a=read(ROOT/'cfd/jet_H320_W252/results.json');b=read(ROOT/'cfd/jet_H320_W252_fine/results.json')
    differences={}
    for key,x,y in [('flow_m3_min',a['nozzle_flow_m3_min'],b['nozzle_flow_m3_min']),
        ('slot_mean_Uz_m_s',a['free_jet_metrics']['slot_mean_uz_m_s'],b['free_jet_metrics']['slot_mean_uz_m_s']),
        ('80mm_common_line_Uz_m_s',a['free_jet_metrics']['80mm']['common_200mm_line_mean_Uz_m_s'],b['free_jet_metrics']['80mm']['common_200mm_line_mean_Uz_m_s']),
        ('80mm_momentum_N',a['free_jet_metrics']['80mm']['forward_momentum_window_N'],b['free_jet_metrics']['80mm']['forward_momentum_window_N'])]:
        differences[key]={'standard':x,'finer_and_longer_domain':y,'change_pct':100*(y/x-1)}
    sensitivity={'type':'Combined cross-section mesh refinement and domain extension; not GCI',
        'baseline':'jet_H320_W252','check':'jet_H320_W252_fine','differences':differences,
        'all_listed_changes_under_5_pct':all(abs(v['change_pct'])<5 for v in differences.values())}
    assert sensitivity['all_listed_changes_under_5_pct'],sensitivity
    write('cfd/sensitivity_check.json',sensitivity)
    start=read(ROOT/'source_integrity_start.json');source=ROOT.parent/start['source_folder']
    hashes={k:hashlib.sha256((source/k).read_bytes()).hexdigest() for k in start['files']}
    assert hashes==start['files']
    write('source_integrity.json',{'source_folder':source.name,'all_original_files_unchanged':True,'file_count':len(hashes),'files':hashes})
    base=read(ROOT/'cfd/jet_H260_W216/results.json');chosen=read(ROOT/f'cfd/jet_H{height}_W252/results.json')
    previous=read(ROOT.parent/'AirKnife_K1C_20261105/cfd/jet_g16/results.json')
    baseline_check={'mesh_hash_matches_previous':hashlib.sha256((ROOT/'cfd/jet_H260_W216/nozzle.msh').read_bytes()).hexdigest()==hashlib.sha256((ROOT.parent/'AirKnife_K1C_20261105/cfd/jet_g16/nozzle.msh').read_bytes()).hexdigest(),
        'recomputed_flow_change_pct':100*(base['nozzle_flow_m3_min']/previous['nozzle_flow_m3_min']-1),
        'recomputed_slot_mean_velocity_change_pct':100*(base['free_jet_metrics']['slot_mean_uz_m_s']/previous['free_jet_metrics']['slot_mean_axial_velocity_m_s']-1)}
    assert baseline_check['mesh_hash_matches_previous'] and abs(baseline_check['recomputed_flow_change_pct'])<1
    write('cfd/baseline_reproduction_check.json',baseline_check)
    shorter=read(ROOT/'cfd/jet_H320_W252/results.json');longer=read(ROOT/'cfd/jet_H360_W252/results.json')
    selection={'date':'2026-11-14','requested_gap_mm':16,'selected_total_height_mm':height,
        'selected_clear_span_mm':252,'physical_outer_width_mm':256.8,'max_allowed_width_mm':300,
        'existing_body_reused':True,'body_height_mm':200,'lip_flow_length_mm':height-200,
        'lip_print_height_mm':height-194,'no_external_ribs':True,'main_parts':2,
        'computed_flow_change_vs_baseline_pct':100*(chosen['nozzle_flow_m3_min']/base['nozzle_flow_m3_min']-1),
        '80mm_common_line_velocity_change_pct':100*(chosen['free_jet_metrics']['80mm']['common_200mm_line_mean_Uz_m_s']/base['free_jet_metrics']['80mm']['common_200mm_line_mean_Uz_m_s']-1),
        '80mm_momentum_change_pct':100*(chosen['free_jet_metrics']['80mm']['forward_momentum_window_N']/base['free_jet_metrics']['80mm']['forward_momentum_window_N']-1),
        'H360_momentum_change_vs_H320_pct':100*(longer['free_jet_metrics']['80mm']['forward_momentum_window_N']/shorter['free_jet_metrics']['80mm']['forward_momentum_window_N']-1),
        'selection_reason':'H320 keeps higher flow and momentum than H360 while using a shorter printed lip' if height==320 else 'H360 selected for the reported comparison',
        'hypothetical_inlet_total_pressure_Pa':400,'actual_fan_curve_used':False,
        'actual_slicing_verified':False,'physical_print_verified':False,'drying_performance_verified':False}
    write('selection.json',selection)
    ge=read(ROOT/'cad/geometry_checks.json');r=next(x for x in ge['parts'] if x['group']==f'lip_H{height}')
    report=[]
    for h,w in [(260,216),(320,252),(360,252)]:
        body=read(ROOT/f'cfd/body_H{h}_W{w}/results.json');jet=read(ROOT/f'cfd/jet_H{h}_W{w}/results.json');f=jet['free_jet_metrics']
        report.append((h,w,body,jet,f))
    bodytable='\n'.join(f"| {h} | {w} | {bo['required_static_pressure_Pa']:.2f} | {bo['pressure_loss_to_domain_outlet_Pa']:.2f} | {bo['outlet_mean_axial_velocity_m_s']:.2f} | {100*bo['negative_uz_volume_fraction']:.6f} |" for h,w,bo,je,f in report)
    jettable='\n'.join(f"| {h} | {w} | {je['nozzle_flow_m3_min']:.3f} | {f['slot_mean_uz_m_s']:.2f} | {f['80mm']['common_200mm_line_mean_Uz_m_s']:.2f} | {f['80mm']['covered_span_line_CV_pct']:.3f} | {f['80mm']['forward_momentum_window_N']:.3f} |" for h,w,bo,je,f in report)
    convtable='\n'.join(f"| {name} | {v['last_iteration']} | {v['last_residuals']['continuity']:.3g} | {v['mass_imbalance_pct']:.4g} | {'是' if v['strict_all_residuals_below_1e_minus_5'] else '否'} |" for name,v in convergence.items())
    sentable='\n'.join(f"| {k} | {v['standard']:.5g} | {v['finer_and_longer_domain']:.5g} | {v['change_pct']:+.3f}% |" for k,v in differences.items())
    text=f'''# 16 mm 出口展寬及加長：ANSYS 比較

2026-11-14。依最新要求，出口間隙維持 **16 mm**，淨長由 216 展寬為 **252 mm**，外寬約 **256.8 mm**，小於 300 mm。沿用已列印的 200 mm 單件本體，透過新的吹嘴把總長增加為 320 或 360 mm。此次交付以 **{height} mm 總長**為優先試作選項；另一長度保留作對照。原本無補強肋、無定位銷的一體設計維持。

本報告的正式比較與交付吹嘴均為 16 mm 出口。

## 幾何與試作建議

推薦先使用 `print/STL/lip_252x16_H{height}_no_ribs_mm.stl`。STL 已在平台平面旋轉 45°、底面 Z=0，單位 mm、100% 匯入。新吹嘴列印包絡約 **{r['print_size_mm'][0]:.1f} × {r['print_size_mm'][1]:.1f} × {r['print_size_mm'][2]:.0f} mm**；加四周 5 mm brim 仍可放入 K1C 220×220×250 mm 成形空間。

入口接口沿用 216×20 mm，流道平滑過渡至 252×16 mm。接合止面 Z=200，定位裙向下伸 6 mm，因此吹嘴實體列印高度為總長減 194 mm。整組法蘭到出口總長，與單獨吹嘴列印高度是不同尺寸。

兩種新吹嘴都能接回同一個現有單件本體；已印好的本體無須重印。使用 4 支 M3×16 mm 螺絲及 4 顆 M3 螺母接合；原風機法蘭 12 支固定螺絲沿用。先放本體螺母，再從上方套入新吹嘴，硬止面靠合後均勻輕鎖；有密封需求時，鎖合後從接縫外側貼膠帶。

0.4 mm 噴嘴、PLA／PLA+ 可從 0.20 mm 層高、6 道壁、5 mm brim 開始切片。檢查接合耳座與定位裙的局部支撐，清除孔口與流道毛邊。名義截面壁厚維持 2.4 mm；實際剛性、翹曲與列印高低差尚未驗證。兩側出口上緣在模型中同高，詳細數值在 `cad/airpath_checks.json`。通用 3MF 只含模型及擺放位置，沒有預先切片或 G-code。

## A. 同流量比較

同樣名義 3 m³/min、出口表壓 0 Pa。網格離散的實際流量約 2.9998 m³/min。入口靜壓包含出口加速需求；不可逆總壓損另列，兩者不能混用。

| 總長 mm | 出口淨長 mm | 入口靜壓 Pa | 入口到出口總壓損 Pa | 出口面平均 Uz m/s | 內部負軸向速度體積 % |
|---|---:|---:|---:|---:|---:|
{bodytable}

展寬增加出口面積，在固定流量下會降低出口平均速度與加速所需壓力；更長的壁面仍會增加摩擦。較低入口靜壓不等於所有壓損下降。

## B. 相同假設總壓下的自由射流

入口總表壓固定 **400 Pa**，周圍與遠場表壓 0 Pa。這是公平比較幾何用的假設邊界，**不是風機實際工作點**。風機圖片的 11 m³/min 與 460 Pa 靜壓沒有完整 P–Q 曲線，不能同時強制當作裝上吹嘴後的實際條件，也不能把 460 Pa 靜壓直接視為 400 Pa 總壓。

| 總長 mm | 出口淨長 mm | 算得流量 m³/min | 出口面平均 Uz m/s | 8 cm 共用中央線 Uz m/s | 8 cm 各自涵蓋線 CV % | 8 cm 動量通量 N |
|---|---:|---:|---:|---:|---:|---:|
{jettable}

共用中央線為 X=0、Y=−100…100 mm 上 101 點平均，並非整個工作面的平均速度。各自涵蓋線長度為出口淨長減 16 mm：原版 200 mm、新版 236 mm，共 121 點，用來看更寬範圍的均勻度。動量通量在所有案例使用相同視窗 X=±40、Y=±160 mm，積分 ∫ρ max(Uz,0)²dA；它不是傘布的實測作用力。

在此假設下，所選版本相較原版：流量變化 **{selection['computed_flow_change_vs_baseline_pct']:+.2f}%**，8 cm 共用中央線速度變化 **{selection['80mm_common_line_velocity_change_pct']:+.2f}%**，動量通量變化 **{selection['80mm_momentum_change_pct']:+.2f}%**。360 mm 相較 320 mm 的 8 cm 動量差異為 **{selection['H360_momentum_change_vs_H320_pct']:+.2f}%**；這些差異須連同更長零件的材料、空間與列印需求一起判斷，不能只看長度。

360 mm 版的涵蓋線速度 CV 略低（{longer['free_jet_metrics']['80mm']['covered_span_line_CV_pct']:.3f}% 對 {shorter['free_jet_metrics']['80mm']['covered_span_line_CV_pct']:.3f}%），但兩者在這條線上都很均勻；320 mm 版的流量與前向動量較高，零件也較短，因此優先試作 320 mm。

![8 cm 中央線比較](images/CFD_80mm_profiles.png)

## 求解設定及驗證

Fluent Student 2026 R1，3D 雙精度、4 CPU，穩態不可壓縮、SST k–ω，ρ=1.2 kg/m³、μ=1.8×10⁻⁵ Pa·s；光滑無滑移壁面，入口紊流強度 5%、水力尺度 84 mm。冷啟動先 80 步一階，之後動量與紊流二階迎風、壓力二階。自由射流使用前案計算場作初始猜測後，再由 Fluent 重新迭代；初猜不等同求解結果。

基準自由射流網格 425240 cells／448600 nodes；320 mm 標準案例 444680 cells／469690 nodes。額外驗證 320 mm 案例，加密截面並將外部長度由 250 增至 400 mm，網格為 826880 cells／864879 nodes。各案都低於 Student 百萬 cells 與 nodes 限制，細胞體積均為正。

| 指標 | 標準網格／250 mm 域 | 加密／400 mm 域 | 差異 |
|---|---:|---:|---:|
{sentable}

此為網格與外部域長同時改動的敏感度檢查，並非正式 GCI，也沒有把兩種影響分離。360 mm 案例未另做加密研究。

工程收斂門檻：連續性 <10⁻⁴、速度 <10⁻⁶、k／ω <10⁻⁵，最後兩批入口靜壓與流量變化各 <0.5%，質量不平衡 <0.1%。全案通過此門檻；另列是否全部殘差都達 10⁻⁵。

| 案例 | 最後迭代 | 連續性殘差 | 質量不平衡 % | 全殘差 <10⁻⁵ |
|---|---:|---:|---:|---|
{convtable}

原生 case/data 重新讀取後，入口靜／總壓及各邊界質量流率與儲存紀錄核對，結果在 `cfd/reopen_checks.json`。原生 case/data、網格及場資料保留在本機 `cfd`，列印 ZIP 僅收錄摘要、表格、曲線、圖片及檢查紀錄。

## 回流與實測限制

內部負軸向速度統計只包含 z<出口高度且 Uz<−0.01 m/s 的體積。外部環境吸入屬射流捲吸，不能把原始全域負速度比例或遠場邊界回流當作鼓風機吸入口倒吹。原始 `outlet` 欄位是遠端計算盒邊界，實體出口與工作距離數據請使用 `free_jet_metrics`。

模型不包含風機葉輪、蝸殼、實際入口旋流與非均勻分布，也不包含傘布、水膜、熱傳、接縫滲漏、列印粗糙度、外耳附近環境流與瞬態失速。自由射流保留出口壁厚，外接合耳座不作外流解析。無法藉此證明風機吸入口回流完全排除，也不能證明整把傘吹 10 秒後不滴水。

實印後建議用同一把傘、相同浸濕與預滴水時間、固定供電和轉傘方式，在 3／5／8 cm 各測 3 次；吹 10 秒後，觀察停止吹風後 5 秒的滴數，並記錄吸入口方向與脈動。起始帶水量盡量一致。原始模型檔案保持不變，詳見 `source_integrity.json`。
'''
    (ROOT/'README_16mm加寬與ANSYS.md').write_text(text,encoding='utf-8')
    with (ROOT/'五金清單.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['零件','數量','用途']);w.writerows([['M3x16 螺絲',4,'吹嘴接本體'],['M3 螺母',4,'本體耳座'],['原法蘭螺絲',12,'沿用原配置']])
    versions=subprocess.run([sys.executable,'-m','pip','freeze'],check=True,capture_output=True,text=True).stdout
    (ROOT/'environment_versions.txt').write_text(versions,encoding='utf-8')
    print('REPORT_AND_SELECTION_COMPLETE',json.dumps(selection),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--height',type=int,choices=[320,360],default=320);main(p.parse_args().height)
