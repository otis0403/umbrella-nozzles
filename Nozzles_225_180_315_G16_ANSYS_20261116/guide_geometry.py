"""Two thin guide plates shared exactly between CAD and CFD."""
import numpy as np

from design import height, profile
from geometry import smooth, cosine, rect_grid, boundary


def limits(length):
    return 55., height(length)-56.


def section(z,width,length,nx=8,ny=12,nw=2,kind='ramp'):
    w,depth,radius=profile(max(0,z),width,length,kind)
    start,end=limits(length)
    t=float(smooth((z-start)/(end-start)))
    fraction=.23+(1/3-.23)*t
    thick=.8+.8*min(float(smooth((z-start)/15)),float(smooth((end-z)/15)))
    bounds=[-fraction-thick/w,-fraction+thick/w,fraction-thick/w,fraction+thick/w]
    v=np.r_[cosine(-1,bounds[0],ny),cosine(bounds[0],bounds[1],nw)[1:],
            cosine(bounds[1],bounds[2],ny)[1:],cosine(bounds[2],bounds[3],nw)[1:],
            cosine(bounds[3],1,ny)[1:]]
    u=cosine(-1,1,nx)
    grid=rect_grid(-depth/2,depth/2,-w/2,w/2,[radius]*4,nx,3*ny+2*nw,u_values=u,v_values=v)
    return grid,u,v


def plate_ring(z,width,length,index,nx=64,kind='ramp'):
    ny,nw=12,2
    grid,_,_=section(z,width,length,nx,ny,nw,kind)
    row=(ny if index==0 else 2*ny+nw)
    strip=grid[row:row+nw+1].copy()
    # Ends penetrate the housing wall for a connected printable solid.
    strip[:,0,0]-=1
    strip[:,-1,0]+=1
    xy=boundary(strip)
    return np.c_[xy,np.full(len(xy),z)]
