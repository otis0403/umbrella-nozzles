"""Print solids and external screw joints share the CFD profile exactly."""
import argparse
import hashlib
import math
import json
import numpy as np
import trimesh
import manifold3d as manifold

from design import ROOT, FLOW, SOCKET, WALL, height, profile, write_json
from geometry import cross_grid, boundary, smooth
from cad_utils import loft, mesh, cylinder, box


def ring(width, depth, radius, z):
    xy = boundary(cross_grid(width, depth, radius, 64, 64))
    return np.c_[xy, np.full(len(xy), z)]


def full_nozzle(width, length, kind='quintic'):
    h = height(length)
    zs = np.unique(np.r_[np.linspace(0, h, round(h)+1), 25, 35, 25+length, h-8])
    outside = []
    for z in zs:
        if z <= 25:
            w = depth = SOCKET + 2*WALL
            radius = w/2
        else:
            w, depth, radius = profile(z, width, length, kind)
            wall = 2 + .4*float(smooth((h-z-8)/5))
            extra = (SOCKET-FLOW)*(1-float(smooth((z-25)/10)))
            w += 2*wall + extra
            depth += 2*wall + extra
            radius += wall + extra/2
        outside.append(ring(w, depth, radius, z))
    channel = loft([ring(*profile(z, width, length, kind), z) for z in np.r_[24.999, np.linspace(25, h, round(h)), h+.2]])
    socket = loft([ring(d, d, d/2, z) for z, d in [(-.2, SOCKET+1.2), (0, SOCKET+1.2), (1.2, SOCKET), (25, SOCKET)]])
    slots = box([-40, -1, -.2], [40, 1, 19]) + cylinder(2, 80, [0, 0, 19], axis='x', segments=64)
    return loft(outside) - (channel+socket) - slots


def flange(z0, z1, width, length, kind='quintic'):
    zs = np.linspace(z0, z1, 9)
    outer = loft([ring(w+2*WALL+20, d+2*WALL+20, r+WALL+10, z)
                  for z in zs for w, d, r in [profile(z, width, length, kind)]])
    inner = loft([ring(*profile(z, width, length, kind), z) for z in np.linspace(z0-.1, z1+.1, 11)])
    return outer-inner


def segment(solid, width, length, kind='quintic'):
    h = height(length)
    if width != 315 and h <= 250:
        return [('onepiece', solid)], {'joint_screws': []}
    cut = 145.0
    w, d, r = profile(cut, width, length, kind)
    lower = (solid ^ box([-500, -500, -1], [500, 500, cut])) + flange(cut-4, cut, width, length, kind)
    upper = (solid ^ box([-500, -500, cut], [500, 500, h+1])) + flange(cut, cut+4, width, length, kind)
    holes = None
    for x in [-d/2-WALL-5, d/2+WALL+5]:
        for y in [-.3*w, .3*w]:
            hole = cylinder(3.4, 16, [x, y, cut], segments=48)
            holes = hole if holes is None else holes+hole
    lower -= holes
    upper -= holes
    joints = [{'type': 'transverse flange', 'plane_Z_mm': cut, 'screws': '4 x M3x16 with nuts', 'holes_mm': 3.4}]
    if width != 315:
        return [('inlet', lower), ('outlet', upper)], {'joint_screws': joints}
    negative = upper ^ box([-500, -500, cut-.1], [500, 0, h+1])
    positive = upper ^ box([-500, 0, cut-.1], [500, 500, h+1])
    stations = list(np.arange(cut+24, h-24, 60))
    for z in stations:
        depths = [profile(v, width, length, kind)[1]/2+WALL for v in [z-4, z, z+4]]
        lo, hi = min(depths), max(depths)
        for sign in [-1, 1]:
            x0, x1 = sorted([sign*(lo-1.0), sign*(hi+9)])
            negative += box([x0, -8, z-4], [x1, 0, z+4])
            positive += box([x0, 0, z-4], [x1, 8, z+4])
            hole = cylinder(3.4, 20, [sign*(hi+4.5), 0, z], axis='y', segments=48)
            negative -= hole
            positive -= hole
    joints.append({'type': 'longitudinal seam', 'plane_Y_mm': 0, 'stations_Z_mm': stations,
                   'screws': f'{2*len(stations)} x M3x25 with nuts', 'holes_mm': 3.4})
    return [('inlet', lower), ('outlet_A', negative), ('outlet_B', positive)], {'joint_screws': joints}


