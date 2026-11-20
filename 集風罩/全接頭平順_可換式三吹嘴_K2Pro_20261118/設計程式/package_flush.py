import hashlib,json,shutil,zipfile
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'flush_checks.json').read_text(encoding='utf-8-sig'))
native=json.loads((ROOT/'native_checks.json').read_text(encoding='utf-8-sig'))
nuts=json.loads((ROOT/'nut_checks.json').read_text(encoding='utf-8-sig'))
assert native['native_reopened'] and native['all_assembled_poses_verified'] and nuts['nut_count']==18
assert native['verified_STL_sha256']=={r['id']:r['STL_sha256'] for r in data['parts']}
assert all(h['additional_seating_checked_mm']==.16 and h['additional_seating_collision_mm3']<.01
           for g in data['groups'] for j in g['joints'] for h in j['hardware'])
assert all(h['flow_intrusion_mm3']<.001 for h in nuts['results'])
raw=(ROOT/'build_native.log').read_bytes()
log=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
assert 'FLUSH_NATIVE_READBACK_PASSED' in log
labels={'inner_body':'01_內側225_本體','inner_tip_g12':'02_內側225x12_前嘴',
        'center_body':'03_中間180_本體','center_tip_g14':'04_中間180x14_前嘴',
        'outer_inlet':'05_外側315_入口段','outer_guided_body':'06_外側315_導流段','outer_tip_g8':'07_外側315x8_前嘴'}
plt.rcParams['font.family']='Microsoft JhengHei'

fig,axes=plt.subplots(1,2,figsize=(15,7.5),layout='constrained')
for ax,filename,title in zip(axes,['outer_assembled','outer_exploded'],['組裝後：外表連續，螺絲頭沉入殼內','分解示意：12 mm 內藏套接、藏入螺帽']):
    ax.imshow(plt.imread(ROOT/f'images/{filename}.png'));ax.axis('off');ax.set_title(title,fontsize=14,fontweight='bold')
fig.suptitle('全部接頭取消外凸耳座與法蘭｜外側 315×8 mm 示意',fontsize=19,fontweight='bold')
fig.supxlabel('入口段＋導流段＋可換前嘴｜前嘴 6 組、後接頭 4 組 M3×6 沉頭螺絲｜分解圖拉開距離僅供示意',fontsize=12)
fig.savefig(ROOT/'images/flush_assembly_guide.png',dpi=160);plt.close(fig)

fig,axes=plt.subplots(2,4,figsize=(16,10),layout='constrained')
for ax,row in zip(axes.flat,data['parts']):
    color='#e88942' if '_tip_' in row['id'] else '#216b82'
    tri=trimesh.load_mesh(row['STL'],process=True);xy=tri.vertices[:,:2]+150;hull=ConvexHull(xy)
    ax.add_patch(Rectangle((0,0),300,300,facecolor='#f3f6f8',edgecolor='#657581',lw=1.5))
    b=np.array(row['placed_3MF_bounds_mm']);lo=b[0,:2]-8;sz=np.array(row['print_size_mm'][:2])+16
    ax.add_patch(Rectangle(lo,*sz,fill=False,ls='--',edgecolor=color))
    ax.add_patch(Polygon(xy[hull.vertices],facecolor=color,alpha=.75))
    ax.set(xlim=(-7,307),ylim=(-7,307),aspect='equal',xticks=[0,150,300],yticks=[0,150,300])
    w,d,z=row['print_size_mm']
    ax.set_title(labels[row['id']],fontweight='bold',fontsize=11)
    ax.set_xlabel(f'{w:.1f}×{d:.1f}×{z:.1f} mm',fontsize=11)
axes.flat[-1].axis('off')
axes.flat[-1].text(.05,.85,'一組三種吹嘴，共 7 件\n\n每檔一件，分開列印\n已預轉 45°，單位 mm\n\n虛線：每側另留 8 mm\n的裙邊空間\n\n這是投影包絡圖，\n尚未實際切片。',va='top',fontsize=14,linespacing=1.5)
fig.suptitle('K2 Pro 300×300×300 mm｜七件列印方向與空間',fontsize=20,fontweight='bold')
fig.savefig(ROOT/'images/print_layout_7parts.png',dpi=150);plt.close(fig)

DEST=ROOT.parent/'集風罩'/'全接頭平順_可換式三吹嘴_K2Pro_20261118'
for d in ['STL','3MF','模型','圖片','檢查紀錄','設計程式']:(DEST/d).mkdir(parents=True,exist_ok=True)
rows=[]
for row in data['parts']:
    label=labels[row['id']]
    for kind,ext in [('STL','.stl'),('3MF','.3mf')]:
        target=DEST/kind/(label+('_mm' if kind=='STL' else '_K2Pro300')+ext)
        shutil.copy2(row[kind],target)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==row[kind+'_sha256']
    rows.append('| '+label+' | '+'×'.join(f'{v:.1f}' for v in row['print_size_mm'])+' |')
