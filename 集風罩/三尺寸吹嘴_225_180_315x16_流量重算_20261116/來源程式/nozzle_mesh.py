"""O-grid mesh of the R90 feed elbow and the new nozzle, optionally with a jet."""
import math
import numpy as np

from design import ROOT, profile, height
from geometry import cross_grid, cosine, boundary, signed_area
from meshlib import HexMesh


def edges(grid):
    return [grid[0, :], grid[:, -1], grid[-1, ::-1], grid[::-1, 0]]


def make_slices(width,length,external=False,fine=False,reach=250,profile_kind='quintic',extra_stations=()):
    dz = 1.6 if fine else 2.4
    h = height(length)
    slices = []
    # Nozzle coordinates use +Z as the exit direction. The feed elbow turns
    # from -X to +Z, matching the installed vertical-to-horizontal connection.
    for x in np.linspace(100, 90, max(6, round(10 / dz) + 1)):
        slices.append((np.array([x, 0, -95.]), np.array([0., 0, 1]), 51., 51., 25.5, False))
    for angle in np.linspace(0, math.pi/2, max(60, round(90*math.pi/2/dz)) + 1)[1:]:
        center = np.array([90*(1-math.sin(angle)), 0, -5-90*math.cos(angle)])
        short = np.array([math.sin(angle), 0, math.cos(angle)])
        slices.append((center, short, 51., 51., 25.5, False))
    for z in np.linspace(-5, 0, 4)[1:]:
        slices.append((np.array([0., 0, z]), np.array([1., 0, 0]), 51., 51., 25.5, False))
    zs = np.unique(np.r_[np.linspace(0, h, round(h/dz)+1), 25, 25+length, h-8, h, extra_stations])
    for z in zs[1:]:
        w, depth, radius = profile(z, width, length, profile_kind)
        slices.append((np.array([0., 0, z]), np.array([1., 0, 0]), w, depth, radius, z >= h-1e-6))
    if external:
        for z in np.unique(np.r_[h+np.linspace(0, reach, round(reach/2.4)+1), h+30, h+50, h+80])[1:]:
            slices.append((np.array([0., 0, z]), np.array([1., 0, 0]), *profile(h, width, length, profile_kind), True))
    return h,slices


def build(name, width, length, external=False, fine=False, reach=250, profile_kind='quintic'):
    output = ROOT / 'cfd' / name
    output.mkdir(parents=True, exist_ok=True)
    mesh = HexMesh()
    nx, ny, nr = (16, 36, 10) if fine else (12, 28, 8)
    h,slices=make_slices(width,length,external,fine,reach,profile_kind)
    cores = []
    air = [[] for _ in range(4)]
    rims = [[] for _ in range(4)]
    ambient = [[] for _ in range(4)]
    box_width = width + 220
    box_depth = 200
    for center, short, w, depth, radius, outside in slices:
        core = cross_grid(.4*w, .4*depth, 0, nx, ny)
        wall = cross_grid(w, depth, radius, nx, ny)
        rim = cross_grid(w+4, depth+4, radius+2, nx, ny)
        far = cross_grid(box_width, box_depth, 0, nx, ny)
        def world(xy):
            return center + xy[..., 0, None]*short + xy[..., 1, None]*np.array([0., 1, 0])
        cores.append(world(core))
        for side, (a, b, c, d) in enumerate(zip(edges(core), edges(wall), edges(rim), edges(far))):
            blocks = [(air, a, b, cosine(0, 1, nr))]
            if external and outside:
                weights = 1.4**np.arange(12 if fine else 10)
                grading = np.r_[0, np.cumsum(weights)]/weights.sum()
                blocks.extend([(rims, b, c, np.linspace(0, 1, 4)), (ambient, c, d, grading)])
            for rows, left, right, t in blocks:
                xy = left[:, None, :]*(1-t[None, :, None]) + right[:, None, :]*t[None, :, None]
                rows[side].append(world(xy))
    mesh.block(cores)
    for rows in air:
        mesh.block(rows)
    if external:
        for rows in rims + ambient:
            mesh.block(rows)
    def classify(xyz, interior):
        if interior:
            return None
        if np.max(abs(xyz[:, 0]-100)) < 1e-5 and np.max(abs(xyz[:, 2]+95)) < 26:
            return 'inlet'
        if np.max(abs(xyz[:, 2]-(h+reach if external else h))) < 1e-5:
            return 'outlet'
        if external:
            if np.max(abs(xyz[:, 2]-h)) < 1e-5:
                return 'lip_rim' if abs(xyz.mean(0)[0]) <= 10.01 and abs(xyz.mean(0)[1]) <= width/2+2.01 else 'ambient'
            if np.max(abs(abs(xyz[:, 0])-box_depth/2)) < 1e-5 or np.max(abs(abs(xyz[:, 1])-box_width/2)) < 1e-5:
                return 'ambient'
        return None
    area = abs(signed_area(boundary(cross_grid(51, 51, 25.5, nx, ny))))*1e-6
    return mesh.export(output/'nozzle.msh', classify, {
        'name': name, 'height_mm': h, 'width_mm': width, 'span_mm': width,
        'transition_length_mm': length, 'profile_kind': profile_kind, 'gap_mm': 16, 'external': external,
        'fine': fine, 'feed_elbow_R_mm': 90, 'inlet_area_m2': area,
        'outlet_slot_area_m2': (width*16-(4-np.pi)*.8**2)*1e-6,
        'reach_mm': reach if external else 0, 'inlet_normal': [-1, 0, 0],
        'body_height_mm': 25, 'lip_length_mm': h-25,
    })


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('width', type=float)
    parser.add_argument('length', type=float)
    parser.add_argument('--external', action='store_true')
    parser.add_argument('--fine', action='store_true')
    args = parser.parse_args()
    build(args.name, args.width, args.length, args.external, args.fine)
