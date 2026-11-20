"""Tighten linear solution tolerances for the active final fine nozzle only."""
import json
from datetime import datetime,timezone
from geometry import ROOT
from legacy_study import connect

p=ROOT/'cfd/final_jet_fine';meta=json.loads((p/'mesh_summary.json').read_text())
assert meta['cells']==830112 and not (ROOT/'STAGE_52_COMPLETE.json').exists()
s=connect(launch=False,cleanup=False)
v=s.fields.solution_variable_data.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
assert len(v)==830112 and v.min()>0
mg=s.settings.solution.controls.advanced.multi_grid.mg_controls
before=mg.get_state()
for name in ['k','omega','pressure-coupled']:
    assert name in before
    mg[name].termination_criteria=.01
after=mg.get_state()
record=dict(UTC=datetime.now(timezone.utc).isoformat(),verified_native_cells=len(v),before=before,after=after,
    only_inner_linear_tolerances_changed=True,outer_convergence_thresholds_unchanged=True,
    geometry_flow_and_physical_boundary_conditions_unchanged=True)
(p/'linear_solver_adjustment.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('FINE_LINEAR_SOLVER_TOLERANCES_UPDATED',json.dumps(record),flush=True)
