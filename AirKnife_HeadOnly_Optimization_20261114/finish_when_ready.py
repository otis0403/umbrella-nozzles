"""Finish only after both actual fine solutions pass the declared checks."""
import json,time
from geometry import ROOT
from analyze import main as analyze,read
from delivery import main as deliver,metrics,pct

while not (ROOT/'FOLLOWUP_STAGE_4_COMPLETE.json').exists():time.sleep(5)
analyze()
convergence={p.parent.name:read(p) for p in (ROOT/'cfd').glob('*/convergence.json')}
assert len(convergence)==13,(len(convergence),list(convergence))
assert all(v['engineering_convergence_pass'] for v in convergence.values()),[(k,v) for k,v in convergence.items() if not v['engineering_convergence_pass']]
checks=read(ROOT/'cfd/followup_reopen_checks.json')
assert len(checks)==9 and all(v['max_relative_error']<1e-8 for v in checks)
(ROOT/'followup_plan_5.json').write_text(json.dumps({'jobs':[],'final':True}),encoding='utf-8')
while 'OWNED_FOLLOWUP_SOLVER_EXIT_COMPLETED' not in (ROOT/'followup_study.log').read_text(encoding='utf-8',errors='replace'):time.sleep(2)
base=metrics('jet_ref216_fine_p400');new=metrics('jet_short216_fine_p400')
key='same_200x16_patch_normal_dynamic_pressure_mean_Pa'
gains=[pct(new[f'{d}mm'][key],base[f'{d}mm'][key]) for d in [30,50,80]]
std0=metrics('ref216');std1=metrics('jet_wide228_p400');wide_gain=pct(std1['80mm'][key],std0['80mm'][key])
small=min(gains)<3
recommendation=(
    f"**目前不建議只為了『更強』重印。** 在同一假設400 Pa入口總壓、相同吹拂面積下，216短嘴加密後於3、5、8 cm的動壓指標相對原版為 **{gains[0]:+.2f}%、{gains[1]:+.2f}%、{gains[2]:+.2f}%**。此結果不足以支持明顯吹力升級。先沿用現有件，核對實體出口是否等寬16 mm、接縫是否漏氣，以及出口至傘布的距離。"
    if small else
    f"216短嘴在同一假設400 Pa入口總壓下，加密後於3、5、8 cm的動壓指標相對原版為 **{gains[0]:+.2f}%、{gains[1]:+.2f}%、{gains[2]:+.2f}%**，可列為下一個試印候選，但仍需實測風機工作點與吹水效果。")
recommendation+=f"\n\n228加寬款的標準網格8 cm同面積動壓為 **{wide_gain:+.2f}%**，僅增加覆蓋寬度，不列為吹力升級推薦，也未進行加密驗證。兩款STL均保留，供幾何核對或自願試作；原版檔案完全未覆寫。短嘴整組220 mm、加寬款230 mm，分別比目前少40及30 mm；安裝時必須調整位置，保持相同出口至傘布距離。若出口位置固定、必須維持總長260 mm，請繼續使用原嘴；另兩個維持260 mm的篩選方案也未顯示明顯增益。"
selection={
    'date':'2026-11-14','status':'validated_numerical_comparison_physical_test_pending',
    'printed_baseline':{'clear_span_mm':216,'gap_mm':16,'height_mm':260,'no_external_ribs':True},
    'body_reused':True,'body_height_mm':200,'upper_head_only':True,'gap_mm':16,'max_allowed_width_mm':300,
    'delivered_designs':['short216','wide228'],
    'standard_cases':{'short216':'jet_short216_p400','wide228':'jet_wide228_p400'},
    'fine_cases':{'ref216':'jet_ref216_fine_p400','short216':'jet_short216_fine_p400'},
    'labels':{'short216':'Short 216 x 16 / H220 prototype','wide228':'Wide 228 x 16 / H230 prototype'},
    'labels_zh':{'short216':'216短嘴試作款','wide228':'228加寬參考款'},
    'recommendation_zh':recommendation,'recommend_reprinting_for_stronger_blowing':not small,
    'recommended_design':None if small else 'short216',
    'same_area_fine_dynamic_pressure_gain_pct_3_5_8cm':gains,
    'hypothetical_inlet_total_pressure_Pa':400,'actual_fan_curve_used':False,
    'actual_slicing_verified':False,'physical_print_verified':False,'drying_performance_verified':False,
    'owned_solver_exit_confirmed':True,'printpack_name':'K1C_HeadOnly_16mm_Compared_Prototypes.zip'}
(ROOT/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
deliver()
print('COMPARISON_AND_DELIVERY_COMPLETED',flush=True)