def export_part(solid, name, yaw=0):
    assert len(solid.decompose()) == 1, name
    original = mesh(solid.simplify(.001))
    angle = math.radians(yaw)
    rotation = np.array([[math.cos(angle), -math.sin(angle), 0], [math.sin(angle), math.cos(angle), 0], [0, 0, 1.]])
    rotated = original.vertices@rotation.T
    shift = np.r_[rotated[:, :2].mean(0), rotated[:, 2].min()]
    original.vertices = rotated-shift
    target = ROOT/'print/STL'/(name+'_mm.stl')
    original.export(target)
    reread = trimesh.load_mesh(target, process=True)
    assert reread.is_watertight and reread.is_winding_consistent and reread.volume > 0
    assert len(reread.split(only_watertight=False)) == 1
    assert reread.area_faces.min() > 1e-10
    assert (reread.extents[:2]+10 <= 220).all() and reread.extents[2] <= 250, (name, reread.extents)
    matrix = np.eye(4)
    matrix[:3, :3] = rotation.T
    matrix[:3, 3] = rotation.T@shift
    return {'name': name, 'file': str(target), 'print_size_mm': reread.extents.tolist(),
            'assembly_from_print': matrix.tolist(), 'yaw_for_print_degrees': yaw,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'closed_single_solid': True,
            'volume_mm3': float(reread.volume), 'triangles': len(reread.faces), 'K1C_plus_5mm_brim_checked': True}


def build(width, length, kind='quintic', split_for_k1c=False):
    name = f'nozzle_W{width}_G16_L{length}_{kind}'
    solid = full_nozzle(width, length, kind)
    assert len(solid.decompose()) == 1
    full_folder = ROOT/'cad/full'
    full_folder.mkdir(parents=True, exist_ok=True)
    full = mesh(solid.simplify(.001))
    quantized = np.asarray(full.vertices, dtype=np.float32).astype(np.float64)
    rebuilt = manifold.Manifold(manifold.Mesh64(quantized, np.asarray(full.faces, dtype=np.uint64)))
    assert rebuilt.status() == manifold.Error.NoError
    full = mesh(rebuilt.simplify(.001))
    reference = full_folder/(name+'_mm.stl')
    full.export(reference)
    reread = trimesh.load_mesh(reference, process=True)
    assert reread.is_watertight and reread.is_winding_consistent and reread.volume > 0
    assert len(reread.split(only_watertight=False)) == 1
    if not split_for_k1c:
        result = {'width_mm': width, 'gap_mm': 16, 'transition_length_mm': length, 'height_mm': height(length),
                  'profile_kind': kind, 'full_reference_STL': str(reference), 'socket_ID_mm': 55.4,
                  'flow_ID_mm': 51, 'size_mm': reread.extents.tolist(), 'closed_single_solid': True,
                  'sha256': hashlib.sha256(reference.read_bytes()).hexdigest(), 'physical_fit_verified': False}
        write_json(ROOT/'cad'/(name+'_checks.json'), result)
        print('COMPLETE_NOZZLE_VERIFIED', json.dumps(result), flush=True)
        return result
    parts, joints = segment(solid, width, length, kind)
    output = [export_part(part, name+'_'+suffix, 45 if width==225 else 0) for suffix, part in parts]
    union = parts[0][1]
    for _, part in parts[1:]:
        union += part
    # All joint material lies outside the analytical flow cavity.
    h = height(length)
    channel = loft([ring(*profile(z, width, length, kind), z) for z in np.r_[24.999, np.linspace(25, h, round(h)), h+.2]])
    intrusion = (union ^ channel).volume()
    assert intrusion < 2, (name, intrusion)
    result = {'width_mm': width, 'gap_mm': 16, 'transition_length_mm': length, 'height_mm': h,
              'full_reference_STL': str(full_folder/(name+'_mm.stl')), 'socket_ID_mm': 55.4,
              'flow_ID_mm': 51, 'parts': output, 'nominal_joint_material_intrusion_mm3': intrusion,
              'screws': joints['joint_screws'], 'physical_fit_verified': False}
    write_json(ROOT/'cad'/(name+'_checks.json'), result)
    print('PRINT_PARTS_VERIFIED', json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('width', type=int)
    parser.add_argument('length', type=int)
    parser.add_argument('--profile', choices=['quintic', 'ramp'], default='quintic')
    parser.add_argument('--split-for-k1c', action='store_true')
    args = parser.parse_args()
    build(args.width, args.length, args.profile, args.split_for_k1c)
