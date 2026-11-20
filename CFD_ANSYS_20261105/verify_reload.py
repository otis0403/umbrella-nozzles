"""Reopen each delivered Fluent case/data pair and compare native reports."""
import json
from session import ROOT,connect

s=connect(cleanup=True)
checks=[]
for relative in ['medium/Q0.50','medium/Q1.00','medium/Q1.50','fine/Q1.00']:
    case=ROOT/relative
    expected=json.loads((case/'results.json').read_text())['reports_SI']
    s.settings.file.read_case_data(file_name=str(case/'review.cas.h5'))
    reports=s.settings.solution.report_definitions.compute(report_defs=['pin','ptin','ptout','min','mout'])
    actual={k:v[0] for item in reports for k,v in item.items()}
    error=max(abs(actual[k]-expected[k])/max(abs(expected[k]),1e-8) for k in expected)
    assert error<1e-8,(relative,error)
    row={'case':relative,'native_case_data_reopen_success':True,'max_report_relative_difference':error,
         'expected_reports':expected,'reopened_reports':actual}
    checks.append(row)
    (ROOT/'reopen_verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('REOPEN_VERIFIED',relative,error,flush=True)
s.exit(timeout=10,wait=15)
print('FLUENT_EXITED_AND_LICENSE_RELEASED',flush=True)
