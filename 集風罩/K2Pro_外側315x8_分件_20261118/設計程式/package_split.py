import hashlib,json,shutil,zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'print_checks.json').read_text(encoding='utf-8-sig'))
native=json.loads((ROOT/'native_geometry_checks.json').read_text(encoding='utf-8-sig'))
assert native['native_reopened'] and native['assembled_pose_verified']
log_bytes=(ROOT/'build_native.log').read_bytes()
log_text=log_bytes.decode('utf-16' if log_bytes.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
assert 'K2PRO_NATIVE_REOPEN_AND_DIMENSIONS_PASSED' in log_text

plt.rcParams['font.family']='Microsoft JhengHei'
fig,axes=plt.subplots(1,2,figsize=(15,7.5),layout='constrained')
for ax,name,title in zip(axes,['assembled','exploded'],['組裝狀態｜出口 315×8 mm、整組長 388 mm','分解示意｜入口段＋導流段＋可換前嘴']):
    ax.imshow(plt.imread(ROOT/f'images/{name}.png'));ax.axis('off');ax.set_title(title,fontweight='bold',fontsize=14)
fig.suptitle('外側最大吹嘴：K2 Pro 分件版',fontsize=21,fontweight='bold')
fig.legend(handles=[Patch(color=c,label=t) for c,t in [('#124559','入口段'),('#33949f','導流段（兩片導流片完整保留）'),('#ef842c','315×8 mm 可換前嘴')]],loc='lower center',ncol=3,frameon=False,fontsize=12,bbox_to_anchor=(.5,.055))
fig.supxlabel('新增後端接縫：4×M4×16 螺絲鎖合＋密封｜前嘴原接口：6×M4｜螺絲未畫入，分解距離僅供示意',fontsize=12)
fig.savefig(ROOT/'images/assembly_guide.png',dpi=160)
plt.close(fig)

DEST=ROOT.parent/'集風罩'/'K2Pro_外側315x8_分件_20261118'
for d in ['STL','3MF','模型','圖片','檢查紀錄','設計程式']:(DEST/d).mkdir(parents=True,exist_ok=True)
labels=['01_入口段','02_導流段','03_可換前嘴315x8']
mapping=[]
for label,row in zip(labels,data['parts']):
    for key,ext in [('STL','.stl'),('3MF','.3mf')]:
        src=Path(row[key]);target=DEST/key/(label+('_mm' if key=='STL' else '_K2Pro300')+ext)
        shutil.copy2(src,target)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==row[key+'_sha256']
    mapping.append({'part_id':row['id'],'delivered_name':label,'print_size_mm':row['print_size_mm']})
shutil.copy2(ROOT/'cad/outer315_K2Pro_assembled_mm.blend',DEST/'模型/外側315x8_組裝_mm.blend')
for p in (ROOT/'images').glob('*.png'):shutil.copy2(p,DEST/'圖片'/p.name)
for p in ['print_checks.json','native_geometry_checks.json']:shutil.copy2(ROOT/p,DEST/'檢查紀錄'/p)
for p in ['build_split.py','build_native.py','plate_diagram.py','package_split.py']:shutil.copy2(ROOT/p,DEST/'設計程式'/p)
(DEST/'檢查紀錄/交付檔名對照.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')

readme='''# K2 Pro 外側 315×8 mm 吹嘴分件版

本版只處理最大的外側吹嘴。內側225×12 mm、中間180×14 mm與原始交付檔均未修改。依目前外側315×8 mm可換前嘴版製作，本體分為入口段、導流段，前嘴仍是一體可拆換。整組長388 mm，出口淨寬315 mm、間隙8 mm，主要流道內徑51 mm；接管母承口內徑55.4 mm、插入深度25 mm，保持原接口。

## 先選這三個檔案列印

每件獨立列印一次。STL已預轉45°並放平底面；3MF另含平台中央的位置。

| 件號 | 用途 | 列印包絡 X×Y×Z（mm） | 加入每側8 mm裙邊空間後的X×Y（mm） |
|---|---|---|---|
| 01 入口段 | 圓承口、後接縫下半、整合定位凸環 | 101.1×101.1×56.5 | 117.1×117.1 |
| 02 導流段 | 漸擴流道與完整的兩片導流片 | 240.6×240.6×291.5 | 256.6×256.6 |
| 03 可換前嘴315x8 | 收縮段及315×8 mm長縫 | 240.6×240.6×43.0 | 256.6×256.6 |

Creality官方K2 Pro列印範圍300×300×300 mm：[官方產品頁](https://store.creality.com/products/creality-k2-pro-combo-3d-printer)。本版以此空間核對；不是K2 Plus的350 mm空間。

3MF是通用模型與位置檔，沒有材料參數、K2 Pro機器設定、支撐、裙邊或G-code。請在Creality Print選擇你實際的K2 Pro與材料設定，逐一匯入；保留原旋轉與比例，確認包絡同上表。使用STL時單位選mm、平台置中即可。列印用的45°平面旋轉不會改變裝機方向。

導流段以新增接合面朝下，兩片導流片的迎風起點同時落在平台Z=0，不需要跨越原入口段的55 mm空腔才開始生長。其高度291.5 mm距上限僅餘8.5 mm，請勿任意加高或縮放。幾何核對有保留每側8 mm的裙邊空間；若切片加入額外支撐、底筏、擦料塔或其他結構，須重新檢查實際路徑。重點檢查法蘭、沉孔、耳座的懸空與橋接，以及薄壁和導流片的逐層連續性；本交付未實際切片，沒有宣稱免支撐。

## 組裝

1. 先將01入口段與02導流段乾式對合。新增接面在原座標Z=55 mm，兩邊各4 mm厚的外法蘭，90×60 mm、角R6。接口的兩個中空定位凸環已和入口段連成一件，不另印定位銷。
2. 新增接縫使用4顆M4×16螺絲、4顆M4螺帽、8片平墊片。建議螺絲由入口段側穿入，導流段側裝螺帽；交叉逐步鎖緊。不要將塑膠直接當攻牙螺紋。
3. 入口段接面有1.2 mm寬、0.5 mm深的封閉密封槽，位於流道外。使用薄的可拆密封材料，確保定位凸環進入凹座、平面止口貼合，密封材料不突出內流道；實物厚度與壓縮量待試裝確認。不要靠鎖緊力量壓平翹曲件。
4. 前方03前嘴沿用原可換式接口，保留原6組M4×16螺絲、螺帽與每組2片墊片。外側整組合計10組M4固定件；若沿用同版已列印的315×8 mm可換前嘴，03不用重印。不要將前嘴永久黏死。
5. 清除接面與孔內支撐、毛邊後再試裝，確認內壁平順、兩片導流片完整、315×8 mm出口通暢。裝回管路後檢查接縫漏氣及出風。圖中的螺絲省略未畫；分解圖的拉開距離不是墊片或實際間隙。

新增接頭定位凸環OD7.4 mm、高1.5 mm；上段凹座7.9 mm、深1.8 mm，一組固定、對角一組沿Y浮動1 mm。通孔4.4 mm，非固定位置的上段孔沿Y增加1 mm。這些是名義尺寸，並不表示已驗證你材料的收縮或孔位公差。

## 檢查結果與範圍

三個STL皆獨立重讀：封閉網格、面向一致、單一連通實體、正體積、無退化三角形通過。三個3MF也獨立解析單位、網格及平台變換，核對300 mm空間並預留每側8 mm；逐檔雜湊與STL一致性已記錄。Blender模型重新開檔核對三件組裝座標；61點出口間隙約7.9992 mm，淨寬約314.9997 mm，承口約55.4000 mm，原前嘴接口約315×22 mm。導流片底面量得列印座標Z=0。

原外側本體與前嘴的SHA-256前後一致，原檔沒有覆寫。前嘴只作列印方向的剛體轉換及STL精度整理，沒有改變名義流道。新增接縫在原流道外，接面周邊的流道探查體積未見有意新增阻塞，組裝實體穿插小於0.01 mm³；約0.0001 mm³差異屬STL座標量化尺度。兩片導流片完全留在上段，沒有沿長縫分半，出口前仍有56 mm無分隔通道。

本次是分件與幾何檢查，沒有重新跑ANSYS，也沒有量測新接縫的漏氣；原先流場計算的假設與收斂限制仍適用。尚未驗證實際切片、列印、試裝、強度、密封或吹乾效果。模型通過列印空間檢查，不代表已完成實印驗證。

## 檔案

- `STL/`：3件列印用STL，mm。
- `3MF/`：同3件，每檔一件，平台中央，保留45°旋轉。
- `模型/`：三件已組裝的Blender模型，mm。
- `圖片/assembly_guide.png`：組裝與分解對照；`K2Pro_plate_fit.png`：平台投影包絡，並非切片截圖。
- `檢查紀錄/`：STL、3MF、原檔雜湊、原座標組裝轉換、Blender重讀及尺寸結果。
- `設計程式/`：此次分件及出圖程式備查，需原工作區的來源模型與幾何函式才能重建，不是獨立安裝程式。

版本：2026-11-18。原模型來源：case/InnerMiddle_12_14_8_ANSYS_20261117/modular/STL。
'''
(DEST/'先看這裡_列印與組裝說明.md').write_text(readme,encoding='utf-8-sig')
assert len(list((DEST/'STL').glob('*.stl')))==3
assert len(list((DEST/'3MF').glob('*.3mf')))==3
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in data['source_hashes_unchanged'].items())
manifest={str(p.relative_to(DEST)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='SHA256.json'}
(DEST/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
archive=DEST.parent/'K2Pro_外側315x8_3件列印包_20261118.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(DEST.rglob('*')):
        if p.is_file():z.write(p,arcname=str(Path(DEST.name)/p.relative_to(DEST)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name in z.namelist():
        rel=Path(name).relative_to(DEST.name).as_posix()
        if rel in manifest:assert hashlib.sha256(z.read(name)).hexdigest()==manifest[rel]
status={'complete':True,'delivery_directory':str(DEST),'ZIP':str(archive),'ZIP_CRC_and_hashes_passed':True,
        'print_STL_count':3,'print_3MF_count':3,'native_reopen_passed':True,'source_hashes_unchanged':True,
        'actual_slicing_printing_fit_and_sealing_verified':False}
(ROOT/'DELIVERY_COMPLETE.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'WORK_STATUS.md').write_text('# Completed 2026-11-18\n\nLargest outer315x8 nozzle split into inlet lower, guided upper and unchanged onepiece replaceable tip.\nAll 3 print STLs / 3MF fit K2 Pro300mm with 8mm brim allowance, native Blender readback and dimensions passed.\nSource geometry hashes preserved; other heads untouched. No new CFD, actual slicing, printing or fit performed.\n\nDelivery: '+str(DEST)+'\nZIP: '+str(archive)+'\n',encoding='utf-8')
print('K2PRO_DELIVERY_COMPLETE',json.dumps(status,ensure_ascii=True),flush=True)
