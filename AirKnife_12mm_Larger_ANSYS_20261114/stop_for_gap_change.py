"""Close only this task's privately recorded Fluent session after user steering."""
import json
from geometry import ROOT
from study import connect
note={'date':'2026-11-14','reason':'User changed requested outlet gap from 12 mm back to 16 mm',
    'completed_12mm_cases':[p.parent.name for p in (ROOT/'cfd').glob('*/results.json')],
    'partial_12mm_study_not_a_final_deliverable':True}
(ROOT/'USER_STEERING_TO_16MM.json').write_text(json.dumps(note,indent=2),encoding='utf-8')
s=connect(cleanup=True)
s.exit(timeout=30,wait=20)
print('OWNED_12MM_SOLVER_EXIT_REQUESTED_FOR_USER_STEERING',flush=True)
