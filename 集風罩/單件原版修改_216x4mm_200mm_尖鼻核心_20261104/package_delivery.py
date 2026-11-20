from pathlib import Path
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=json.loads((HERE/'尺寸與修改檢查.json').read_text(encoding='utf-8'))
checked=json.loads((HERE/'STL獨立重讀檢查.json').read_text(encoding='utf-8'))
preview=json.loads((HERE/'預覽來源檢查.json').read_text(encoding='utf-8'))
assert sha(HERE/report['stl_file'])==report['stl_sha256']==checked['sha256']
assert sha(HERE/report['blend_file'])==report['blend_sha256']==preview['source_sha256']
assert checked['uploaded_STL_unchanged']
files=[report['stl_file'],report['blend_file'],'01_實際模型_200mm單件外觀.png','02_實際模型_尖鼻核心與底面支撐.png',
    '修改與列印說明.md','尺寸與修改檢查.json','STL獨立重讀檢查.json','預覽來源檢查.json']
target=HERE/'直通吹嘴_216x4mm_200mm_尖鼻核心_單件列印包.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in files:z.write(HERE/name,arcname=name)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None and len(z.namelist())==len(files)
    for name in files:assert z.read(name)==(HERE/name).read_bytes()
print(json.dumps({'zip':str(target),'bytes':target.stat().st_size,'files':len(files),'verified':True},ensure_ascii=True))
