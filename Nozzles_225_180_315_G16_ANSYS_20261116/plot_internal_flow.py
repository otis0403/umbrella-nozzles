"""Plot actual exported Fluent cut faces, preserving wall/plate gaps."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.font_manager import FontProperties
from design import ROOT

font=FontProperties(fname='C:/Windows/Fonts/msjh.ttc',size=12)
fig,axs=plt.subplots(1,3,figsize=(12,7),layout='constrained')
for ax,(case,title,h) in zip(axs,[('ramp_w225_L220','內側 225 × 16 mm',288),
                                ('ramp_w180_L180','中間 180 × 16 mm',248),
                                ('guide_w315_L320','外側 315 × 16 mm',388)]):
    d=np.load(ROOT/'cfd'/case/'long_cut_fields.npz')
    verts=d['vertices'][:,[1,2]]*1000
    indices=d['indices'];offsets=d['offsets'];velocity=d['z-velocity']
    polygons=[verts[indices[i:j]] for i,j in zip(offsets[:-1],offsets[1:])]
    mask=np.array([p[:,1].min()>=24.99 for p in polygons])
    poly=PolyCollection([p for p,keep in zip(polygons,mask) if keep],array=velocity[mask],cmap='coolwarm',clim=(-3,16),edgecolors='none',rasterized=True)
    ax.add_collection(poly)
    ax.set(xlim=(-170,170),ylim=(20,400),aspect='equal')
    ax.set_title(title,fontproperties=font);ax.set_xlabel('長邊座標 Y（mm）',fontproperties=font)
    ax.set_ylabel('入口起算軸向距離 Z（mm）',fontproperties=font)
    ax.grid(alpha=.15);ax.set_facecolor('#eeeeee')
cb=fig.colorbar(poly,ax=axs,shrink=.8,pad=.02)
cb.set_label('軸向速度（m/s）；負值表示局部逆向',fontproperties=font)
fig.suptitle('ANSYS 本體內部截面｜三者各自指定名義出口平均風速 10 m/s，定常殘差未全達標',fontproperties=font)
fig.savefig(ROOT/'images/ANSYS_internal_axial_velocity.png',dpi=180)
plt.close(fig)
print('ACTUAL_FLUENT_INTERNAL_FACE_PLOT_CREATED',flush=True)
