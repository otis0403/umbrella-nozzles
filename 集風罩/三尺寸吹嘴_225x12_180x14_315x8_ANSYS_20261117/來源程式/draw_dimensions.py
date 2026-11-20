"""Dimension drawings use the shared millimetre CAD profile."""
import numpy as np
import json
import design
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from design import ROOT, height, profile, SOCKET, WALL
from geometry import smooth
from guide_geometry import plate_ring, limits

FONT=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=11)
plt.rcParams['axes.unicode_minus']=False
fig,axs=plt.subplots(1,3,figsize=(15,8),layout='constrained')
selection=json.loads((ROOT/'selection.json').read_text())
for ax,(key,label,width,length) in zip(axs,[('inner','內側',225,220),('center','中間',180,180),('outer','外側',315,320)]):
    design.GAP=selection[key]['gap_mm']
    h=height(length);z=np.unique(np.r_[np.linspace(0,h,1000),25,25+length,h-8])
    inside=np.array([profile(v,width,length,'ramp')[0] for v in z])
    outer=[]
    for v in z:
        if v<=25: outer.append(SOCKET+2*WALL)
        else:
            wall=2+.4*float(smooth((h-v-8)/5))
            extra=(SOCKET-51)*(1-float(smooth((v-25)/10)))
            outer.append(profile(v,width,length,'ramp')[0]+2*wall+extra)
    outer=np.array(outer)
    ax.fill(np.r_[-outer/2,outer[::-1]/2],np.r_[z,z[::-1]],color='#b4d7dc')
    ax.fill(np.r_[-inside/2,inside[::-1]/2],np.r_[z,z[::-1]],color='#f5fafb')
    for sign in [-1,1]:
        ax.plot(sign*outer/2,z,color='#207080',lw=1)
        ax.plot(sign*inside/2,z,color='#207080',lw=.8)
    if width==315:
        start,end=limits(length);zz=np.linspace(start,end,280)
        for k in range(2):
            rings=[plate_ring(v,width,length,k) for v in zz]
            centers=np.array([r[:,1].mean() for r in rings])
            ax.plot(centers,zz,color='#ba6928',lw=1.5)
        ax.text(0,205,'2 片導流片\n厚 1.6 mm',fontproperties=FONT,ha='center',color='#9b5420')
        ax.annotate('',xy=(145,h),xytext=(145,h-56),arrowprops={'arrowstyle':'<->','color':'#9b5420'})
        ax.text(139,h-28,'56',ha='right',va='center',color='#9b5420')
    ax.annotate('',xy=(-width/2,h+17),xytext=(width/2,h+17),arrowprops={'arrowstyle':'<->','color':'#224c63'})
    ax.text(0,h+22,f'淨寬 {width} mm',fontproperties=FONT,ha='center')
    xdim=-width/2-19
    ax.annotate('',xy=(xdim,0),xytext=(xdim,h),arrowprops={'arrowstyle':'<->','color':'#224c63'})
    ax.text(xdim-8,h/2,f'{h:.0f} mm',rotation=90,va='center',ha='center')
    ax.annotate('接管內徑 55.4\n插入深度 25 mm',xy=(0,12),xytext=(0,-50),
                fontproperties=FONT,ha='center',arrowprops={'arrowstyle':'->','color':'#333'})
    ax.set_title(f"{label} {width} × {selection[key]['gap_mm']} mm",fontproperties=FONT,pad=15)
    ax.set_xlim(-205,205);ax.set_ylim(-65,440);ax.set_aspect('equal');ax.axis('off')
fig.suptitle('三尺寸吹嘴｜俯視尺寸與內部導流配置（單位 mm）',fontproperties=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=19))
fig.savefig(ROOT/'images/three_nozzles_dimensions.png',dpi=150)
plt.close(fig)
print('DIMENSION_DRAWING_CREATED',flush=True)
