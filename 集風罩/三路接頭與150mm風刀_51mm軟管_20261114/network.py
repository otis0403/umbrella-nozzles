"""Pipe resistance plus measured CFD nozzle curves; gauge total pressures."""
import json,math
import numpy as np
from scipy.optimize import nnls
from geometry import ROOT
RHO=1.2;MU=1.8e-5;A46=math.pi*.046**2/4;A51=math.pi*.051**2/4

def curves():
    result={}
    for gap in [4,6,8,12]:
        points=[]
        for q in [1.,1.8]:
            r=json.loads((ROOT/f'cfd/curve_g{gap}_q{q:g}/results.json').read_text())
            points.append([r['nozzle_flow_m3_min'],r['reports']['ptin']])
        a=np.asarray(points);coeff,_=nnls(np.c_[a[:,0]**2,a[:,0]],a[:,1]);pred=coeff[0]*a[:,0]**2+coeff[1]*a[:,0]
        result[str(gap)]=dict(a_Pa_per_Q2=float(coeff[0]),b_Pa_per_Q=float(coeff[1]),points=points,max_fit_error_pct=float(np.max(abs(pred/a[:,1]-1))*100))
    (ROOT/'nozzle_pressure_curves.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result

def loads(gap,center_length=1.,side_length=1.2,friction=.04,bend=.5,area=A46):
    curve=json.loads((ROOT/'nozzle_pressure_curves.json').read_text())[str(int(gap))];conversion=60*area
    output=[]
    for k,length in enumerate([side_length,center_length,side_length]):
        bend_k=float(bend[k]) if isinstance(bend,(list,tuple)) else float(bend)
        k_pipe=(friction*length/.051+bend_k)*(area/A51)**2
        k_joint=.15 # Assumed combined step/connection minor losses; not measured.
        linear=curve['b_Pa_per_Q']*conversion
        quadratic=curve['a_Pa_per_Q2']*conversion**2+.5*RHO*(k_pipe+k_joint-1)
        assert quadratic>0
        output.append(dict(length_m=length,linear_Pa_per_velocity=linear,quadratic_Pa_per_velocity2=quadratic,
            permeability_m2=MU*.001/linear if linear>1e-12 else 1e20,c2_per_m=quadratic/(.5*RHO*.001),thickness_m=.001,
            hose_K_referred_to_port=k_pipe,bend_K_assumed=bend_k,joint_K_assumed=k_joint,exit_kinetic_energy_correction_included=True))
    return output

if __name__=='__main__':print(json.dumps(curves(),indent=2))
