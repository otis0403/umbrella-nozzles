import bpy, json, runpy, sys, itertools, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
script=ROOT/'integrate_latest.py'
sys.argv=[str(script),'--','verify']
lib=runpy.run_path(str(script),run_name='__main__')
report=json.loads((ROOT/'integration_checks.json').read_text(encoding='utf8'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
boxes={o.name:lib['bounds'](o) for o in meshes}
trees={}

def overlaps_box(a,b):
    return all(a[0][i]<b[1][i]-.0001 and b[0][i]<a[1][i]-.0001 for i in range(3))

def bvh(ob):
    if ob.name not in trees:
        trees[ob.name]=lib['tree'](ob)
    return trees[ob.name]

hoses=[o for o in meshes if o.name.startswith('外購導風管_')]
new_parts=[o for o in meshes if o.name.startswith(('三路分流接頭_','小型集風罩_'))]
others=[o for o in meshes if o.name not in {x.name for x in hoses+new_parts}]
collisions=[]
pairs=[]
for a,b in itertools.combinations(hoses,2):
    pairs.append((a,b))
for a in hoses:
    own=next(h for h in report['hoses'] if h['name']==a.name)
    side='右側' if '右側' in a.name else '左側'
    for b in new_parts+others:
        if b.name in [own['nozzle'],'三路分流接頭_'+side]:
            continue
        pairs.append((a,b))
for a in new_parts:
    for b in others:
        pairs.append((a,b))
for a,b in itertools.combinations(new_parts,2):
    pairs.append((a,b))
checked=0
for a,b in pairs:
    if overlaps_box(boxes[a.name],boxes[b.name]):
        hits=bvh(a).overlap(bvh(b))
        checked+=1
        if hits:
            collisions.append({'parts':[a.name,b.name],'triangle_pairs':len(hits)})
# Pipe ends intentionally seat on their own mating shoulders.
closed=[]
for ob in hoses:
    edges={}
    for face in ob.data.polygons:
        vertices=list(face.vertices)
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):
            key=tuple(sorted((a,b)))
            edges[key]=edges.get(key,0)+1
    assert all(v==2 for v in edges.values()),ob.name
    closed.append(ob.name)
result={'non_mating_part_pairs_considered':len(pairs),'broadphase_overlapping_pairs_tested':checked,
    'non_mating_surface_intersections':collisions,'six_hose_meshes_closed':len(closed)==6,
    'mating_pairs_excluded':'each hose and its own socket/spigot; 25 mm insertion at each end',
    'test_scope':'mesh-surface intersection; hardware and manufacturing tolerance require physical checks'}
(ROOT/'interference_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('ASSEMBLY_INTERFERENCE_CHECK',json.dumps(result,ensure_ascii=False),flush=True)
assert not collisions,'Interference requires correction'
# Adjust the preview framing and only the new-part appearance.
for ob in list(bpy.data.objects):
    if ob.name.startswith('整機預覽燈'):
        bpy.data.objects.remove(ob,do_unlink=True)
for name,color in [('新版三路接頭',(.035,.24,.29)),('新版150x16吹嘴',(.045,.29,.34)),
                   ('軟管_0',(.18,.38,.43)),('軟管_1',(.52,.32,.16)),('軟管_2',(.16,.4,.30))]:
    m=bpy.data.materials[name]
    m.diffuse_color=(*color,1)
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
lib['render_views']()
lib['verify']()
notes='''# 整機中央弧線配置整合

本版以完整模型為基礎，配置兩顆鼓風機、兩個中管口加高 10 mm 的三路接頭與六個 150×16 mm 外套式吹嘴。六個出口沿既有放傘弧面的中央線排列，左右對稱，出口高度約 709.87 mm。

## 開啟模型

開啟同資料夾「完整模型_中央弧線_三路51mm_150x16.blend」。整機外殼包絡為 1400×500×1250 mm。Blender 場景採公分座標，scale_length 為 0.01。

01 圖顯示整機背面。02 圖暫時隱藏外殼，呈現六個出口與夾傘機構的相對位置。

## 接管規格

每顆風機接三路。風機端採原 82×88 mm 入口與 12 孔法蘭。三路接頭管端外徑 50 mm、流道內徑 46 mm，插入軟管 25 mm。軟管內徑 51 mm，外徑以 54.6 mm 估算。吹嘴套口內徑 55.4 mm，軟管插入 25 mm。套口尺寸仍待實物試配。

## 軟管走向與長度

本版以平滑空心管表示實機安裝走向，軟管波紋、管夾及固定支架需要後續實機配置。左右對稱的三支路徑中心線長約為內側 333.28 mm、中間約 252 mm、外側 313.37 mm，已包含兩端各 25 mm 套接長度。各支路最小中心線轉彎半徑詳見 integration_checks.json。

以上是 CAD 走向的中心線量測，實際裁切長度待實機核對。先前 ANSYS 的 50/70、60/80、100/120 cm 管長比較採各自的測試假設。本次整機走向及外套式吹嘴尚待新的 CFD 與實測驗證。

## 核對紀錄

- 六個出口同高，左右三組鏡像定位誤差小於 0.01 mm。
- 61 點出口縫寬約 16 mm，出口淨長約 150 mm，套口內徑約 55.4 mm。
- 兩個三路接頭的原法蘭座標、入口尺寸與 12 個孔位通過核對。
- 新零件、軟管與外殼、風機、夾傘機構的非接合面網格交叉檢查通過。套接部位另依插入長度與口徑核對。
- 38 個其餘網格的幾何、座標變換與材質索引已比對，並以獨立 Blender 程序重新開啟模型驗證。
- 原始整機及兩份來源 STL 的雜湊檢查通過。

Blender 5.1.2 輸出本版。原整機檔使用較新的 5.2 格式，讀取時出現版本提示，以上網格比對及原生檔重開驗證均已完成。

尺寸與裝配檢查紀錄位於 integration_checks.json、interference_checks.json、native_reopen_checks.json。本次交付為整機裝配模型，氣密、管夾固定、實際管長、風場與吹乾效果仍待實機確認。

## 對應列印零件

- 三路接頭共 2 顆，使用本資料夾 print/STL/splitter_center_neck_plus10_mm.stl。中管口由原本 25 mm 長延長為 35 mm，軟管仍套入 25 mm；加高 10 mm 提供根部的軟管間隙。
- 外套式吹嘴共 6 顆，來源 ../Nozzle_FemaleSocket_51mm_150x16_20261114/print/STL/nozzle_150x16_female_ID55p4_H188_mm.stl。
- 套口試配圈先用 ../Nozzle_FemaleSocket_51mm_150x16_20261114/print/STL/fit_ring_ID55p4_mm.stl。

列印零件 STL 的尺寸單位為 mm，匯入比例 100%。
'''
(ROOT/'整合說明.md').write_text(notes,encoding='utf8')
files=['完整模型_中央弧線_三路51mm_150x16.blend','01_整機背面_最新三路配置.png','02_中央弧線_六吹口定位.png',
       'integration_checks.json','interference_checks.json','native_reopen_checks.json','splitter_revision_checks.json','print/STL/splitter_center_neck_plus10_mm.stl','整合說明.md']
manifest={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
(ROOT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('ASSEMBLY_FINALIZED_AND_VERIFIED',json.dumps({'files':len(files),'folder':str(ROOT)},ensure_ascii=False),flush=True)

