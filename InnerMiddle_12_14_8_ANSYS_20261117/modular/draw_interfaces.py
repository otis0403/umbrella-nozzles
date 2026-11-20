import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Circle,Rectangle
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'modular_checks.json').read_text())
font=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=11)
fig,axs=plt.subplots(3,1,figsize=(13,8),layout='constrained')
for ax,group,label in zip(axs,data['groups'],['內側','中間','外側']):
    w=group['width_mm'];g=group['preferred_gap_mm']
    for x,y in group['screw_centers_XY_mm']:
        ax.add_patch(Circle((y,x),7,color='#aacbd2'))
        y0,y1=sorted([12.4*(1 if x>0 else -1),x])
        ax.add_patch(Rectangle((y-7,y0),14,y1-y0,color='#aacbd2'))
    def rounded(width,depth,radius,color):
        ax.add_patch(FancyBboxPatch((-width/2,-depth/2),width,depth,boxstyle=f'round,pad=0,rounding_size={radius}',facecolor=color,edgecolor='#287080',linewidth=.5))
    rounded(w+4.8,26.8,5.4,'#aacbd2');rounded(w+3.6,25.6,4.8,'#d99555');rounded(w+1.2,23.2,3.6,'#aacbd2');rounded(w,22,3,'white')
    for i,(x,y) in enumerate(group['screw_centers_XY_mm']):
        if i in group['locator_indices']:ax.add_patch(Circle((y,x),3.7,facecolor='#287080',edgecolor='#144353',linewidth=.8))
        ax.add_patch(Circle((y,x),2.2,facecolor='white',edgecolor='#144353',linewidth=.6))
    ax.annotate('',xy=(-w/2,35),xytext=(w/2,35),arrowprops={'arrowstyle':'<->','color':'#224c63'})
    ax.text(0,38,f'共同流道淨寬 {w} mm',ha='center',fontproperties=font)
    ax.annotate('',xy=(w/2+14,-11),xytext=(w/2+14,11),arrowprops={'arrowstyle':'<->','color':'#224c63'})
    ax.text(w/2+17,0,'22',va='center',fontsize=10)
    ax.text(-w/2-8,-40,f'{label}：可換前嘴 {g} mm；{group["screw_count"]} × M4（通孔Ø4.4）',fontproperties=font)
    ax.set_xlim(-180,190);ax.set_ylim(-50,52);ax.set_aspect('equal');ax.axis('off')
fig.suptitle('可換接合面｜22 mm為本體接合高度；前端另收縮成12／14／8 mm',fontproperties=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=16))
fig.savefig(ROOT/'images/modular_interfaces.png',dpi=160)
print('MODULAR_INTERFACE_DRAWING_CREATED',flush=True)
