"""Independently read the exported STL; do not execute the Blender generator."""
from pathlib import Path
from collections import Counter
import struct,math,json,hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
STL=HERE/'直通吹嘴_216x4mm_中央鴨嘴導流_單件_mm.stl'
blob=STL.read_bytes();n=struct.unpack_from('<I',blob,80)[0]
assert len(blob)==84+50*n
vertices={};parents=[];sizes=[];edge_counts=Counter();edge_balance=Counter()
low=[math.inf]*3;high=[-math.inf]*3;volume=0.0;collapsed=0;minimum_double_area=math.inf

def find(i):
    while parents[i]!=i:
        parents[i]=parents[parents[i]];i=parents[i]
    return i

def union(a,b):
    a,b=find(a),find(b)
    if a==b:return
    if sizes[a]<sizes[b]:a,b=b,a
    parents[b]=a;sizes[a]+=sizes[b]

for j,values in enumerate(struct.iter_unpack('<12fH',blob[84:])):
    xyz=[tuple(values[k:k+3]) for k in [3,6,9]];ids=[]
    for p in xyz:
        if p not in vertices:
            vertices[p]=len(parents);parents.append(len(parents));sizes.append(1)
        ids.append(vertices[p])
        for k in range(3):low[k]=min(low[k],p[k]);high[k]=max(high[k],p[k])
    union(ids[0],ids[1]);union(ids[1],ids[2])
    a,b,c=xyz;u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    double_area=math.sqrt(sum(c*c for c in cross));minimum_double_area=min(minimum_double_area,double_area)
    if len(set(ids))<3 or double_area<1e-12:collapsed+=1
    volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    for k in range(3):
        a0,b0=ids[k],ids[(k+1)%3];key=(min(a0,b0),max(a0,b0))
        edge_counts[key]+=1;edge_balance[key]+=1 if a0<b0 else -1

bad_edges=sum(count!=2 for count in edge_counts.values())
bad_orientations=sum(balance!=0 for balance in edge_balance.values())
components=len({find(i) for i in range(len(parents))})
dimensions=[high[k]-low[k] for k in range(3)]
assert bad_edges==0 and bad_orientations==0 and collapsed==0 and components==1
assert volume>1000 and all(abs(a-b)<.002 for a,b in zip(dimensions,[220,120,240]))
assert abs(low[2])<.001
build=json.loads((HERE/'尺寸與列印幾何檢查.json').read_text(encoding='utf-8'))
assert abs(volume-build['mesh']['volume_mm3'])/volume<1e-5
baseline=json.loads((HERE/'原始檔案保留紀錄.json').read_text(encoding='utf-8'))
changed=[]
for item in baseline['original_files']:
    p=ROOT/item['path']
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:changed.append(item['path'])
assert not changed,changed
report={'file':STL.name,'units':'mm','triangles':n,'vertices':len(vertices),
        'coordinate_edges_not_shared_twice':bad_edges,'inconsistent_oriented_edges':bad_orientations,
        'degenerate_triangles':collapsed,'material_components':components,'signed_volume_mm3':volume,
        'bounds_mm':[low,high],'size_mm':dimensions,'minimum_triangle_double_area_mm2':minimum_double_area,
        'grounded_at_Z0':True,'original_files_verified_unchanged':len(baseline['original_files']),
        'sha256':hashlib.sha256(blob).hexdigest(),'physical_print_tested':False}
(HERE/'STL獨立重讀檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
