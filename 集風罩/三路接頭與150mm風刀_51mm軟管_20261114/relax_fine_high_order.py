"""Stabilize deferred high-order terms without changing the final scheme."""
import json
from datetime import datetime,timezone
from geometry import ROOT
from legacy_study import connect

p=ROOT/'cfd/final_jet_fine'
assert not (ROOT/'STAGE_53_COMPLETE.json').exists()
s=connect(launch=False,cleanup=False)
v=s.fields.solution_variable_data.get_data(variable_name='SV_VOLUME',zone_names=['fluid'])['fluid']
assert len(v)==830112 and v.min()>0
methods=s.settings.solution.methods
before=methods.get_state()
control=methods.high_order_term_relaxation
control.enable=True;control.relaxation_factor=.25;control.select_variables='all-variables'
after=methods.get_state()
assert before['spatial_discretization']==after['spatial_discretization']
record=dict(UTC=datetime.now(timezone.utc).isoformat(),verified_native_cells=len(v),before=before,after=after,
    second_order_spatial_schemes_unchanged=True,only_iterative_high_order_term_relaxation_changed=True,
    geometry_inlet_flow_and_physical_boundaries_unchanged=True)
(p/'high_order_iteration_adjustment.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('FINE_HIGH_ORDER_RELAXATION_UPDATED',json.dumps(record),flush=True)
