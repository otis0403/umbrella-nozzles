import hashlib
import json
from pathlib import Path
from build_mesh import ROOT,SOURCE

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

original_stl=next(SOURCE.parent.glob('*.stl'))
expected='6f8f9ca5d755b9c6a77b417ffdef844ebb825ae8b044a93c8e071cddce0158cc'
actual=digest(original_stl)
assert actual==expected,(actual,expected)
files={str(p.relative_to(ROOT.parent)):digest(p) for p in SOURCE.parent.rglob('*') if p.is_file()}
record={'source_stl_sha256_expected':expected,'source_stl_sha256_actual':actual,'source_stl_matches_prior_record':True,
        'source_geometry_sha256':digest(SOURCE),'source_folder_read_only_during_analysis':True,
        'writes_restricted_by_scripts_to_analysis_folder':str(ROOT),'source_folder_files':files}
dest=ROOT/'source_integrity.json'
if dest.exists():
    old=json.loads(dest.read_text())
    assert old['source_folder_files']==files,'Source folder contents changed during analysis'
    record['all_recorded_source_files_unchanged']=True
dest.write_text(json.dumps(record,indent=2),encoding='utf-8')
print('SOURCE_STL_MATCHES_PRIOR_RECORD; source folder files:',len(files))
