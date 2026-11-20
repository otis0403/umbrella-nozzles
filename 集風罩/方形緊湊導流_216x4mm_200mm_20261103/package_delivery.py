from pathlib import Path
import json,zipfile,hashlib
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
model=json.loads((HERE/'模型幾何檢查.json').read_text(encoding='utf-8'))
verified=json.loads((HERE/'STL獨立重讀檢查.json').read_text(encoding='utf-8'))
preview=json.loads((HERE/'預覽來源檢查.json').read_text(encoding='utf-8'))
assert verified['all_existing_files_unchanged']
assert preview['source_sha256']==model['blend_sha256']==sha(HERE/model['blend_file'])
for part in model['parts']:
    assert sha(HERE/part['file'])==part['sha256']==next(p for p in verified['parts'] if p['file']==part['file'])['sha256']
files=[p['file'] for p in model['parts']]+[model['blend_file'],'01_實際模型_方形緊湊組裝.png','02_實際模型_尖鼻與十字導流透視.png',
    '計算與列印說明.md','尺寸方案計算.json','長度方案比較.csv','模型幾何檢查.json','STL獨立重讀檢查.json','預覽來源檢查.json']
target=HERE/'方形緊湊導流_216x4mm_200mm_雙半殼列印包.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in files:z.write(HERE/name,arcname=name)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None and len(z.namelist())==len(files)
    for name in files:assert z.read(name)==(HERE/name).read_bytes()
print(json.dumps({'zip':str(target),'bytes':target.stat().st_size,'files':len(files),'verified':True},ensure_ascii=True))
