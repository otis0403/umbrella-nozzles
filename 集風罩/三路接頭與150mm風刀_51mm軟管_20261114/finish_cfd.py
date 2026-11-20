"""Verify selected converged native cases, then release the owned Fluent session."""
import json,sys,time
from geometry import ROOT
from analyze import convergence,jet_metrics

fine=sys.argv[1];stage=int(sys.argv[2]);prototype='--prototype' in sys.argv
assert not (ROOT/f'plan_{stage}.json').exists()
cv=convergence()
pipe={k:'final_adapter_'+k for k in ['100_120','60_80','50_70']}
jets={k:'final_jet_'+k for k in pipe}
curves=['curve_selected_P22_q1','curve_selected_P22_q2.5']
sens=['final_pressure200','final_friction_low','final_friction_high','final_short_pipe_more_bends','final_one_side_extra_bend']
reference='reference_final_old_layout'
primary=curves+list(pipe.values())+sens+[reference]+list(jets.values())+['final_adapter_fine']
fine_converged=cv.get(fine,{}).get('engineering_convergence_pass',False)
assert prototype or fine_converged,'Fine case has not passed convergence'
assert all(cv.get(n,{}).get('engineering_convergence_pass') for n in primary),[(n,cv.get(n)) for n in primary if not cv.get(n,{}).get('engineering_convergence_pass')]
cases=primary+[fine];validated=primary+([fine] if fine_converged else [])
metrics=[jet_metrics(n) for n in list(jets.values())+[fine]]
maximum_cv=max(m[f'{d}mm']['core_140mm_line_CV_pct'] for m in metrics for d in [30,50,80])
selection=dict(date='2026-11-14',adapter_height_mm=110.,neck_mm=46.,nozzle_gap_mm=16,nozzle_span_mm=150,
    nozzle_length_mm=120,nozzle_shoulder_mm=150,nozzle_plenum_mm=22,pipe_cases=pipe,jet_cases=jets,
    fine_adapter_case='final_adapter_fine',fine_jet_case=fine,reference_case=reference,sensitivity_cases=sens,
    validation_cases=validated,diagnostic_cases=[] if fine_converged else [fine],fine_nozzle_converged=fine_converged,
    nozzle_uniformity_target_met=fine_converged and maximum_cv<=10,maximum_nozzle_CV_pct=maximum_cv,
    actual_fan_curve_used=False,hypothetical_reference_total_pressure_Pa=400,physical_testing_complete=False,
    physical_pipe_lengths_include_25mm_insertion_each_end=True,
    fine_nozzle_numerical_method='SIMPLE native continuation' if fine.endswith('segregated') else 'Coupled native continuation',
    delivery_scope='user_selected_printable_prototype_and_report' if prototype else 'converged_selected_cases')
(ROOT/'final_selection.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
plan=dict(jobs=[dict(kind='verify',name='verify_selected_native_cases',cases=cases)],final=True)
path=ROOT/f'plan_{stage}.json';temporary=path.with_suffix('.json.tmp')
temporary.write_text(json.dumps(plan,indent=2),encoding='utf-8');temporary.replace(path)
while not (ROOT/f'STAGE_{stage}_COMPLETE.json').exists():time.sleep(3)
while 'OWNED_SOLVER_EXIT_COMPLETED' not in (ROOT/'fluent_final.log').read_text(encoding='utf-8',errors='replace'):time.sleep(2)
(ROOT/'CFD_VALIDATION_FINISHED.json').write_text(json.dumps(dict(selection=selection,owned_solver_exit_confirmed=True,primary_cases_engineering_converged=True,
    fine_nozzle_converged=fine_converged,diagnostic_case_not_counted_as_validated=not fine_converged),indent=2),encoding='utf-8')
print('CFD_ALL_SELECTED_CASES_VALIDATED',json.dumps(selection),flush=True)
