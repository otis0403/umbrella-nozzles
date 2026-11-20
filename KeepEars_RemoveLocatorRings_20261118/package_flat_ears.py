import hashlib,json,shutil,zipfile
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'flat_ear_checks.json').read_text(encoding='utf-8-sig'))
native=json.loads((ROOT/'native_checks.json').read_text(encoding='utf-8-sig'))
assert native['native_reopened'] and native['assembled_poses_verified']
assert native['verified_STL_sha256']=={r['id']:r['STL_sha256'] for r in data['parts']}
assert len(native['flat_faces'])==4 and sum(r['ring_count'] for r in native['flat_faces'])==8
raw=(ROOT/'build_native.log').read_bytes()
log=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
assert 'ORIGINAL_EARS_RETAINED_ALL_8_RING_FACES_FLAT_NATIVE_PASSED' in log
plt.rcParams['font.family']='Microsoft JhengHei'
fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
for ax,file,title in zip(axes,['ear_before','ear_after'],['原版：耳座表面有 1.5 mm 定位凸環','新版：耳座保留，孔邊表面修平']):
    ax.imshow(plt.imread(ROOT/f'images/{file}.png'));ax.axis('off');ax.set_title(title,fontweight='bold',fontsize=14)
fig.suptitle('實際 STL 修改前後對照｜只去凸環，保留外凸耳座',fontsize=19,fontweight='bold')
fig.supxlabel('相同視角與比例｜原 M4 通孔、耳座厚度與外形保留｜不是額外的概念生成圖',fontsize=11)
fig.savefig(ROOT/'images/actual_ear_before_after.png',dpi=160);plt.close(fig)

labels={'inner_body':'01_內側225_本體_耳座去凸環','inner_tip_g12':'02_內側225x12_前嘴_沿用',
        'center_body':'03_中間180_本體_耳座去凸環','center_tip_g14':'04_中間180x14_前嘴_沿用',
        'outer_inlet':'05_外側315_入口段_去凸環','outer_guided_body':'06_外側315_導流段_耳座去凸環',
        'outer_tip_g8':'07_外側315x8_前嘴_沿用'}
fig,axes=plt.subplots(2,4,figsize=(16,10),layout='constrained')
for ax,row in zip(axes.flat,data['parts']):
    color='#277a8d' if row['changed'] else '#e98c46'
    tri=trimesh.load_mesh(row['STL'],process=True);xy=tri.vertices[:,:2]+150;hull=ConvexHull(xy)
    ax.add_patch(Rectangle((0,0),300,300,facecolor='#f3f6f8',edgecolor='#657581',lw=1.5))
    b=np.array(row['placed_3MF_bounds_mm']);lo=b[0,:2]-8;sz=np.array(row['print_size_mm'][:2])+16
    ax.add_patch(Rectangle(lo,*sz,fill=False,ls='--',edgecolor=color))
    ax.add_patch(Polygon(xy[hull.vertices],facecolor=color,alpha=.75))
    ax.set(xlim=(-7,307),ylim=(-7,307),aspect='equal',xticks=[0,150,300],yticks=[0,150,300])
    w,d,z=row['print_size_mm'];ax.set_title(labels[row['id']].replace('_','\n',1),fontsize=10,fontweight='bold')
    ax.set_xlabel(f'{w:.1f}×{d:.1f}×{z:.1f} mm',fontsize=11)
axes.flat[-1].axis('off')
axes.flat[-1].text(.05,.86,'藍色：4 件去凸環新版\n橘色：3 件沿用前嘴\n\n每檔一件，分開列印\n已預轉 45°，單位 mm\n\n虛線：另留每側 8 mm\n的裙邊空間\n\n此圖為投影包絡，\n尚未實際切片。',va='top',fontsize=13,linespacing=1.5)
fig.suptitle('K2 Pro 300×300×300 mm｜保留原外凸耳座的列印配置',fontsize=19,fontweight='bold')
fig.savefig(ROOT/'images/K2Pro_7parts_layout.png',dpi=150);plt.close(fig)

DEST=ROOT.parent/'集風罩'/'保留耳座_去凸環_三吹嘴_K2Pro_20261118'
for d in ['STL','3MF','模型','圖片','檢查紀錄','設計程式']:(DEST/d).mkdir(parents=True,exist_ok=True)
table=[];mapping=[]
for row in data['parts']:
    label=labels[row['id']]
    for kind,ext in [('STL','.stl'),('3MF','.3mf')]:
        target=DEST/kind/(label+('_mm' if kind=='STL' else '_K2Pro300')+ext)
        shutil.copy2(row[kind],target);assert hashlib.sha256(target.read_bytes()).hexdigest()==row[kind+'_sha256']
    table.append('| '+label+' | '+'×'.join(f'{v:.1f}' for v in row['print_size_mm'])+' | '+('需重印' if row['changed'] else '可沿用舊凸耳版')+' |')
    mapping.append({'id':row['id'],'file_prefix':label,'changed':row['changed']})
