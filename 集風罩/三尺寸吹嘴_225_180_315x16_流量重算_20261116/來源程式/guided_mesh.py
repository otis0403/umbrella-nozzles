"""Resolved guide plate volumes, including their leading and trailing faces."""
import numpy as np
from pathlib import Path

from design import ROOT
from geometry import rect_grid,boundary,signed_area
from guide_geometry import section,limits
from nozzle_mesh import make_slices,edges
from meshlib import HexMesh


def build(name,width,length,external=False,fine=False,reach=250,profile_kind='ramp'):
    output=ROOT/'cfd'/name
    output.mkdir(parents=True,exist_ok=True)
    start,end=limits(length)
    h,slices=make_slices(width,length,external,False,reach,profile_kind,[start,start+15,end-15,end])
    nx,ny,nr=(10,16,8) if fine else (8,12,6)
    nw=2
    grids=[];local=[]
    for center,short,w,depth,radius,outside in slices:
        grid,u,v=section(center[2],width,length,nx,ny,nw,profile_kind)
        # The elbow uses circular local sections irrespective of its Z coordinate.
        if center[2]<=0:
            grid=rect_grid(-25.5,25.5,-25.5,25.5,[25.5]*4,nx,len(v)-1,u_values=u,v_values=v)
        grids.append(center+grid[...,0,None]*short+grid[...,1,None]*np.array([0.,1,0]))
        local.append((grid,u,v))
    grids=np.asarray(grids)
    mesh=HexMesh()
    for k in range(3):
        row=k*(ny+nw)
        mesh.ogrid(grids[:,row:row+ny+1],nr=nr)
    for interval in range(len(slices)-1):
        z=(slices[interval][0][2]+slices[interval+1][0][2])/2
        if start<z<end:
            continue
        for row in [ny,2*ny+nw]:
            mesh.block(grids[interval:interval+2,row:row+nw+1])
    if external:
        rim_rows=[[] for _ in range(4)]
        outer_rows=[[] for _ in range(4)]
        for item,(grid,u,v) in zip(slices,local):
            center,short,w,depth,radius,outside=item
            if not outside:continue
            rim=rect_grid(-(depth+4)/2,(depth+4)/2,-(w+4)/2,(w+4)/2,[radius+2]*4,nx,len(v)-1,u_values=u,v_values=v)
            box=rect_grid(-100,100,-(width+220)/2,(width+220)/2,[0]*4,nx,len(v)-1,u_values=u,v_values=v)
            def world(xy):
                return center+xy[...,0,None]*short+xy[...,1,None]*np.array([0.,1,0])
            for side,(a,b,c) in enumerate(zip(edges(grid),edges(rim),edges(box))):
                for rows,left,right,t in [(rim_rows,a,b,np.linspace(0,1,4)),
                    (outer_rows,b,c,np.r_[0,np.cumsum(1.4**np.arange(10))]/np.sum(1.4**np.arange(10)))]:
                    xy=left[:,None,:]*(1-t[None,:,None])+right[:,None,:]*t[None,:,None]
                    rows[side].append(world(xy))
        for rows in rim_rows+outer_rows:mesh.block(rows)
    def classify(xyz,interior):
        if interior:return None
        if np.max(abs(xyz[:,0]-100))<1e-5 and np.max(abs(xyz[:,2]+95))<26:return 'inlet'
        if np.max(abs(xyz[:,2]-(h+reach if external else h)))<1e-5:return 'outlet'
        if external:
            if np.max(abs(xyz[:,2]-h))<1e-5:
                return 'lip_rim' if abs(xyz.mean(0)[0])<=10.01 and abs(xyz.mean(0)[1])<=width/2+2.01 else 'ambient'
            if np.max(abs(abs(xyz[:,0])-100))<1e-5 or np.max(abs(abs(xyz[:,1])-(width+220)/2))<1e-5:return 'ambient'
        return None
    inlet_area=abs(signed_area(boundary(local[0][0])))*1e-6
    return mesh.export(output/'nozzle.msh',classify,{'name':name,'height_mm':h,'width_mm':width,'span_mm':width,
        'transition_length_mm':length,'profile_kind':profile_kind,'gap_mm':16,'external':external,'fine':fine,
        'feed_elbow_R_mm':90,'inlet_area_m2':inlet_area,'outlet_slot_area_m2':(width*16-(4-np.pi)*.8**2)*1e-6,
        'body_height_mm':25,'lip_length_mm':h-25,'reach_mm':reach if external else 0,
        'vane_count':2,'guide_nominal_thickness_mm':1.6,'guide_Z_mm':[start,end],'unpartitioned_outlet_length_mm':56})


if __name__=='__main__':
    build('guide_mesh_check',315,320)
