import json
import re
from session import ROOT

pattern=re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+',re.M)
for level in ['coarse','medium','fine']:
    for case in sorted((ROOT/level).glob('Q*')):
        q=float(case.name[1:])
        code={.5:'0p5',1.:'1',1.5:'1p5'}[q]
        logs=sorted(ROOT.glob(f'{level}_Q{code}_*run*.log'))
        records=[]
        for p in logs:
            raw=p.read_bytes()
            txt=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
            for m in pattern.finditer(txt):
                records.append([int(m[1])]+[float(v) for v in m[2].split()])
        if not records: continue
        hist=json.loads((case/'history.json').read_text())
        values=[{k:v[0] for item in h['reports'] for k,v in item.items()} for h in hist]
        pt=[h['ptin']-h['ptout'] for h in values]
        pin=[h['pin'] for h in values]
        mass=abs(values[-1]['min']+values[-1]['mout'])/abs(values[-1]['min'])*100
        change=lambda vals:100*abs(vals[-1]-vals[-2])/max(abs(vals[-1]),1e-12) if len(vals)>1 else None
        last=records[-1]
        residuals=dict(zip(['continuity','x_velocity','y_velocity','z_velocity','k','omega'],last[1:]))
        result={'iteration':last[0],'last_residuals':residuals,
                'strict_all_residuals_lt_1e_minus_5':max(last[1:])<1e-5,
                'last_report_interval_pin_change_pct':change(pin),
                'last_report_interval_pressure_loss_change_pct':change(pt),
                'mass_imbalance_pct':mass,
                'engineering_convergence_criteria':{'continuity_lt':1e-4,'velocity_residuals_lt':1e-6,
                    'k_omega_residuals_lt':1e-5,'pressure_change_pct_lt':.5,'mass_imbalance_pct_lt':.1},
                'engineering_convergence_pass':(last[1]<1e-4 and max(last[2:5])<1e-6
                    and max(last[5:])<1e-5 and mass<.1 and change(pin) is not None
                    and change(pin)<.5 and change(pt)<.5),
                'source_logs':[p.name for p in logs]}
        (case/'convergence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        with (case/'residual_history.csv').open('w',encoding='ascii') as f:
            f.write('iteration,continuity,x_velocity,y_velocity,z_velocity,k,omega\n')
            for row in records: f.write(','.join(str(v) for v in row)+'\n')
        print(level,case.name,json.dumps(result))
