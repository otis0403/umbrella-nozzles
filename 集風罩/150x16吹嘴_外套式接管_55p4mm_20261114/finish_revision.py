"""Engineering drawing and a clearly labelled, untested female-socket revision."""
import csv,json,hashlib,zipfile,shutil
from pathlib import Path,PurePosixPath
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle,Rectangle
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

geo=read(ROOT/'cad/geometry_checks.json');checks=read(ROOT/'cad/airpath_checks.json')
assert read(ROOT/'cad/native_reopen_checks.json')['native_blend_reopened']
assert abs(checks['measured_socket_ID_mm']-55.4)<.03 and max(abs(g-16) for g in checks['gap_range_mm'])<.03
original=read(ROOT/'original_release_hashes.json');assert all(digest(p)==v for p,v in original.items())
write(ROOT/'original_release_integrity.json',dict(original_files_unchanged=True,files=original))
part=geo['parts'][0];tm=trimesh.load_mesh(ROOT/'print/STL'/(part['name']+'_mm.stl'),process=True)
assert digest(ROOT/'print/STL'/(part['name']+'_mm.stl'))==part['sha256']
font=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=10)
fig,axes=plt.subplots(1,3,figsize=(15,7),layout='constrained')
def section(ax,origin,normal,coordinates):
    cut=tm.section(plane_origin=origin,plane_normal=normal);assert cut is not None
    for entity in cut.entities:
        v=entity.discrete(cut.vertices);ax.plot(v[:,coordinates[0]],v[:,coordinates[1]],color='#193441',lw=1)
def dim(ax,a,b,label,offset=(0,0)):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='<->',color='#168998',lw=1))
    xy=(np.array(a)+np.array(b))/2+offset
    ax.text(*xy,label,ha='center',va='center',fontsize=10,color='#126b76',rotation=90 if a[0]==b[0] else 0,
        bbox=dict(facecolor='white',edgecolor='none',pad=1))
ax=axes[0];section(ax,[0,0,0],[1,0,0],(1,2))
for sign in [-1,1]:
    ax.add_patch(Rectangle((25.5 if sign>0 else -27.3,-20),1.8,45,facecolor='#d3d8dc',edgecolor='#777',alpha=.8))
dim(ax,(-41,0),(-41,25),'25 mm',(-11,0));dim(ax,(90,0),(90,188),'188 mm',(13,0))
ax.text(0,-37,'軟管插入吹嘴內，端面抵住 25 mm 止擋\n灰色管壁依最大厚度繪製，非實測輪廓',ha='center',fontproperties=font)
ax.set(xlim=(-95,120),ylim=(-50,202),xlabel='Y (mm)',ylabel='Z (mm)');ax.set_title('外套式接管縱剖面',fontproperties=font)
ax=axes[1];section(ax,[0,0,10],[0,0,1],(0,1))
ax.add_patch(Circle((0,0),27.3,fill=False,linestyle='--',edgecolor='#9a7b4f',lw=1.5))
dim(ax,(0,-27.7),(0,27.7),'55.4 mm',(0,0));dim(ax,(-30.1,-40),(30.1,-40),'60.2 mm')
ax.text(0,43,'虛線：估算軟管外徑 Ø54.6 mm\n名義直徑間隙 0.8 mm，須實物試配',ha='center',fontproperties=font)
ax.text(0,-51,'兩道 2 mm 短槽供管夾收緊\n管夾開口需涵蓋約 Ø60.2 mm',ha='center',fontproperties=font)
ax.set(xlim=(-55,55),ylim=(-62,62),xlabel='X (mm)',ylabel='Y (mm)');ax.set_title('接管端 Z=10 mm 橫剖面',fontproperties=font)
ax=axes[2];section(ax,[0,0,187.9],[0,0,1],(1,0))
dim(ax,(-75,-23),(75,-23),'150 mm');dim(ax,(88,-8),(88,8),'16 mm',(12,0))
ax.text(0,39,'出口維持 150×16 mm\n入口流道改為 Ø51 mm，尚未重跑 CFD',ha='center',fontproperties=font)
ax.set(xlim=(-90,120),ylim=(-65,65),xlabel='Y (mm)',ylabel='X (mm)');ax.set_title('出口淨尺寸',fontproperties=font)
for ax in axes:ax.set_aspect('equal');ax.grid(alpha=.12)
fig.suptitle('51 mm 軟管用外套式吹嘴｜55.4 mm 試配版｜單位 mm',fontproperties=font,fontsize=15)
fig.savefig(ROOT/'images/Socket_dimensions_and_fit.png',dpi=180);plt.close(fig)

