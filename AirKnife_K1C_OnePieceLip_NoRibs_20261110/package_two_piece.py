"""Explicit handoff pack for the two printed components; no original writes."""
import csv,hashlib,json,zipfile
import numpy as np
import trimesh
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager
from geometry import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for f in ['cad/assembled_airpath_checks.json','cad/native_model_reopen.json',
              'cad/insertion_checks.json','print/independent_readback_checks.json']:
        assert (ROOT/f).exists(),f
    original=json.loads((ROOT/'source_integrity.json').read_text())
    source=ROOT.parent/original['source_folder']
    assert all(sha(source/name)==digest for name,digest in original['source_files_sha256'].items())
    fontManager.addfont(r'C:\Windows\Fonts\msjh.ttc')
    plt.rcParams.update({'font.family':'Microsoft JhengHei','axes.unicode_minus':False})
    fig,axs=plt.subplots(1,2,figsize=(13,7),layout='constrained')
    for ax,name,label in zip(axs,['body_onepiece','lip_16mm_onepiece_no_ribs'],['本體：171.7×171.7×200 mm','一體吹嘴：179.0×179.0×66 mm']):
        tm=trimesh.load_mesh(ROOT/'print/STL'/(name+'_mm.stl'),process=True)
        xy=tm.vertices[:,:2]+110;outline=xy[ConvexHull(xy).vertices]
        lo=xy.min(0)-5;dims=xy.max(0)-xy.min(0)+10
        ax.add_patch(plt.Rectangle((0,0),220,220,fc='#f4f7fa',ec='#234459',lw=2))
        ax.add_patch(plt.Rectangle((0,215),220,5,color='#bbb',alpha=.4))
        ax.fill(outline[:,0],outline[:,1],color='#4e9eaf',alpha=.65)
        ax.add_patch(plt.Rectangle(lo,*dims,fill=False,ls='--',ec='#b17827'))
        ax.set(xlim=(-5,225),ylim=(-5,225),xlabel='平台 X (mm)',ylabel='平台 Y (mm)',title=label)
        ax.set_aspect('equal');ax.grid(alpha=.15)
    fig.suptitle('K1C 分開兩盤列印｜兩件皆已旋轉 45°\n色塊為全高度投影，虛線為投影包絡再外擴 5 mm；並非切片結果',fontsize=15)
    fig.savefig(ROOT/'images/03_K1C_placement.png',dpi=160);plt.close(fig)
    with (ROOT/'五金清單.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['零件','數量','用途'])
        w.writerows([['M3 x 16 mm 螺絲',4,'吹嘴接本體'],['M3 六角螺母',4,'本體耳座'],
            ['M3 墊片',4,'選用；確認螺紋咬合'],['原風機固定螺絲',12,'依原配置沿用']])
    files=[]
    for pat in ['*.py','*.md','*.csv','source_integrity.json','cad/*.json','cad/*.blend',
        'cad/reference/*.stl','print/**/*.stl','print/**/*.3mf','print/*.json','images/*.png']:
        files.extend(p for p in ROOT.glob(pat) if p.is_file())
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    (ROOT/'MANIFEST.sha256').write_text(''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files),encoding='utf-8')
    files.append(ROOT/'MANIFEST.sha256');dest=ROOT/'K1C_TwoPiece_AirKnife_NoRibs_PrintPack.zip'
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
