"""Dimensioned orthographic sections extracted from the final printable STL."""
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from geometry import ROOT


def draw_dimensions(geo):
    font = FontProperties(fname='C:/Windows/Fonts/msjh.ttc', size=10)
    parts = {p['group']: p for p in geo['parts']}
    meshes = {k: trimesh.load_mesh(ROOT/'cad/reference'/(p['name']+'.stl'), process=True)
              for k, p in parts.items() if k in ['adapter', 'nozzle']}
    fig, axes = plt.subplots(1, 3, figsize=(15, 7), layout='constrained')

    def section(ax, mesh, origin, normal, coordinates):
        cut = mesh.section(plane_origin=origin, plane_normal=normal)
        assert cut is not None
        for entity in cut.entities:
            path = entity.discrete(cut.vertices)
            ax.plot(path[:, coordinates[0]], path[:, coordinates[1]], color='#193441', lw=1)

    def dim(ax, a, b, label, text_offset=(0, 0)):
        ax.annotate('', xy=b, xytext=a, arrowprops=dict(arrowstyle='<->', color='#168998', lw=1))
        center = (np.asarray(a)+np.asarray(b))/2+text_offset
        rotation=90 if abs(a[0]-b[0])<1e-8 else 0
        ax.text(*center, label, ha='center', va='center', fontsize=10, color='#126b76', rotation=rotation,
                bbox=dict(facecolor='white', edgecolor='none', pad=1))

    ax = axes[0]
    section(ax, meshes['adapter'], [0, 0, 1.5], [0, 0, 1], (0, 1))
    dim(ax, (-57, -72), (61, -72), '118 mm')
    dim(ax, (-69, -60), (-69, 60), '120 mm', (-9, 0))
    dim(ax, (-41, -25), (41, -25), '82 mm')
    dim(ax, (0, -44), (0, 44), '88 mm', (0, 15))
    ax.text(0, 80, '原法蘭孔位保持：4 × Ø6.4、8 × Ø4.4 mm\n法蘭厚 3 mm；中心相對入口 X 偏移 +2 mm',
            ha='center', fontproperties=font)
    ax.set(xlim=(-88, 88), ylim=(-90, 100), xlabel='X (mm)', ylabel='Y (mm)')
    ax.set_title('接頭底部剖面：固定接口', fontproperties=font)

    h = parts['nozzle']['print_size_mm'][2]
    ax = axes[1]
    section(ax, meshes['nozzle'], [0, 0, h-.1], [0, 0, 1], (1, 0))
    dim(ax, (-75, -21), (75, -21), '150 mm')
    dim(ax, (89, -8), (89, 8), '16 mm', (13, 0))
    ax.text(0, 40, '出口淨尺寸 150 × 16 mm\n尺寸直接取自交付 STL；長邊沿 Y 方向',
            ha='center', fontproperties=font)
    ax.set(xlim=(-95, 125), ylim=(-85, 95), xlabel='Y (mm)', ylabel='X (mm)')
    ax.set_title('吹嘴出口剖面：16 mm 淨縫', fontproperties=font)

    ax = axes[2]
    section(ax, meshes['nozzle'], [0, 0, 0], [1, 0, 0], (1, 2))
    dim(ax, (91, 0), (91, h), f'{h:g} mm', (13, 0))
    dim(ax, (-38, 0), (-38, 25), '25 mm', (-17, 0))
    ax.text(0, -20, '插管端 Ø50 外徑／Ø46 內徑\n無中央核心；出口兩端同高', ha='center', fontproperties=font)
    ax.set(xlim=(-95, 125), ylim=(-40, max(h+15, 170)), xlabel='Y (mm)', ylabel='Z (mm)')
    ax.set_title('吹嘴中央剖面：單件直通', fontproperties=font)

    for ax in axes:
        ax.set_aspect('equal')
        ax.grid(alpha=.12)
    fig.suptitle('三路接頭與 150 × 16 mm 吹嘴｜CAD 尺寸核對（單位 mm）', fontproperties=font, fontsize=15)
    out = ROOT/'images/CAD_dimension_checks.png'
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


if __name__ == '__main__':
    draw_dimensions(json.loads((ROOT/'cad/geometry_checks.json').read_text(encoding='utf-8')))