readme='''# 150×16 mm 吹嘴：外套式接管試配版

本次另存新版本，上一版三路接頭、吹嘴及 ZIP 未改動。先以 **55.4 mm 套口試配**，尚未確認實物尺寸、氣密、固定強度或實際列印結果；本版沒有重跑 ANSYS。

## 規格來源與尺寸推算

找到與使用者圖片完全相同的一列：[固得耐可繞性風管規格表](https://www.goodnice.com.tw/p-h05.html)。51 是內徑 mm，250 是重量 g/m，0.4／1.8 是最小／最大厚度 mm；廠商沒有直接列出外徑。

以最大厚度估算外包絡：51＋2×1.8＝**54.6 mm**。本版套口內徑 **55.4 mm**，預留 **0.8 mm 直徑間隙／0.4 mm 單側間隙**。這是設計估算，不是已量到的軟管外徑。

## 這次的接法

鼓風機 → 原三路接頭（外徑50 mm，插入管內）→ 內徑51 mm軟管 → 新吹嘴（軟管插入55.4 mm套口）→ 150×16 mm出口。

新吹嘴總高 **188 mm**，包絡約 **60.2×154.8×188 mm**；套入深度25 mm，內部有環形端面止擋。套口入口有1.2 mm長導入倒角，內徑在距端面1.2 mm以上回到55.4 mm；底端量到較大的倒角直徑屬設計幾何。

兩道2 mm寬、20 mm高的短槽讓管夾可收緊套口。使用開口能涵蓋約 **60.2 mm外徑** 的管夾，位置放在距吹嘴底端約5–14 mm範圍。短槽不是額外進風口；軟管必須插到底並固定，再確認接合處氣密與拉脫情況。止擋是周邊環形面，不含中央塞塊。

## 先試配，再印三顆

先印 `print/STL/fit_ring_ID55p4_mm.stl`。另附55.0與55.8 mm試配圈，供確認實物與列印公差；圈高10 mm，只用來確認套接尺寸，不代表完整固定或氣密已驗證。

正式吹嘴檔案：`print/STL/nozzle_150x16_female_ID55p4_H188_mm.stl`，整組需要3顆。若55.4 mm試配圈不合，應先依實物調整正式套口，再印完整吹嘴。所有STL採 **mm、100%比例** 匯入。

各零件有單件通用3MF，另有三顆吹嘴的K1C排版 `print/3MF/nozzles_quantity3_K1C.3mf`。幾何空間已核對含5 mm brim，三顆模型間距約11.8 mm；3MF沒有印表機或材料切片參數，尚未實際切片、實印。

## 風道與模擬狀態

本版吹嘴內部從51 mm流道開始，展寬段120 mm，接150×22 mm配風腔，再收至150×16 mm出口。它更改了上一版46 mm入口的幾何，舊版ANSYS壓損、風量及分布數值不能當成本版的驗證。本次只交付可試配的CAD原型，未宣稱風量增加、無回流或吹乾更快。

## 已核對

STL單一連通封閉實體、正體積、法向一致、沒有退化三角面；3MF以mm獨立重讀並核對K1C範圍。Blender由STL獨立量測套口55.4 mm、入口約51 mm、61個16 mm縫寬樣本、150 mm出口淨長，以及兩端188 mm等高；Blender原生檔重新開啟通過。

幾何網格完整不代表接管後已驗證氣密。實物套接、管夾固定、列印剛性與風場仍須確認。

![外觀](images/CAD_female_nozzle.png)
![套口底部](images/CAD_socket_bottom.png)
![接合尺寸與剖面](images/Socket_dimensions_and_fit.png)
'''
(ROOT/'README_外套式接管試配版.md').write_text(readme,encoding='utf-8')
with (ROOT/'parts_and_status.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['項目','尺寸或數量','狀態'])
    w.writerows([['吹嘴','150×16 mm；55.4 mm母套口；印3顆','CAD通過，實物套接待驗證'],['試配圈','55.0／55.4／55.8 mm；先試55.4','僅尺寸試配'],
        ['吹嘴端管夾','需涵蓋約60.2 mm外徑；3個','使用者自備'],['原三路接頭','外徑50 mm插入51 mm軟管','沿用，未改動'],['ANSYS','新版51 mm入口','未重算']])
paths=[ROOT/'README_外套式接管試配版.md',ROOT/'parts_and_status.csv',ROOT/'original_release_hashes.json',ROOT/'original_release_integrity.json']
for folder in ['print','cad','images']:paths += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
paths += [ROOT/n for n in ['build_revision.py','render_and_measure.py','verify_native.py','finish_revision.py']]
paths += [p for p in (ROOT/'dependencies').glob('*.py')] if (ROOT/'dependencies').exists() else []
paths=sorted(set(paths));manifest={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
(ROOT/'MANIFEST.sha256').write_text('\n'.join(f'{v}  {k}' for k,v in manifest.items())+'\n',encoding='utf-8')
pack=ROOT/'FemaleSocket55p4_150x16_Prototype.zip'
with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in paths+[ROOT/'MANIFEST.sha256']:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(pack) as z:
    assert z.testzip() is None
    for name,expected in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected
dest=ROOT.parent/'集風罩'/'150x16吹嘴_外套式接管_55p4mm_20261114'
assert not dest.exists(),'Save another revision instead of overwriting a delivery'
dest.mkdir(parents=True)
with zipfile.ZipFile(pack) as z:
    for name in z.namelist():
        p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
    z.extractall(dest)
shutil.copyfile(pack,dest/pack.name);assert digest(pack)==digest(dest/pack.name)
write(ROOT/'DELIVERY_COMPLETE.json',dict(delivery_directory=str(dest),zip=str(dest/pack.name),
    file_CRC_and_hashes_passed=True,original_release_unchanged=True,physical_fit_verified=False,CFD_rerun=False))
print('FEMALE_PROTOTYPE_DELIVERED',json.dumps(dict(directory=str(dest),ZIP_bytes=pack.stat().st_size),ensure_ascii=True),flush=True)
