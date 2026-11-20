"""Analytic screening only: no new CFD, no CAD changes.

Retain fitted nozzle loss, hose/connector losses and calibrated distributor loss.
Change only mean exit kinetic pressure for a new inner/middle gap.
This neglects changes in separation, contraction loss and profile uniformity.
"""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'Outer315_NarrowGap_ANSYS_20261117'
baseline=json.loads((SOURCE/'cfd/network_narrow_Ps460_hose60/results.json').read_text())
curves=json.loads((SOURCE/'selected_pressure_curves.json').read_text())
rho=1.2
widths=np.array([225.,180.,315.])
old_gaps=np.array([16.,16.,8.])
q0=np.array(baseline['branch_flow_m3_min'])
pin=baseline['reports']['pin']
pt=baseline['reports']['ptin']
inlet_coefficient=(pt-pin)/q0.sum()**2
adapter_coefficients=(pt-np.array(baseline['physical_port_total_pressure_Pa']))/q0**2
pipe_area=np.pi*.051**2/4
joint_area=np.pi*.046**2/4
pipe_coefficients=rho/2/(60*pipe_area)**2*(.04*(.6-.05)/.051+.5)
joint_coefficients=.15*rho/2/(60*joint_area)**2
a0=np.array([curves[str(int(w))]['a'] for w in widths])
b0=np.array([curves[str(int(w))]['b'] for w in widths])
def calculate(gaps):
    gaps=np.asarray(gaps,dtype=float)
    old_area=widths*old_gaps*1e-6
    new_area=widths*gaps*1e-6
    correction=rho/2*((1/(60*new_area))**2-(1/(60*old_area))**2)
    a=a0+correction+pipe_coefficients+joint_coefficients+adapter_coefficients
    def flows(total_pressure):
        return 2*total_pressure/(b0+np.sqrt(b0*b0+4*a*total_pressure))
    total_pressure=brentq(lambda p:p-pin-inlet_coefficient*flows(p).sum()**2,10,4000)
    q=flows(total_pressure)
    return {'gaps_mm':gaps.tolist(),'flows_m3_min':q.tolist(),'mean_slot_speed_m_s':(q/60/new_area).tolist(),
            'total_flow_m3_min':float(q.sum()),'inlet_total_pressure_Pa':total_pressure,
            'inlet_static_pressure_Pa':pin,'new_ANSYS_simulation':False,'CAD_changed':False}

rows=[calculate(gaps) for gaps in [[16,16,8],[14,14,8],[12,14,8],[12,12,8],[14,12,8]]]
baseline_error=np.max(abs(np.array(rows[0]['flows_m3_min'])/q0-1))*100
assert baseline_error<.2,baseline_error
summary={'method':'one-dimensional calibrated loss network plus mean exit kinetic-pressure correction',
         'source_root':str(SOURCE),'assumed_hose_cuts_m':[.6,.6,.6],
         'baseline_reproduction_max_branch_flow_difference_pct':float(baseline_error),
         'limitation':'calibration is not independent validation; changed nozzle losses and fan P-Q are unverified',
         'results':rows}
(ROOT/'screen_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
flat=[{'inner_gap_mm':r['gaps_mm'][0],'center_gap_mm':r['gaps_mm'][1],'outer_gap_mm':r['gaps_mm'][2],
       'inner_mean_speed_m_s':r['mean_slot_speed_m_s'][0],'center_mean_speed_m_s':r['mean_slot_speed_m_s'][1],
       'outer_mean_speed_m_s':r['mean_slot_speed_m_s'][2],'total_flow_m3_min':r['total_flow_m3_min'],
       'new_ANSYS_simulation':False} for r in rows]
with (ROOT/'screen_results.csv').open('w',newline='',encoding='utf-8-sig') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
print(json.dumps(flat,indent=2),flush=True)
