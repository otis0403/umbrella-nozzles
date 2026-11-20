"""Package the checked STL and its documentation without touching old files."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json

HERE=Path(__file__).resolve().parent
FILES=[
    '直通吹嘴_216x4mm_中央鴨嘴導流_單件_mm.stl',
    '直通吹嘴_216x4mm_中央鴨嘴導流_單件.blend',
    '01_實際模型_完整外觀.png',
    '02_實際模型_核心與十字導流剖視.png',
    '列印與使用說明.md',
    '尺寸與列印幾何檢查.json',
    'STL獨立重讀檢查.json',
    '預覽來源檢查.json',
]
check=json.loads((HERE/'STL獨立重讀檢查.json').read_text(encoding='utf-8'))
preview=json.loads((HERE/'預覽來源檢查.json').read_text(encoding='utf-8'))
assert preview['source_unchanged'] and 'transparent' in preview['preview_method']
for name in FILES:assert (HERE/name).is_file(),name
archive=HERE/'STL_中央鴨嘴導流版_列印包.zip'
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=6) as z:
    for name in FILES:z.write(HERE/name,arcname=name)
with ZipFile(archive) as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read(FILES[0])).hexdigest()==check['sha256']
print(json.dumps({'archive':str(archive),'files':FILES,'bytes':archive.stat().st_size,
    'STL_sha256':check['sha256']},ensure_ascii=False),flush=True)
