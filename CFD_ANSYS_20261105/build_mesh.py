"""Conformal hex FLUID mesh, SI units; originals are read only.

ASCII Fluent face normals point into c0 per the Ansys mesh format manual.
The finite-thickness crossed vanes end at z=134 and 144 mm respectively.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = next((p for p in ROOT.parent.rglob('geometry.py') if
              '216x12mm_200mm_' in str(p.parent) and
              '\u7121\u6838\u5fc3_20261105' in str(p.parent)), ROOT/'source_geometry.py')
G = {}
exec(compile(SOURCE.read_text(encoding='utf-8-sig'), str(SOURCE), 'exec'), G)


def bands(width, thick, side, centre):
    # Cosine clustering resolves walls and both sides of each vane.
    f = (1 - np.cos(np.linspace(0, math.pi, side + 1))) / 2
    left = -width / 2 + (width - thick) / 2 * f
    mid = np.linspace(-thick / 2, thick / 2, centre + 1)
    right = thick / 2 + (width - thick) / 2 * f
    return np.r_[left[:-1], mid[:-1], right]


def main(level):
    su, sv, nc, dz = {'coarse': (24, 10, 2, 1.25),
                       'medium': (36, 14, 4, .8),
                       'fine': (40, 16, 6, .7)}[level]
    z = list(np.linspace(0, 200, round(200 / dz) + 1)) + [12, 188]
    for tip in (134., 144.):
        z.extend(tip + s * a for s in (-1, 1)
                 for a in (0, .025, .05, .1, .25, .5, 1, 2))
    z = np.array(sorted(set(round(x, 8) for x in z)))
    nu, nv, nz = 2 * su + nc, 2 * sv + nc, len(z) - 1
    coords = []
    for zz in z:
        w, d, r = G['section'](zz)
        tu = G['thickness'](min(zz, 134), 134)
        tv = G['thickness'](min(zz, 144), 144)
        uu, vv = np.meshgrid(bands(w, tu, su, nc), bands(d, tv, sv, nc))
        radial = np.maximum(abs(uu) / (w/2), abs(vv) / (d/2))
        safe = np.maximum(radial, 1e-30)
        bu, bv = abs(uu)/safe, abs(vv)/safe
        corner = (bu > w/2-r) & (bv > d/2-r) & (r > 1e-12)
        a = bu*bu + bv*bv
        b = -2*(bu*(w/2-r) + bv*(d/2-r))
        c = (w/2-r)**2 + (d/2-r)**2 - r*r
        lam = (-b + np.sqrt(np.maximum(0, b*b-4*a*c))) / np.maximum(2*a, 1e-30)
        blend = np.clip((radial-.85)/.15, 0, 1)
        blend = blend*blend*(3-2*blend)
        scale = np.where(corner, 1 + blend*(lam-1), 1.)
        coords.append(np.stack((-vv*scale, uu*scale, np.full_like(uu, zz)), axis=-1))
    pts = np.array(coords).reshape(-1, 3) / 1000
    pids = np.arange(len(pts)).reshape(nz+1, nv+1, nu+1)
    fluid = np.ones((nz, nv, nu), bool)
    for k in range(nz):
        zm = (z[k] + z[k+1])/2
        if zm < 134: fluid[k, :, su:su+nc] = False
        if zm < 144: fluid[k, sv:sv+nc, :] = False
    cid = np.zeros(fluid.shape, dtype=np.int32)
    ncell = int(fluid.sum())
    cid[fluid] = np.arange(1, ncell+1)
    k,j,i = np.nonzero(fluid)
    cells = np.stack([pids[k,j,i],pids[k,j,i+1],pids[k,j+1,i+1],pids[k,j+1,i],
                      pids[k+1,j,i],pids[k+1,j,i+1],pids[k+1,j+1,i+1],pids[k+1,j+1,i]], axis=1)
    used = np.unique(cells)
    remap = np.zeros(len(pts), np.int32)
    remap[used] = np.arange(1, len(used)+1)
    points = pts[used]
    cells = remap[cells]-1
    # Positive signed tetrahedral decomposition, diagonal 0--6.
    xyz = points[cells]
    volumes = np.zeros(ncell)
    min_tet = float('inf')
    for a,b,c in ((1,2,6),(2,3,6),(3,7,6),(7,4,6),(4,5,6),(5,1,6)):
        v = np.einsum('ij,ij->i', np.cross(xyz[:,a]-xyz[:,0],xyz[:,b]-xyz[:,0]),xyz[:,c]-xyz[:,0])/6
        min_tet = min(min_tet, float(v.min()))
        volumes += v
    assert min_tet > 0, min_tet
    assert len(points) < 1_000_000 and ncell < 1_000_000
    zones = {x: [] for x in range(3,9)}

    def face(nodes, lower, upper, wall):
        if lower == 0 and upper == 0: return
        ns = remap[np.array(nodes)]
        if lower:
            ns = ns[::-1]
            c0,c1 = lower,upper
        else:
            c0,c1 = upper,0
        zid = 3 if lower and upper else wall
        zones[zid].append((*ns,int(c0),int(c1)))

    for k in range(nz):
        for j in range(nv):
            for i in range(nu+1):
                face((pids[k,j,i],pids[k,j+1,i],pids[k+1,j+1,i],pids[k+1,j,i]),
                     cid[k,j,i-1] if i else 0,cid[k,j,i] if i<nu else 0,
                     6 if i in (0,nu) else 8)
    for k in range(nz):
        for j in range(nv+1):
            for i in range(nu):
                face((pids[k,j,i],pids[k+1,j,i],pids[k+1,j,i+1],pids[k,j,i+1]),
                     cid[k,j-1,i] if j else 0,cid[k,j,i] if j<nv else 0,
                     6 if j in (0,nv) else 7)
    for k in range(nz+1):
        for j in range(nv):
            for i in range(nu):
                zid = 4 if k==0 else 5 if k==nz else 8 if abs(z[k]-134)<1e-7 else 7
                face((pids[k,j,i],pids[k,j,i+1],pids[k,j+1,i+1],pids[k,j+1,i]),
                     cid[k-1,j,i] if k else 0,cid[k,j,i] if k<nz else 0,zid)
    zones = {key:np.array(val, dtype=np.int32) for key,val in zones.items()}
    nface = sum(len(val) for val in zones.values())
    out = ROOT / level
    out.mkdir(exist_ok=True)
    names = {3:('interior',2),4:('inlet',10),5:('outlet',5),
             6:('housing',3),7:('long_vane',3),8:('short_vane',3)}
    with (out/'nozzle.msh').open('w',encoding='ascii',newline='\n') as f:
        f.write('(0 "No-core nozzle fluid domain. Coordinates in metres.")\n(2 3)\n')
        f.write(f'(10 (0 1 {len(points):x} 0))\n(12 (0 1 {ncell:x} 0))\n(13 (0 1 {nface:x} 0))\n')
        f.write(f'(10 (1 1 {len(points):x} 1 3)(\n')
        np.savetxt(f,points,fmt='%.12g')
        f.write('))\n'+f'(12 (2 1 {ncell:x} 1 4))\n')
        first = 1
        for key,faces in zones.items():
            f.write(f'(13 ({key:x} {first:x} {first+len(faces)-1:x} {names[key][1]:x} 4)(\n')
            for row in faces:
                f.write(' '.join(format(int(x),'x') for x in row)+'\n')
            f.write('))\n')
            first += len(faces)
        f.write('(39 (2 fluid fluid)())\n')
        for key,(name,bc) in names.items():
            typ = {2:'interior',10:'velocity-inlet',5:'pressure-outlet',3:'wall'}[bc]
            f.write(f'(39 ({key:x} {typ} {name})())\n')
    summary = {'level':level,'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               'cells':ncell,'nodes':len(points),'faces':nface,'volume_m3':float(volumes.sum()),
               'min_tetra_volume_m3':min_tet,'bounds_m':[points.min(0).tolist(),points.max(0).tolist()],
               'zones':{names[key][0]:len(val) for key,val in zones.items()},'structured_dimensions':[nu,nv,nz]}
    for key,name in ((4,'inlet'),(5,'outlet')):
        vtx = points[zones[key][:,:4]-1]
        area = np.linalg.norm(np.cross(vtx[:,1]-vtx[:,0],vtx[:,2]-vtx[:,0]),axis=1)/2
        area += np.linalg.norm(np.cross(vtx[:,2]-vtx[:,0],vtx[:,3]-vtx[:,0]),axis=1)/2
        summary[name+'_area_m2'] = float(area.sum())
    sample = np.linspace(0,200,20001)
    exact_volume = float(np.trapezoid([G['net_area'](zz)['net_air_area_mm2'] for zz in sample],sample)*1e-9)
    summary['parametric_volume_m3'] = exact_volume
    summary['volume_error_pct'] = 100*(volumes.sum()/exact_volume-1)
    np.savez_compressed(out/'mesh_geometry.npz',points=points,cells=cells,centres=xyz.mean(1),
                        volumes=volumes,inlet_faces=zones[4][:,:4]-1,outlet_faces=zones[5][:,:4]-1)
    (out/'mesh_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('level',choices=['coarse','medium','fine'])
    main(parser.parse_args().level)
