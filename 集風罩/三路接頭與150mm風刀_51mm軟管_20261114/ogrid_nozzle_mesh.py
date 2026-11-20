"""O-grid hexahedra avoid collapsed corners in circle-to-slot passages."""
import numpy as np
from geometry import ROOT,nozzle_profile,cross_grid,cosine,signed_area,boundary
from meshlib import HexMesh
CURRENT_LENGTH=120.
CURRENT_SHOULDER=150.
CURRENT_PLENUM=None

def edges(g):return [g[0,:],g[:,-1],g[-1,::-1],g[::-1,0]]

def build(name,height,gap,external=False,fine=False,reach=250.,span=150.,body=25.):
    out=ROOT/'cfd'/name;out.mkdir(parents=True,exist_ok=True);m=HexMesh()
    nx,ny,nr=(16,28,12) if fine else (12,20,8)
    dz=1.25 if fine else 2.;zs=np.unique(np.r_[np.linspace(0,height,round(height/dz)+1),25,25+CURRENT_LENGTH,height-8,height])
    if external:zs=np.unique(np.r_[zs,height+np.linspace(0,reach,round(reach/2)+1),height+30,height+50,height+80])
    cores=[];airs=[[] for _ in range(4)];rims=[[] for _ in range(4)];ambients=[[] for _ in range(4)]
    for z in zs:
        w,d,r=nozzle_profile(min(z,height),gap,CURRENT_LENGTH,CURRENT_SHOULDER,CURRENT_PLENUM)
        core=cross_grid(.4*w,.4*d,0,nx,ny);air=cross_grid(w,d,r,nx,ny)
        outer=cross_grid(w+4,d+4,r+2,nx,ny);box=cross_grid(400,200,0,nx,ny)
        cores.append(np.dstack([core,np.full(core.shape[:2],z)]))
        for side,(a,b,c,e) in enumerate(zip(edges(core),edges(air),edges(outer),edges(box))):
            work=[(airs,a,b,cosine(0,1,nr))]
            if z>=height-1e-6:
                weights=1.45**np.arange(14 if fine else 10);radial=np.r_[0,np.cumsum(weights)]/weights.sum()
                work.extend([(rims,b,c,np.linspace(0,1,4)),(ambients,c,e,radial)])
            for rows,left,right,tt in work:
                xy=left[:,None,:]*(1-tt[None,:,None])+right[:,None,:]*tt[None,:,None]
                rows[side].append(np.dstack([xy,np.full(xy.shape[:2],z)]))
    m.block(cores)
    for rows in airs:m.block(rows)
    if external:
        for rows in rims+ambients:m.block(rows)
    def classify(xyz,interior):
        if interior:return None
        if np.max(abs(xyz[:,2]))<1e-5:return 'inlet'
        if np.max(abs(xyz[:,2]-zs[-1]))<1e-5:return 'outlet'
        if external:
            if np.max(abs(xyz[:,2]-height))<1e-5:
                return 'lip_rim' if abs(xyz.mean(0)[0])<=gap/2+2.01 and abs(xyz.mean(0)[1])<=77.01 else 'ambient'
            if np.max(abs(abs(xyz[:,0])-100))<1e-5 or np.max(abs(abs(xyz[:,1])-200))<1e-5:return 'ambient'
        return None
    inlet_area=abs(signed_area(boundary(cross_grid(46,46,23,nx,ny))))*1e-6
    return m.export(out/'nozzle.msh',classify,dict(name=name,height_mm=height,gap_mm=gap,span_mm=150.,body_height_mm=25.,lip_length_mm=height-25,
        profile_config={'length':CURRENT_LENGTH,'shoulder':CURRENT_SHOULDER,'plenum':CURRENT_PLENUM},external=external,fine=fine,inlet_area_m2=inlet_area,outlet_slot_area_m2=(150*gap-(4-np.pi)*.8**2)*1e-6,vane_count=0))

if __name__=='__main__':build('curve_g4_q1',188,4)
