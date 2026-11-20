"""Stop only after two batches satisfy the published engineering criteria."""
import os,re
from pathlib import Path
PAT=re.compile(r'^\s*(\d+)\s+((?:[\d.eE+\-]+\s+){5}[\d.eE+\-]+)\s+\d+:\d+:\d+',re.M)

def ready(history,outlet_names):
    if len(history)<4:return False
    path=Path(os.environ.get('CFD_ACTIVE_LOG','fluent_final.log'))
    if not path.exists():return False
    with path.open('rb') as f:
        bom=f.read(2)
        offset=max(0,path.stat().st_size-70000)
        if bom==b'\xff\xfe': offset-=offset%2
        f.seek(offset)
        text=f.read().decode('utf-16-le' if bom==b'\xff\xfe' else 'utf-8',errors='ignore')
    rows=list(PAT.finditer(text))
    if not rows:return False
    last=[float(v) for v in rows[-1][2].split()];a,b=history[-2:]
    names=outlet_names or ['min'];dq=max(100*abs(b[k]-a[k])/max(abs(a[k]),1e-8) for k in names)
    key='ptin' if 'ptin' in a else 'pin'
    dp=100*abs(b[key]-a[key])/max(abs(b[key]),1e-8)
    mass=100*abs(b['min']+sum(b[k] for k in outlet_names))/abs(b['min'])
    return bool(last[0]<1e-4 and max(last[1:4])<1e-6 and max(last[4:])<1e-5 and dq<.5 and dp<.5 and mass<.1)
