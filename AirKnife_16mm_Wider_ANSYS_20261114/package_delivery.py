import hashlib,json,zipfile
from geometry import ROOT
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel in ['selection.json','cad/native_reopen_check.json','print/independent_readback_checks.json','cfd/reopen_checks.json']:
    assert (ROOT/rel).exists(),rel
files=[]
for pattern in ['*.py','*.md','*.csv','*.txt','selection.json','source_integrity.json','source_integrity_start.json','case_matrix.json',
    'cad/*.json','cad/*.blend','cad/reference/*.stl','print/**/*.stl','print/**/*.3mf','print/*.json',
    'images/*.png','cfd/*.json','cfd/*/results.json','cfd/*/history.json','cfd/*/mesh_summary.json',
    'cfd/*/convergence.json','cfd/*/*.csv','cfd/*/*.png']:
    files.extend(p for p in ROOT.glob(pattern) if p.is_file())
files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
assert all('serverinfo' not in p.name.lower() and 'connection' not in p.name.lower() for p in files)
(ROOT/'MANIFEST.sha256').write_text(''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files),encoding='utf-8')
files.append(ROOT/'MANIFEST.sha256');dest=ROOT/'K1C_252x16_Wider_ANSYS_PrintPack.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for p in files:assert hashlib.sha256(z.read(p.relative_to(ROOT).as_posix())).hexdigest()==sha(p)
report={'file':dest.name,'files':len(files),'bytes':dest.stat().st_size,'sha256':sha(dest),'zip_CRC_pass':True,
    'every_member_hash_matches':True,'raw_CFD_kept_locally':'cfd/','raw_CFD_in_ZIP':False,
    'actual_slicing_verified':False,'physical_print_verified':False}
(ROOT/'package_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
