import hashlib
import json
import zipfile
from pathlib import Path
from build_mesh import ROOT,SOURCE

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
    return h.hexdigest()

required=[ROOT/'medium'/f'Q{q:.2f}' for q in [.5,1.,1.5]]+[ROOT/'fine'/'Q1.00']
for case in required:
    assert json.loads((case/'convergence.json').read_text())['engineering_convergence_pass'],case
    assert (case/'review.cas.h5').exists() and (case/'review.dat.h5').exists(),case
assert (ROOT/'README.md').exists()
reopened=json.loads((ROOT/'reopen_verification.json').read_text())
assert len(reopened)==4 and all(x['native_case_data_reopen_success'] for x in reopened)
(ROOT/'source_geometry.py').write_bytes(SOURCE.read_bytes())
files=list(ROOT.glob('*.py'))
files += [ROOT/n for n in ['README.md','blower_input.json','comparison.csv','outlet_profiles.png',
                          'mesh_sensitivity.json','source_integrity.json','exported_data_checks.json','python_environment.txt',
                          'reopen_verification.json','reopen_verification.log','solver_shutdown.json']]
files += sorted(ROOT.glob('*_run*.log'))
files += sorted(ROOT.glob('*_post.log'))
for level in ['coarse','medium','fine']:
    files.append(ROOT/level/'mesh_summary.json')
    for case in sorted((ROOT/level).glob('Q*')):
        files += [p for p in case.iterdir() if p.suffix in ['.json','.npz','.csv','.png']]
        if level=='coarse': files += [case/'solution.cas.h5',case/'solution.dat.h5']
        else: files += [case/'review.cas.h5',case/'review.dat.h5']
files=sorted(set(files))
manifest={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}
mp=ROOT/'delivery_manifest.json'
mp.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
files.append(mp)
archive=ROOT/'ANSYS_216x12mm_no_core_20261105.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p in files:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(files)
    # Verify extracted bytes against the manifest for each payload.
    for name,entry in manifest.items():
        h=hashlib.sha256()
        with z.open(name.replace('\\','/')) as f:
            for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
        assert h.hexdigest()==entry['sha256'],name
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),
                  'sha256':digest(archive),'zip_crc_and_payload_hashes_verified':True},indent=2))
summary_files=[p for p in files if p.suffix in ['.md','.png','.csv']
               or p.name in ['mesh_sensitivity.json','blower_input.json','convergence.json','results.json']]
summary_archive=ROOT/'CFD_report_and_images_20261105.zip'
with zipfile.ZipFile(summary_archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p in summary_files:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(summary_archive) as z:assert z.testzip() is None
print(json.dumps({'summary_archive':str(summary_archive),'bytes':summary_archive.stat().st_size,
                  'files':len(summary_files),'zip_crc_verified':True}))
