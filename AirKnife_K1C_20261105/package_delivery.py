"""Package explicit deliverables; never include credentials, launcher files, or logs."""
import hashlib,json,zipfile
from geometry import ROOT

selected=[]
for pattern in ['*.md','*.csv','*.py','design_summary.json','source_integrity.json',
                'cad/*.json','cad/*.blend','cad/reference/*.stl','print/**/*.stl','print/**/*.3mf',
                'print/*.json','images/*.png','cfd/*.json','cfd/*/results.json',
                'cfd/*/convergence.json','cfd/*/mesh_summary.json','cfd/*/history.json',
                'cfd/*/*.csv','cfd/*/*.png']:
    selected.extend(ROOT.glob(pattern))
selected=sorted(set(p for p in selected if p.is_file()),key=lambda p:p.relative_to(ROOT).as_posix())
assert not any(p.suffix in ['h5','.npz'] for p in selected)
assert all(ROOT in p.resolve().parents for p in selected)
assert all('connection' not in p.name.lower() and 'serverinfo' not in p.name.lower() for p in selected)
for required in ['cad/native_model_reopen.json','print/independent_readback_checks.json','cfd/reopen_checks.json']:
    assert ROOT/required in selected,required
manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in selected)
(ROOT/'MANIFEST.sha256').write_text(manifest,encoding='utf-8')
selected.append(ROOT/'MANIFEST.sha256')
dest=ROOT/'K1C_AirKnife_260mm_8-12-16mm_PrintPack.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in selected:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for p in selected:
        assert hashlib.sha256(z.read(p.relative_to(ROOT).as_posix())).digest()==hashlib.sha256(p.read_bytes()).digest()
    members=z.namelist()
    assert len(members)==len(set(members))
    assert not any(n.startswith('/') or '..' in n.split('/') for n in members)
report={'file':dest.name,'files':len(selected),'size_bytes':dest.stat().st_size,
    'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'zip_CRC_pass':True,
    'each_member_hash_matches_delivered_source':True,'raw_CFD_case_data_included':False,
    'raw_CFD_retained_locally_at':'cfd/','actual_slicing_or_print_verified':False}
(ROOT/'package_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
