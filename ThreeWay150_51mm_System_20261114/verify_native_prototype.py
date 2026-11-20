"""Read saved files in a fresh solver, without running any iterations."""
import json,time,socket
from geometry import ROOT
from legacy_study import connect,reports,PRIVATE
from analyze import convergence

sel=json.loads((ROOT/'final_selection.json').read_text());cv=convergence()
assert all(cv[n]['engineering_convergence_pass'] for n in sel['validation_cases'])
cases=sel['validation_cases']+sel.get('diagnostic_cases',[])
s=connect(launch=True,cleanup=True);connection=json.loads(PRIVATE.read_text());rows=[];exit_warning=None
try:
    for name in cases:
        p=ROOT/'cfd'/name;r=json.loads((p/'results.json').read_text())
        s.settings.file.read_case_data(file_name=str(p/'solution.cas.h5'))
        names=['pin','ptin','min']+([f'm{k}' for k in range(3)] if 'branch_flow_m3_min' in r else ['mout'])
        values=reports(s,names)
        errors={k:abs(values[k]-r['reports'][k])/max(abs(r['reports'][k]),1e-8) for k in names}
        row=dict(case=name,native_case_data_reopened=True,maximum_relative_error=max(errors.values()),relative_errors=errors,
            engineering_convergence_pass=cv[name]['engineering_convergence_pass'],diagnostic_only=name in sel.get('diagnostic_cases',[]))
        rows.append(row);(ROOT/'native_reopen_checks.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print('NATIVE_READBACK',json.dumps(row),flush=True)
        assert row['maximum_relative_error']<1e-8,(name,row)
finally:
    try:s.exit(timeout=15,wait=20)
    except Exception as exc:exit_warning=type(exc).__name__

closed=False
for _ in range(10):
    try:probe=socket.create_connection((connection['ip'],connection['port']),1);probe.close()
    except OSError:closed=True;break
    time.sleep(1)
assert closed,'Owned verification solver did not close'
state=dict(selection=sel,owned_solver_exit_confirmed=True,primary_cases_engineering_converged=True,
    fine_nozzle_converged=sel['fine_nozzle_converged'],diagnostic_case_not_counted_as_validated=not sel['fine_nozzle_converged'],
    native_readback_in_fresh_session=True,shutdown_warning_type=exit_warning)
(ROOT/'CFD_VALIDATION_FINISHED.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('NATIVE_PROTOTYPE_FILES_VERIFIED_AND_SOLVER_CLOSED',flush=True)