shutil.copy2(ROOT/'cad/original_ears_flat_faces_assembled_mm.blend',DEST/'模型/保留耳座_去凸環_三吹嘴組裝_mm.blend')
for p in (ROOT/'images').glob('*.png'):shutil.copy2(p,DEST/'圖片'/p.name)
for name in ['flat_ear_checks.json','native_checks.json']:shutil.copy2(ROOT/name,DEST/'檢查紀錄'/name)
for name in ['build_flat_ears.py','build_native.py','package_flat_ears.py']:shutil.copy2(ROOT/name,DEST/'設計程式'/name)
(DEST/'檢查紀錄/交付檔名對照.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
manual='''# 保留原本外凸耳座，只去掉耳座表面的定位凸環

版本：2026-11-18。本版依確認的局部示意修改：耳座繼續向外伸出，原本孔邊額外高起的1.5 mm定位凸環移除，讓塑膠耳座表面與孔邊為同一平面。三個前嘴接頭，以及最大吹嘴後端法蘭接頭，合計8個定位凸環已移除。

沿用原本外側M4螺絲固定方式、單顆耳座外形、4 mm耳座厚度、孔位及孔徑、2.4 mm名義殼厚與約2 mm唇厚。平面指塑膠耳座表面；標準M4螺絲頭、螺帽和墊片仍是外側零件。沒有加厚成先前內藏套接版，也沒有將單顆耳座連成長條。

## 需要重印的零件

| 檔名 | 已擺方向的 X×Y×Z（mm） | 使用方式 |
|---|---|---|
'''+ '\n'.join(table)+'''

**只有01、03、05、06四件是去凸環的修改件。** 已有原M4凸耳版的02、04、07三個前嘴，可以沿用，不必重印。此包仍附三個前嘴，供尚未列印者湊成完整一組。最大吹嘴保留K2 Pro分件配置，入口段55 mm、導流段290 mm、前嘴43 mm；組裝總長仍388 mm。零件少了1.5 mm凸環高度，不代表流道或組裝長度縮短。

請使用此資料夾的「保留耳座／去凸環」系列，或搭配原先M4凸耳版相容前嘴。先前另存的M3內藏套接版本接口不同，無法與本版混裝；舊版原檔都保留。

## 列印配置

STL已預轉45°，單位mm，底面Z=0。3MF為每檔一件的通用模型與位置，置於300×300 mm平台中央；不含材料參數、機器設定、支撐、裙邊、底筏或G-code。請在Creality Print選自己的K2 Pro、材料及噴嘴設定，保留比例與方向後檢查切片。

以[K2 Pro官方300×300×300 mm列印空間](https://store.creality.com/products/creality-k2-pro-combo-3d-printer)核對，七件皆容納且另預留每側8 mm裙邊空間；最高導流段290 mm，距Z上限10 mm。外側導流段以原Z55接合面朝下，兩片導流片的起始面也在列印Z=0。加入支撐、底筏或其他結構後需重新核對實際路徑；本交付尚未實際切片，沒有宣稱免支撐。

`圖片/K2Pro_7parts_layout.png`是投影凸包與平台包絡，並非切片截圖。藍色為四件修改件，橘色為沿用前嘴。

## 尺寸與接口

- 內側225×12 mm，整組長288 mm，前嘴接合平面原Z245。
- 中間180×14 mm，整組長248 mm，前嘴接合平面原Z205。
- 外側315×8 mm，整組長388 mm，前嘴接合平面原Z345；後端法蘭分件平面原Z55。
- 母承口內徑55.4 mm、插入25 mm、主入口流道名義51 mm；沿用原接口。
- 外側兩片導流片保留，原Z55到332 mm，出口前仍有56 mm無分隔通道。

對面的原定位凹座保留，螺絲通孔、浮動長孔和密封槽也保留，以維持舊凸耳版零件相容性。原定位凸環已取消，組裝時改靠螺絲孔及人工對齊。

## 固定與組裝

| 接頭 | M4×16螺絲 | M4螺帽 | 平墊片（原設計OD9） |
|---|---:|---:|---:|
| 內側前嘴 | 4 | 4 | 8 |
| 中間前嘴 | 4 | 4 | 8 |
| 外側前嘴 | 6 | 6 | 12 |
| 外側本體後端法蘭 | 4 | 4 | 8 |
| 一組三種吹嘴合計 | 18 | 18 | 36 |

螺絲規格維持原M4×16，不是先前內藏版的M3。先清理接面、孔及毛邊，乾式對合；確認四周接面貼合、流道內壁對齊後，螺絲先輕鎖，再交錯均勻鎖緊。接合平面直接貼合，沒有1.5 mm的額外墊高間隙。螺絲穿過平耳座、配螺帽固定，不把塑膠通孔當螺紋使用。

密封槽保持原寬1.2 mm、深0.5 mm；可用薄的可拆密封材料試配，材料厚度與壓縮量依實物確認，不要擠入流道或用永久膠黏死可換前嘴。外側後法蘭的螺絲可由入口側穿入、另一側裝螺帽，方便工具操作。

## 檢查紀錄

四件修改前後以實體差集核對：移除材料全部位於原定位凸環範圍內，耳座平面以下移除量為0、額外新增材料為0。各件移除兩個凸環，合計八個；原本耳座、法蘭、孔位和流道保留。

7個STL獨立重讀，封閉網格、單一連通實體、正體積、面方向一致、無退化面均通過；7個3MF另行解析單位、網格及平台變換，核對300 mm空間和8 mm餘量。Blender重開原生模型後核對7件裝配姿態、原承口及出口尺寸。

每個原凸環的位置，沿孔外半徑3 mm處取16點，合計128點量測。修改前高於耳座面約1.5 mm，修改後與耳座平面齊平；同時核對耳座厚度4 mm及M4通孔約4.4 mm。三個出口各量61點，檢查225×12／180×14／315×8 mm；原檔SHA-256前後一致。`圖片/actual_ear_before_after.png`是實際來源STL及修改STL以相同視角出圖，不是概念生成圖。

此修改在流道外，本次沒有重新跑ANSYS。幾何檢查不能代替列印、套合、強度、漏氣或風量實測；先前流場計算的假設與收斂限制仍適用。組裝後仍須檢查密封和出風狀況。

## 交付內容

- `STL/`、`3MF/`：完整一組7件；已有前嘴可只印4件修改件。
- `模型/`：三種吹嘴已組裝的Blender模型，mm。
- `圖片/`：實際耳座修改前後、三吹嘴總覽、外側分解及K2 Pro平台包絡。
- `檢查紀錄/`：來源與交付檔雜湊、只移除凸環的差集結果、接口平面及尺寸檢查。
- `設計程式/`：本次程式備查，重建需原工作區幾何函式與來源模型。
'''
(DEST/'先看這裡_列印與組裝說明.md').write_text(manual,encoding='utf-8-sig')
assert len(list((DEST/'STL').glob('*.stl')))==7 and len(list((DEST/'3MF').glob('*.3mf')))==7
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in data['source_hashes_unchanged'].items())
manifest={str(p.relative_to(DEST)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='SHA256.json'}
(DEST/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
archive=DEST.parent/'保留耳座_去凸環_7件列印包_20261118.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(DEST.rglob('*')):
        if p.is_file():z.write(p,str(Path(DEST.name)/p.relative_to(DEST)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name in z.namelist():
        relative=Path(name).relative_to(DEST.name).as_posix()
        if relative in manifest:assert hashlib.sha256(z.read(name)).hexdigest()==manifest[relative]
status={'complete':True,'delivery':str(DEST),'ZIP':str(archive),'print_STL_count':7,'print_3MF_count':7,
        'modified_parts':4,'raised_locator_rings_removed':8,'original_external_ears_retained':True,
        'original_M4_fixings_and_tip_compatibility_retained':True,'original_source_hashes_unchanged':True,
        'STL_3MF_native_and_archive_checks_passed':True,'physical_print_fit_strength_sealing_verified':False}
(ROOT/'DELIVERY_COMPLETE.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'WORK_STATUS.md').write_text('# Complete 2026-11-18\n\nReturned to original external M4 ear/flange design. Removed only eight raised locating rings on four male mating faces.\n7 print STLs / 3MF, source CSG masks and 128 native flat-face ray samples passed.\nOriginal tips compatible, original source hashes preserved. No CFD or physical print/fit/sealing verification.\n\n'+str(archive)+'\n',encoding='utf-8')
print('ORIGINAL_EARS_ONLY_RING_REMOVAL_DELIVERY_COMPLETE',json.dumps(status,ensure_ascii=True),flush=True)
