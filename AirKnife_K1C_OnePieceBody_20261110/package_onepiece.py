"""Read-back, print-plate illustration, and explicit non-destructive packaging."""
import csv,hashlib,json,zipfile
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager
from geometry import ROOT

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for p in ['cad/assembled_airpath_checks.json','cad/native_model_reopen.json','print/independent_readback_checks.json']:
        assert (ROOT/p).exists(),p
    integrity=json.loads((ROOT/'source_integrity.json').read_text())
    old=ROOT.parent/integrity['source_folder']
    assert all(sha(old/name)==digest for name,digest in integrity['source_files_sha256'].items())
    tm=trimesh.load_mesh(ROOT/'print/STL/body_onepiece_mm.stl',process=True)
    fontManager.addfont(r'C:\Windows\Fonts\msjh.ttc')
    plt.rcParams.update({'font.family':'Microsoft JhengHei','axes.unicode_minus':False})
    xy=tm.vertices[:,:2]+110;hull=ConvexHull(xy);outline=xy[hull.vertices]
    floor=xy[tm.vertices[:,2]<1e-5];floor=floor[ConvexHull(floor).vertices]
    fig,ax=plt.subplots(figsize=(8,8),layout='constrained')
    ax.add_patch(plt.Rectangle((0,0),220,220,fc='#f5f8fa',ec='#203c51',lw=2))
    ax.add_patch(plt.Rectangle((0,215),220,5,color='#bbb',alpha=.6))
    ax.fill(outline[:,0],outline[:,1],color='#9dc5d0',alpha=.6,label='全高度投影範圍')
    ax.fill(floor[:,0],floor[:,1],color='#43667e',alpha=.75,label='底層法蘭外形')
    bounds=np.array([xy.min(0),xy.max(0)])
    ax.add_patch(plt.Rectangle(bounds[0]-5,*(bounds[1]-bounds[0]+10),fill=False,ls='--',ec='#b16e18',label='投影包絡再外擴 5 mm'))
    ax.set(xlim=(-5,225),ylim=(-5,225),xlabel='平台 X (mm)',ylabel='平台 Y (mm)',
        title='K1C：單件本體旋轉 45° 後置中\n列印尺寸約 171.7 × 171.7 × 200 mm')
    ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='lower left',fontsize=10)
    fig.savefig(ROOT/'images/03_K1C_body_placement.png',dpi=170);plt.close(fig)
    with (ROOT/'五金清單.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['零件','數量','用途'])
        w.writerows([['M3 x 16 mm',4,'吹唇接本體'],['M3 x 30 mm',4,'吹唇兩半'],
            ['M3 六角螺母',8,'鎖固'],['原風機固定螺絲',12,'原配置沿用'],['2.8 x 6 mm 定位銷',4,'吹唇選用；本體無需']])
    files=[]
    for pat in ['*.py','*.md','*.csv','source_integrity.json','cad/*.json','cad/*.blend',
        'cad/reference/*.stl','print/**/*.stl','print/**/*.3mf','print/*.json','images/*.png']:
        files.extend(p for p in ROOT.glob(pat) if p.is_file())
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    manifest=''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
    (ROOT/'MANIFEST.sha256').write_text(manifest,encoding='utf-8');files.append(ROOT/'MANIFEST.sha256')
    dest=ROOT/'K1C_OnePieceBody_200mm_CompatibleLips_PrintPack.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for p in files:assert hashlib.sha256(z.read(p.relative_to(ROOT).as_posix())).hexdigest()==sha(p)
    report={'file':dest.name,'files':len(files),'size_bytes':dest.stat().st_size,'sha256':sha(dest),
        'zip_CRC_pass':True,'each_member_hash_matches_source':True,'original_files_unchanged':True,
        'physical_print_verified':False,'actual_slicing_verified':False}
    (ROOT/'package_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
