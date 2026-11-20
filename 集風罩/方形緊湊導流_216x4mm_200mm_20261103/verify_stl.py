"""Independent triangle/edge/volume checks on the actual delivered STL files."""
from pathlib import Path
from collections import Counter
import struct,math,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
report=json.loads((HERE/'模型幾何檢查.json').read_text(encoding='utf-8'))
parts=[]
for part in report['parts']:
    path=HERE/part['file'];blob=path.read_bytes();n=struct.unpack_from('<I',blob,80)[0]
    assert len(blob)==84+50*n
    verts={};parents=[];sizes=[];edges=Counter();balance=Counter()
    lo=[math.inf]*3;hi=[-math.inf]*3;vol=0.;badfaces=0
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    def join(a,b):
        a,b=find(a),find(b)
        if a==b:return
        if sizes[a]<sizes[b]:a,b=b,a
        parents[b]=a;sizes[a]+=sizes[b]
    for row in struct.iter_unpack('<12fH',blob[84:]):
        xyz=[tuple(row[k:k+3]) for k in [3,6,9]];ids=[]
        for p in xyz:
            if p not in verts:verts[p]=len(parents);parents.append(len(parents));sizes.append(1)
            ids.append(verts[p])
            for k in range(3):lo[k]=min(lo[k],p[k]);hi[k]=max(hi[k],p[k])
        join(ids[0],ids[1]);join(ids[1],ids[2])
        a,b,c=xyz;u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        if len(set(ids))<3 or sum(x*x for x in cross)<1e-24:badfaces+=1
        vol+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for k in range(3):
            a0,b0=ids[k],ids[(k+1)%3];key=(min(a0,b0),max(a0,b0));edges[key]+=1;balance[key]+=1 if a0<b0 else -1
    badedges=sum(c!=2 for c in edges.values());badorient=sum(c!=0 for c in balance.values());components=len({find(i) for i in range(len(parents))})
    assert badedges==0 and badorient==0 and badfaces==0 and components==1,(path.name,badedges,badorient,badfaces,components)
    assert vol>1000 and abs(vol-part['mesh']['volume_mm3'])/vol<1e-5
    dims=[hi[k]-lo[k] for k in range(3)]
    assert all(abs(a-b)<.002 for a,b in zip(dims,[220,200,60])) and abs(lo[2])<.001
    digest=hashlib.sha256(blob).hexdigest();assert digest==part['sha256']
    parts.append({'file':path.name,'triangles':n,'vertices':len(verts),'edges_not_shared_twice':badedges,'inconsistent_edge_orientation':badorient,
        'degenerate_triangles':badfaces,'material_components':components,'signed_volume_mm3':vol,'size_mm':dims,'minimum_Z_mm':lo[2],'sha256':digest})
base=json.loads((HERE/'原始檔案保留紀錄.json').read_text(encoding='utf-8'))
changed=[]
for item in base['original_files']:
    p=ROOT/item['path']
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:changed.append(item['path'])
assert not changed,changed
out={'parts':parts,'existing_files_verified_unchanged':len(base['original_files']),'all_existing_files_unchanged':True,'physically_printed':False,'airflow_tested':False}
(HERE/'STL獨立重讀檢查.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=True))