shutil.copy2(ROOT/'cad/flush_three_nozzles_assembled_mm.blend',DEST/'模型/三吹嘴_全接頭平順_組裝_mm.blend')
for p in (ROOT/'images').glob('*.png'):shutil.copy2(p,DEST/'圖片'/p.name)
for name in ['flush_checks.json','native_checks.json','nut_checks.json']:shutil.copy2(ROOT/name,DEST/'檢查紀錄'/name)
for name in ['build_flush.py','check_nuts.py','build_native.py','package_flush.py']:shutil.copy2(ROOT/name,DEST/'設計程式'/name)
readme='''# 三個吹嘴：全部接頭取消外凸耳座與法蘭

2026-11-18 新版。適用內側225×12、中間180×14、外側315×8 mm三種吹嘴。所有前嘴接頭與外側本體的分件接頭，均採12 mm內藏套接、沉頭M3螺絲、藏入殼內的螺帽。裝好後外表面連續，沒有個別凸耳或外凸法蘭。前嘴仍可拆換。

**新版接口需要本體與前嘴配套重印。與舊凸耳版、舊M4接口、舊16 mm參考前嘴不相容。** 原檔保留，不要把新舊版本混裝。這份交付包含各尺寸各一組，共7個列印零件；若左右各需同一組，則各檔列印兩份。

## 列印檔

| 件號／檔名 | 擺好方向後 X×Y×Z（mm） |
|---|---|
'''+ '\n'.join(rows)+'''

各檔皆已預轉45°並置於平台Z=0，STL單位mm。3MF為通用模型與平台位置，每檔一件，置中於300×300 mm平台；不包含機器、材料、支撐、裙邊、底筏或G-code。請在Creality Print選擇自己的K2 Pro與材料設定後逐件匯入，保持比例與旋轉，檢查尺寸同上表。

以[K2 Pro官方300×300×300 mm列印空間](https://store.creality.com/products/creality-k2-pro-combo-3d-printer)核對，七件模型皆可容納，並另預留每側8 mm的裙邊空間。外側導流段290 mm高，距Z上限餘10 mm。實際加入支撐、底筏或擦料結構後仍需檢查切片路徑。`圖片/print_layout_7parts.png`是模型投影凸包，並非切片預覽。

外側入口段以管口朝下，導流段以後端套接舌朝下；兩片導流片的迎風端也在其列印底面Z=0。三種前嘴以母套開口朝下、出口朝上；其餘本體以管口朝下。檢查橫向螺絲孔、沉孔及藏螺帽槽頂部的橋接和懸空；沒有宣稱免支撐或已實印。

## 外形與流道

內部沿用原流道：內側225×12 mm、全長288 mm；中間180×14 mm、全長248 mm；外側315×8 mm、全長388 mm。母承口內徑55.4 mm、插入25 mm，主要入口流道名義51 mm。外側兩片導流片Z55至332 mm保留，出口前56 mm仍連通。

為讓螺帽與套接結構藏入殼內，本體採連續加厚外殼：短方向名義8 mm、長邊端部4.4 mm；前嘴在原收縮段沿長度逐漸回到2 mm唇厚。外殼會比舊版厚、耗材增加，並非只把凸耳削除。外側最大外形長邊約323.8 mm，列印時靠45°擺放容納；出口淨寬仍315 mm。套接外形和殼面相接，沒有局部突出的固定耳座。

前嘴現在55 mm長，與本體重疊12 mm，所以整組總長不增加。內側前嘴套接範圍Z233–245，中間Z193–205，外側Z333–345。外側後端套接範圍Z55–67，導流段向入口段內插入12 mm；其外表接縫在Z67。所有接頭都有台階止口，裝配時推到底，零件長度不能直接相加。

## 螺絲與螺帽

| 位置 | M3×6沉頭螺絲 | M3六角螺帽 |
|---|---:|---:|
| 內側前嘴 | 4 | 4 |
| 中間前嘴 | 4 | 4 |
| 外側前嘴 | 6 | 6 |
| 外側本體後接頭 | 4 | 4 |
| 一組三個吹嘴合計 | 18 | 18 |

螺絲按DIN7991 M3×6沉頭內六角規格設計，頭徑6 mm、頭高上限1.7 mm；螺帽按DIN934 M3對邊5.5 mm、厚2.4 mm設計。規格參考：[螺絲尺寸](https://www.accu.co.uk/countersunk-socket-head-screws/495076-SSK-M3-6-10-9)、[螺帽尺寸](https://www.accu.co.uk/api/product-datasheet?id=268686)。本版不使用原M4×16、普通高頭螺絲、凸出的螺帽或墊片；螺絲長度影響內壁餘量，請使用設計指定規格。

母套通孔3.6 mm，公舌的盲孔3.4 mm，留內壁不打穿流道；藏螺帽槽厚2.7 mm、寬5.8 mm。名義套合間隙每側0.3 mm，套接12 mm。沉頭表面至少比局部殼面下沉約0.55 mm，後端曲面處約0.65 mm；另檢查向內多座合0.16 mm時仍不碰盲孔底或侵入流道。金屬件在模型中僅供組裝示意，不是待印零件。

## 組裝次序

1. 清除接合面、套接舌、螺絲孔與螺帽槽的支撐、毛邊，先乾式試套，確認12 mm套合能到底。
2. 前嘴的螺帽由本體前端公舌的槽口滑入，對齊側孔；外側後接頭的螺帽由導流段後端公舌的槽口滑入。螺帽先放入，之後才裝母套。
3. 公舌周圍有1.2 mm寬、0.4 mm深的環形密封槽，可用薄的可拆密封材料試配。材料厚度、壓縮量須實物核對，不要讓材料進入流道或螺帽槽，不要用永久膠把可換前嘴黏死。
4. 前嘴套上本體至止口貼合，再由外側鎖入M3×6沉頭螺絲。外側入口段與導流段也以同方式套合、鎖緊。輕鎖、交替均勻貼合，勿靠螺絲強壓翹曲件；目前沒有實測可用扭矩。
5. 確認螺絲頭在殼面內、螺帽未鬆脫、前嘴仍可拆卸，接回管路檢查漏氣、吸入口方向與出口分布。

## 幾何檢查

7個STL全部獨立重讀，均為封閉、面向一致、正體積、單一連通實體，沒有零面積／退化三角形。7個3MF另行解析單位、網格與平台變換，核對300 mm範圍及每側8 mm額外空間。組裝穿插、18個螺絲頭是否超出連續外殼、螺絲與塑膠碰撞、18個螺帽能否放入槽，以及螺絲／螺帽是否侵入流道均通過幾何檢查。

CAD階段與原模型比較，流道內新增及移除的探查體積都是0。外側重新讀取STL並轉回組裝座標後，在導流片表面產生約0.185／0.158 mm³的薄層差異；Blender對照原檔量得導流片表面最大位移約0.000004 mm，屬浮點座標量化尺度。此數字不是流量變化。

Blender已重新開檔核對7件裝配姿態，並沿每個出口量61點：內側約11.994–12.000 mm、中間約14.000 mm、外側約7.999 mm，淨寬225／180／315 mm；母承口約55.400 mm。外側導流片起點為列印Z=0。原始來源STL雜湊前後一致。

本次沒有重新跑ANSYS，幾何保持名義流道不代表已驗證實際漏氣與風量。原流場計算的假設及收斂限制仍適用。尚未完成實際切片、列印、套合、強度、耐久或密封驗證；螺帽槽和沉頭孔也須依材料收縮試裝。

## 內容

- `STL/`：7件列印用模型；`3MF/`：同7件，每檔一件。
- `模型/`：三種吹嘴已裝配的Blender模型，mm；金屬件標註為示意。
- `圖片/`：三種吹嘴總覽、外側組裝／分解圖、七件平台包絡。
- `檢查紀錄/`：零件雜湊、原檔雜湊、裝配變換、流道與金屬件碰撞、Blender重讀結果。
- `設計程式/`：本次產生程式備查，需原工作區幾何函式和來源STL才能重建，不是獨立安裝程式。

原先凸耳版本與K2 Pro分件版保留，未覆寫；請以此資料夾內的一套零件配套使用。
'''
(DEST/'先看這裡_列印與組裝說明.md').write_text(readme,encoding='utf-8-sig')
assert len(list((DEST/'STL').glob('*.stl')))==7 and len(list((DEST/'3MF').glob('*.3mf')))==7
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in data['source_hashes_unchanged'].items())
manifest={str(p.relative_to(DEST)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='SHA256.json'}
(DEST/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
zip_path=DEST.parent/'全接頭平順_三吹嘴_7件列印包_20261118.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as arc:
    for p in sorted(DEST.rglob('*')):
        if p.is_file():arc.write(p,str(Path(DEST.name)/p.relative_to(DEST)))
with zipfile.ZipFile(zip_path) as arc:
    assert arc.testzip() is None
    for name in arc.namelist():
        rel=Path(name).relative_to(DEST.name).as_posix()
        if rel in manifest:assert hashlib.sha256(arc.read(name)).hexdigest()==manifest[rel]
status={'complete':True,'delivery':str(DEST),'ZIP':str(zip_path),'STL_count':7,'3MF_count':7,
        'flush_joint_count':4,'M3x6_screw_and_M3_nut_sets':18,'original_sources_unchanged':True,
        'all_native_and_archive_checks_passed':True,'physical_print_fit_strength_seal_verified':False}
(ROOT/'DELIVERY_COMPLETE.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'WORK_STATUS.md').write_text('# Complete 2026-11-18\n\nAll three nozzle tip joints and outer body split redesigned with telescoping joints and recessed M3x6 screws/captive M3 nuts, no external ears/flanges.\n7 print STLs/3MF, reloaded meshes and native Blender pose/rays/guide checks passed; all 18 screws/nuts checked for fit/flow intrusion.\nOriginal sources untouched. Physical slicing/printing/fit/strength/sealing not performed.\n\n'+str(zip_path)+'\n',encoding='utf-8')
print('FLUSH_7PART_DELIVERY_COMPLETE',json.dumps(status,ensure_ascii=True),flush=True)
