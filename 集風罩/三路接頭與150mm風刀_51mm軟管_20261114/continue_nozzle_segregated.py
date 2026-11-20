"""An isolated native continuation with SIMPLE, preserving the Coupled case."""
import json,shutil,hashlib,time
from geometry import ROOT
from legacy_study import connect
from resume_nozzle import resume
from analyze import convergence

while not (ROOT/'STAGE_53_COMPLETE.json').exists():time.sleep(3)
assert not (ROOT/'plan_54.json').exists(),'Main controller must be idle'
status=convergence().get('final_jet_fine',{})
if status.get('engineering_convergence_pass'):
    print('FINE_COUPLED_CASE_CONVERGED_NO_ALTERNATE_NEEDED',flush=True)
    raise SystemExit(0)
source=ROOT/'cfd/final_jet_fine';target=ROOT/'cfd/final_jet_fine_segregated'
assert not target.exists(),'Do not overwrite an existing continuation'
target.mkdir()
for name in ['solution.cas.h5','solution.dat.h5','results.json','history.json','mesh_summary.json','boundary_conditions.json']:
    shutil.copyfile(source/name,target/name)
    assert hashlib.sha256((source/name).read_bytes()).digest()==hashlib.sha256((target/name).read_bytes()).digest()
for filename in ['results.json','mesh_summary.json']:
    p=target/filename;r=json.loads(p.read_text());r['name']=target.name;r['source_native_case']=source.name
    p.write_text(json.dumps(r,indent=2),encoding='utf-8')
(target/'initial_state_provenance.json').write_text(json.dumps(dict(source=source.name,native_case_and_data_copied_then_really_iterated=True),indent=2),encoding='utf-8')
s=connect(launch=False,cleanup=False)
resume(s,dict(name=target.name,batches=15,adaptive=True,flow_scheme='SIMPLE'))
print('SEGREGATED_NATIVE_CONTINUATION_COMPLETE',flush=True)
