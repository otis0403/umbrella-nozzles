import json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'print_checks.json').read_text(encoding='utf-8-sig'))
plt.rcParams['font.family']='Microsoft JhengHei'
fig,axes=plt.subplots(1,3,figsize=(15,6),layout='constrained')
colors=['#124559','#33949f','#ef842c']
names=['1 入口段','2 導流段（含完整導流片）','3 可換前嘴（保留一體）']
for ax,row,color,name in zip(axes,data['parts'],colors,names):
    tri=trimesh.load_mesh(row['STL'],process=True)
    xy=tri.vertices[:,:2]+150;hull=ConvexHull(xy)
    ax.add_patch(Rectangle((0,0),300,300,facecolor='#f4f7f9',edgecolor='#617383',lw=2))
    bounds=np.array(row['placed_3MF_bounds_mm'])
    lo=bounds[0,:2]-8;size=np.array(row['print_size_mm'][:2])+16
    ax.add_patch(Rectangle(lo,*size,fill=False,ls='--',lw=1.5,edgecolor=color))
    ax.add_patch(Polygon(xy[hull.vertices],closed=True,facecolor=color,alpha=.7,edgecolor=color))
    ax.set(xlim=(-10,310),ylim=(-10,310),aspect='equal',xticks=[0,150,300],yticks=[0,150,300])
    ax.set_title(name,fontweight='bold',fontsize=13,pad=16)
    w,d,z=row['print_size_mm']
    ax.set_xlabel(f'X×Y：{w:.1f}×{d:.1f} mm\n高度：{z:.1f} mm｜Z 餘量：{300-z:.1f} mm',fontsize=12)
    ax.text(150,150,'45°',color='white',ha='center',va='center',fontsize=17,fontweight='bold')
fig.suptitle('K2 Pro 300×300 mm 平台｜每件分開列印',fontsize=19,fontweight='bold')
fig.supxlabel('色塊為實際模型的 XY 投影凸包；虛線為包絡外另預留每側 8 mm。這不是切片預覽，未產生裙邊或支撐。',fontsize=11)
fig.savefig(ROOT/'images/K2Pro_plate_fit.png',dpi=160)
print('PLATE_DIAGRAM_SAVED')
