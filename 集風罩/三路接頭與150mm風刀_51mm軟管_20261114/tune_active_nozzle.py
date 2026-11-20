"""Apply only iterative controls to the verified active final fine-nozzle mesh."""
import json
from datetime import datetime,timezone
from geometry import ROOT
from legacy_study import connect

case=ROOT/'cfd/final_jet_fine'
meta=json.loads((case/'mesh_summary.json').read_text())
assert meta['fine'] and meta['external'] and meta['gap_mm']==16 and meta['cells']==830112
assert not (ROOT/'STAGE_52_COMPLETE.json').exists()
solver=connect(launch=False,cleanup=False)
volumes=solver.fields.solution_variable_data.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
assert len(volumes)==meta['cells'] and volumes.min()>0
assert 'ambient' in solver.settings.setup.boundary_conditions.pressure_outlet.get_object_names()
pseudo=solver.settings.solution.run_calculation.pseudo_time_settings.time_step_method
relax=solver.settings.solution.controls.pseudo_time_explicit_relaxation_factor.global_dt_pseudo_relax
before=dict(pseudo_time=pseudo.get_state(),relaxation=relax.get_state())
pseudo.time_step_size_scale_factor=.1
for equation in ['k','omega']:relax[equation]=.5
after=dict(pseudo_time=pseudo.get_state(),relaxation=relax.get_state())
record=dict(UTC=datetime.now(timezone.utc).isoformat(),verified_native_cells=len(volumes),before=before,after=after,
    only_iterative_controls_changed=True,geometry_inlet_flow_and_boundary_conditions_unchanged=True,
    requested_during_controller_solve=True)
(case/'iteration_control_adjustment.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('ACTIVE_FINE_NOZZLE_CONTROLS_UPDATED',json.dumps(record),flush=True)
# Do not close the solver owned by run_solver.py.
