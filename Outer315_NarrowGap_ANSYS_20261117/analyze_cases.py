"""Extract quantities from Fluent field exports and identify convergence status."""
import csv
import json
import re
import numpy as np
from scipy.interpolate import LinearNDInterpolator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from design import ROOT, write_json

RESIDUAL = re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+')


def convergence_records():
    records = {}
    for path in ROOT.glob('*fluent.log'):
        current = None
        residual = None
        raw=path.read_bytes()
        log_text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
        for line in log_text.splitlines():
            if line.startswith('MESH_READY '):
                current = re.split(r'[\\/]', line.split()[1])[-1]
                residual = None
            match = RESIDUAL.match(line)
            if match:
                residual = [float(x) for x in match[2].split()]
            if line.startswith(('CASE_COMPLETE ','NETWORK_COMPLETE ')):
                _, name, payload = line.split(' ', 2)
                result = json.loads(payload)
                if residual is None:
                    continue
                history = json.loads((ROOT/'cfd'/name/'history.json').read_text())
                dp = 100*abs(history[-1]['ptin']-history[-2]['ptin'])/max(abs(history[-1]['ptin']), 1e-9)
                passed = residual[0] < 1e-4 and max(residual[1:4]) < 1e-6 and max(residual[4:]) < 1e-5 and dp < .5 and result['mass_imbalance_pct'] < .1
                records[name] = {'residuals': dict(zip(['continuity','Ux','Uy','Uz','k','omega'],residual)),
                                 'last_total_pressure_change_pct': dp, 'engineering_convergence_pass': bool(passed),
                                 'mass_imbalance_pct': result['mass_imbalance_pct'], 'source_log': path.name}
    return records


def analyze():
    convergence = convergence_records()
    rows = []
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for path in sorted((ROOT/'cfd').glob('*/results.json')):
        result = json.loads(path.read_text())
        if 'nozzle_flow_m3_min' not in result:
            continue
        external=result['conditions'].get('external_free_jet',False)
        fields = np.load(path.parent/('slot_fields.npz' if external else 'outlet_fields.npz'))
        width = result['conditions']['span_mm']
        xy = fields['centroids'][:, :2]*1000
        velocity = fields['z-velocity']
        areas=fields['areas']
        if external:
            mask=(abs(xy[:,0])<result['conditions']['gap_mm']/2+.001)&(abs(xy[:,1])<width/2+.001)
            xy=xy[mask];velocity=velocity[mask];areas=areas[mask]
        f = LinearNDInterpolator(xy, velocity)
        y = np.linspace(-width/2+5, width/2-5, 181)
        line = f(np.c_[np.zeros(len(y)), y])
        assert np.isfinite(line).all()
        mean = float(line.mean())
        row = {'case': path.parent.name, 'width_mm': width, 'gap_mm':result['conditions']['gap_mm'], 'flow_m3_min': result['nozzle_flow_m3_min'],
               'inlet_total_pressure_Pa': result['reports']['ptin'], 'total_pressure_loss_Pa': result['pressure_loss_to_domain_outlet_Pa'],
               'slot_area_mean_velocity_m_s': float(np.average(velocity,weights=areas)),
               'core_line_CV_pct': float(line.std()/mean*100), 'core_line_mean_velocity_m_s': mean,
               'full_slot_area_CV_pct': float(np.sqrt(np.average((velocity-np.average(velocity,weights=areas))**2,weights=areas))/np.average(velocity,weights=areas)*100),
               'body_reverse_volume_pct': result.get('nozzle_body_reverse_axial_volume_pct'),
               'engineering_convergence_pass': convergence.get(path.parent.name,{}).get('engineering_convergence_pass',False)}
        write_json(path.parent/'profile_metrics.json', row)
        np.savetxt(path.parent/'outlet_centerline.csv', np.c_[y,line], delimiter=',', header='Y_mm,Uz_m_s', comments='')
        if path.parent.name.startswith(('screen_','ramp_','guide_')):
            ax.plot(y/width, line/mean, label=path.parent.name, linewidth=1.3)
        rows.append(row)
    if rows:
        ax.set(xlabel='Position / outlet width', ylabel='Axial velocity / line mean', title='Normalized nozzle outlet profiles')
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(ROOT/'images/screen_profiles.png', dpi=170)
        with (ROOT/'screen_comparison.csv').open('w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
    plt.close(fig)
    write_json(ROOT/'convergence_summary.json', convergence)
    write_json(ROOT/'screen_comparison.json', rows)
    print(json.dumps(rows, indent=2), flush=True)


if __name__ == '__main__':
    analyze()
