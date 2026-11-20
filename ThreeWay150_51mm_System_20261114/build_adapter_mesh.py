import json
import numpy as np
from geometry import ROOT,root_grid,rect_grid,split_bounds,branch_grid,port,port_grid,reference_branch_grid,reference_port,reference_port_grid
from meshlib import HexMesh

def build(name,height=120.,neck=46.,fine=False,reference=False):
    out=ROOT/'cfd'/name;out.mkdir(parents=True,exist_ok=True);m=HexMesh();nx,ny=(16,28) if fine else (12,24);nw=3 if fine else 2
    rootz=40 if reference else 30;shift=rootz-30
    dz=.75 if fine else 1.5;zs=np.unique(np.r_[np.arange(0,rootz,dz),10.+shift,rootz]);grids=[]
    for z in zs:
        rows=[];bounds=split_bounds(z-shift)
        for k in range(3):
            if k:
                x0=bounds[k-1][1];x1=bounds[k][0];wall=rect_grid(x0,x1,-44,44,[0]*4,nw,ny)
                rows.append(wall[:,1:])
            root=root_grid(k,z-shift,nx,ny);rows.append(root if k==0 else root[:,1:])
        xy=np.concatenate(rows,axis=1);grids.append(np.dstack([xy,np.full(xy.shape[:2],z)]))
    # Below the leading edges all five strips are fluid. Above them only the three channels are fluid.
    if fine:
        # Each canal uses an O-grid through the plenum and curved branch.
        for k in range(3):m.ogrid(np.array(grids)[:,:,k*(nx+nw):k*(nx+nw)+nx+1,:])
        below=np.array(grids)[zs<=10+shift+1e-8]
        for k in [0,1]:m.block(below[:,:,k*(nx+nw)+nx:k*(nx+nw)+nx+nw+1,:])
    else:
        for j in range(len(zs)-1):
            if zs[j+1]<=10+shift+1e-8:m.block(grids[j:j+2])
            else:
                for k in range(3):m.block(np.array(grids[j:j+2])[:,:,k*(nx+nw):k*(nx+nw)+nx+1,:])
    for k in range(3):
        E,D=reference_port(k) if reference else port(k,height);n=max(24,int((E[2]-rootz)/dz)+1)
        add=m.ogrid if fine else m.block
        add([reference_branch_grid(k,float(t),nx,ny) if reference else branch_grid(k,float(t),height,nx,ny,neck=neck) for t in np.linspace(0,1,n+1)])
        ss=np.unique(np.r_[np.linspace(0,25,round(25/dz)+1),np.linspace(25,33,round(8/dz)+1)])
        add([reference_port_grid(k,float(s),nx,ny) if reference else port_grid(k,float(s),height,nx,ny) for s in ss])
    endpoints=[reference_port(k) if reference else port(k,height) for k in range(3)]
    def classify(xyz,interior):
        if not interior and np.max(abs(xyz[:,2]))<1e-5:return 'inlet'
        for k,(E,D) in enumerate(endpoints):
            dist=(xyz-E)@D
            if interior and np.max(abs(dist-25))<1e-5:return f'load_{k}'
            if not interior and np.max(abs(dist-33))<1e-5:return f'outlet_{k}'
        return None
    return m.export(out/'nozzle.msh',classify,{'name':name,'type':'adapter','height_mm':height,'neck_mm':neck,'fine':fine,'reference_old_layout_ID46':reference,'inlet_area_m2':(82*88-(4-np.pi)*9)*1e-6,'external':False})

if __name__=='__main__':build('adapter_H120',120)
