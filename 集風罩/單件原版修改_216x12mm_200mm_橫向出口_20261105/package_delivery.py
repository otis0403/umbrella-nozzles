from pathlib import Path
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((HERE/'尺寸與方向檢查.json').read_text(encoding='utf-8'))
verified=json.loads((HERE/'STL獨立重讀檢查.json').read_text(encoding='utf-8'))
preview=json.loads((HERE/'預覽來源檢查.json').read_text(encoding='utf-8'))
draw=json.loads((HERE/'圖面來源檢查.json').read_text(encoding='utf-8'))
assert sha(HERE/r['stl_file'])==r['stl_sha256']==verified['sha256']==draw['new_stl_sha256']
assert sha(HERE/r['blend_file'])==r['blend_sha256']==preview['new_sha256']==draw['new_manufacturing_blend_sha256']
assert verified['all_existing_files_unchanged'] and preview['all_sources_unchanged']
for name,h in draw['images'].items():assert sha(HERE/name)==h
files=[r['stl_file'],r['blend_file'],'01_實際模型_12mm橫向出口.png','02_實際模型_橫向核心與支撐.png',
    '03_固定法蘭_新舊出口方向對照.png','04_橫向出口_尺寸與孔位圖.png','橫向出口_尺寸與孔位圖.pdf',
    '修改與列印說明.md','尺寸與方向檢查.json','STL獨立重讀檢查.json','預覽來源檢查.json','圖面來源檢查.json','實測紀錄.csv']
target=HERE/'直通吹嘴_216x12mm_200mm_橫向出口_單件列印包.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in files:z.write(HERE/name,arcname=name)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None and len(z.namelist())==len(files)
    for name in files:assert z.read(name)==(HERE/name).read_bytes()
print(json.dumps({'zip':str(target),'bytes':target.stat().st_size,'files':len(files),'verified':True},ensure_ascii=True))
