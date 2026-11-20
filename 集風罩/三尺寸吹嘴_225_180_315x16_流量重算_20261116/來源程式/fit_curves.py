import json
import time
import numpy as np
from scipy.optimize import nnls

from design import ROOT, write_json

while (ROOT/'refine315.hold').exists():
    time.sleep(5)

SOURCES = {
    180: ['curve_w180_q1p2','ramp_w180_L180','curve_w180_q2p4','curve_w180_q4p0'],
    225: ['curve_w225_q1p3','ramp_w225_L220','curve_w225_q4p0'],
    315: ['guide_w315_q1p5','guide_w315_L320','guide_w315_q4p5'],
}
curves = {}
for width, names in SOURCES.items():
    points = []
    for name in names:
        result = json.loads((ROOT/'cfd'/name/'results.json').read_text())
        history = json.loads((ROOT/'cfd'/name/'history.json').read_text())
        pressure = np.array([v['ptin'] for v in history[-8:]])
        points.append({'case':name,'Q_m3_min':result['nozzle_flow_m3_min'],'required_total_Pa':result['reports']['ptin'],
                       'late_iteration_pressure_range_pct':float(np.ptp(pressure)/pressure.mean()*100)})
    q = np.array([p['Q_m3_min'] for p in points])
    p = np.array([p['required_total_Pa'] for p in points])
    coefficients, _ = nnls(np.c_[q*q,q]/p[:,None], np.ones(len(p)))
    prediction = coefficients[0]*q*q + coefficients[1]*q
    curves[str(width)] = {'a':float(coefficients[0]),'b':float(coefficients[1]),'units':'Pa; Q in m3/min',
                          'fit':'P_total = a Q^2 + b Q','points':points,
                          'maximum_fit_error_pct':float(np.max(abs(prediction/p-1))*100),
                          'includes_feed_elbow_R90':True,'inlet_ID_mm':51,'gap_mm':16,
                          'actual_fan_operating_point_verified':False}
write_json(ROOT/'selected_pressure_curves.json',curves)
write_json(ROOT/'selection.json',{
    'inner':{'width_mm':225,'gap_mm':16,'length_mm':220,'height_mm':288,'profile_kind':'ramp','case':'ramp_w225_L220'},
    'center':{'width_mm':180,'gap_mm':16,'length_mm':180,'height_mm':248,'profile_kind':'ramp','case':'ramp_w180_L180'},
    'outer':{'width_mm':315,'gap_mm':16,'length_mm':320,'height_mm':388,'profile_kind':'ramp','guided':True,'guide_count':2,'case':'guide_w315_L320'},
    'printer_capacity_is_not_a_design_constraint_this_stage':True,
    'selection_status':'flow-oriented complete nozzle prototypes; numerical convergence and physical tests reported separately'
})
print('NEW_PRESSURE_CURVES_FITTED',json.dumps(curves,indent=2),flush=True)
