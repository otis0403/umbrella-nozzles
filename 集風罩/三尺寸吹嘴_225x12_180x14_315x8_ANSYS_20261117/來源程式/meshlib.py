"""Conformal multiblock hexahedra, native Fluent ASCII mesh (metres)."""
import json
from collections import defaultdict
import numpy as np
from geometry import ROOT,boundary,signed_area

class HexMesh:
    def __init__(self):self.nodes=[];self.lookup={};self.cells=[]
    def ogrid(self,grids,nr=12):
        """Rectangular core plus four radial blocks: no collapsed circle corners."""
        grids=np.asarray(grids);nz,ny,nx=grids.shape[:3];u=(1-np.cos(np.linspace(0,np.pi,nx)))/2;v=(1-np.cos(np.linspace(0,np.pi,ny)))/2
        U,V=np.meshgrid(u,v);U=U[:,:,None];V=V[:,:,None];cores=[];rings=[[] for _ in range(4)]
        tt=(1-np.cos(np.linspace(0,np.pi,nr+1)))/2
        for g in grids:
            corners=np.array([g[0,0],g[0,-1],g[-1,-1],g[-1,0]]);center=corners.mean(0);p=center+.6*(corners-center)
            core=(1-U)*(1-V)*p[0]+U*(1-V)*p[1]+U*V*p[2]+(1-U)*V*p[3];cores.append(core)
            outer=[g[0,:],g[:,-1],g[-1,::-1],g[::-1,0]];inner=[core[0,:],core[:,-1],core[-1,::-1],core[::-1,0]]
            for k,(a,b) in enumerate(zip(inner,outer)):rings[k].append(a[:,None,:]*(1-tt[None,:,None])+b[:,None,:]*tt[None,:,None])
        self.block(cores)
        for ring in rings:self.block(ring)
    def block(self,grids):
        grids=np.asarray(grids);ids=np.empty(grids.shape[:3],np.int32)
        for index in np.ndindex(ids.shape):
            p=grids[index];key=tuple(np.round(p,7));number=self.lookup.get(key)
            if number is None:number=len(self.nodes);self.nodes.append(p);self.lookup[key]=number
            ids[index]=number
        k,j,i=np.indices(np.array(ids.shape)-1)
        cell=np.stack([ids[k,j,i],ids[k,j,i+1],ids[k,j+1,i+1],ids[k,j+1,i],ids[k+1,j,i],ids[k+1,j,i+1],ids[k+1,j+1,i+1],ids[k+1,j+1,i]],axis=-1).reshape(-1,8)
        self.cells.extend(cell)
    def export(self,path,classify,metadata):
        pts=np.asarray(self.nodes)/1000;cells=np.asarray(self.cells);assert len(cells)<1e6 and len(pts)<1e6
        p=pts[cells];vol=np.zeros(len(cells));mintet=1
        for a,b,c in [(1,2,6),(2,3,6),(3,7,6),(7,4,6),(4,5,6),(5,1,6)]:
            tet=np.einsum('ij,ij->i',np.cross(p[:,a]-p[:,0],p[:,b]-p[:,0]),p[:,c]-p[:,0])/6
            mintet=min(mintet,float(tet.min()));vol+=tet
        assert mintet>0,('nonpositive_tetra',mintet)
        faces={}
        order=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        for cid,cell in enumerate(cells,1):
            for indices in order:
                face=tuple(int(cell[x]) for x in indices);key=tuple(sorted(face))
                if key in faces:faces[key][2]=cid
                else:faces[key]=[face,cid,0]
        zones=defaultdict(list)
        for face,c0,c1 in faces.values():
            xyz=pts[list(face)]*1000;name=classify(xyz,bool(c1))
            if c1 and name is None:name='interior'
            if not c1 and name is None:name='housing'
            # Fluent face normal points INTO c0, opposite the outward cell loops.
            zones[name].append((*[v+1 for v in reversed(face)],c0,c1))
        names=list(zones);nface=len(faces)
        with path.open('w',encoding='ascii') as f:
            f.write('(0 "Three-way and nozzle fluid mesh; coordinates metres")\n(2 3)\n')
            f.write(f'(10 (0 1 {len(pts):x} 0))\n(12 (0 1 {len(cells):x} 0))\n(13 (0 1 {nface:x} 0))\n')
            f.write(f'(10 (1 1 {len(pts):x} 1 3)(\n');np.savetxt(f,pts,fmt='%.12g');f.write('))\n')
            f.write(f'(12 (2 1 {len(cells):x} 1 4))\n');first=1
            for zid,name in enumerate(names,3):
                rows=zones[name];bc=2 if rows[0][-1] else 10 if name=='inlet' else 5 if name.startswith('outlet') or name=='ambient' else 3
                f.write(f'(13 ({zid:x} {first:x} {first+len(rows)-1:x} {bc:x} 4)(\n')
                for row in rows:f.write(' '.join(format(int(x),'x') for x in row)+'\n')
                f.write('))\n');first+=len(rows)
            f.write('(39 (2 fluid fluid)())\n')
            for zid,name in enumerate(names,3):
                typ='interior' if zones[name][0][-1] else 'velocity-inlet' if name=='inlet' else 'pressure-outlet' if name.startswith('outlet') or name=='ambient' else 'wall'
                # Section 39 uses decimal zone IDs; sections 10/12/13 use hex.
                f.write(f'(39 ({zid} {typ} {name})())\n')
        metadata.update(cells=len(cells),nodes=len(pts),minimum_tetra_volume_m3=mintet,volume_m3=float(vol.sum()),zones={n:len(v) for n,v in zones.items()},geometry_revision='20261114_open_ambient_v1')
        path.with_name('mesh_summary.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        print('MESH_READY',str(path.parent),len(cells),len(pts),flush=True)
        return metadata
