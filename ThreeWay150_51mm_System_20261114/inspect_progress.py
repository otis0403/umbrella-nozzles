"""Small read-only status view; never connects to the active solver."""
import json,re
from pathlib import Path

root=Path(__file__).resolve().parent
for p in sorted((root/'cfd').glob('final_*/results.json'),key=lambda p:p.stat().st_mtime):
    r=json.loads(p.read_text());c=p.parent/'convergence.json'
    cv=json.loads(c.read_text()).get('engineering_convergence_pass') if c.exists() else None
    print(json.dumps(dict(case=p.parent.name,Q=r.get('total_flow_m3_min',r.get('nozzle_flow_m3_min')),
        balance_pct=r.get('balance_error_pct'),load_pass=r.get('network_load_consistency_pass'),convergence_pass=cv)))
active_log=max(root.glob('fluent*.log'),key=lambda p:p.stat().st_mtime)
print('ACTIVE_LOG',active_log.name)
with active_log.open('rb') as f:
    f.seek(max(0,active_log.stat().st_size-18000));tail=f.read().decode('utf-8',errors='replace')
matches=re.findall(r'CASE_(?:PROGRESS|COMPLETE)\s+(\S+)',tail)
if matches:print('LATEST_REPORTED_CASE',matches[-1])
residuals=re.findall(r'^\s*(\d+)\s+([\d.eE+\-]+(?:\s+[\d.eE+\-]+){5})\s+\d+:\d+:\d+',tail,re.M)
if residuals:print('LAST_ITERATION_AND_RESIDUALS',*residuals[-1])
latest_coordinator=max(root.glob('auto_after_adapters*.log'),key=lambda p:p.stat().st_mtime)
for name in [latest_coordinator.name,'finish_print_delivery_refined.log']:
    p=root/name
    if p.exists():print(name, '\n'.join(p.read_text(encoding='utf-8',errors='replace').splitlines()[-2:]))
