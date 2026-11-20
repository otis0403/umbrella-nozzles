"""Millimetres. Exact common geometry for printed solids and CFD blocks."""
import math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
WALL=2.4
HOLES=[{'x':2+dx,'y':y,'d':6.4 if abs(y)==51 and abs(dx)==50 else 4.4}
 for y,dx in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]]
PIPE_OD=50.;PIPE_ID=46.;INSERT=25.;SPAN=150.

def smooth(t):
    t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)

def cosine(a,b,n):return a+(b-a)*(1-np.cos(np.linspace(0,np.pi,n+1)))/2

def boundary(grid):
    return np.concatenate([grid[0,:],grid[1:,-1],grid[-1,-2::-1],grid[-2:0:-1,0]])

def signed_area(p):return .5*float(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))

def rect_grid(x0,x1,y0,y1,radii,nx=20,ny=28):
    u,v=np.meshgrid(cosine(-1,1,nx),cosine(-1,1,ny));x=u*(x1-x0)/2;y=v*(y1-y0)/2
    rho=np.maximum(abs(u),abs(v));safe=np.maximum(rho,1e-30);bx,by=abs(x)/safe,abs(y)/safe
    idx=np.where(v<0,np.where(u<0,0,1),np.where(u<0,3,2));r=np.asarray(radii)[idx]
    hx=(x1-x0)/2;hy=(y1-y0)/2;a=bx*bx+by*by;b=-2*(bx*(hx-r)+by*(hy-r));c=(hx-r)**2+(hy-r)**2-r*r
    lam=(-b+np.sqrt(np.maximum(0,b*b-4*a*c)))/np.maximum(2*a,1e-30)
    corner=(r>0)&(bx>hx-r)&(by>hy-r)
    factor=np.where(corner,1+(lam-1)*rho*rho,1)
    xy=np.stack([x*factor+(x0+x1)/2,y*factor+(y0+y1)/2],axis=-1)
    U=((u+1)/2)[:,:,None];V=((v+1)/2)[:,:,None]
    edges=(1-U)*xy[:,0:1]+U*xy[:,-1:]+(1-V)*xy[0:1,:]+V*xy[-1:,:]
    corners=(1-U)*(1-V)*xy[0,0]+U*(1-V)*xy[0,-1]+U*V*xy[-1,-1]+(1-U)*V*xy[-1,0]
    return edges-corners

def cross_grid(w,d,r,nx=20,ny=36):return rect_grid(-d/2,d/2,-w/2,w/2,[r]*4,nx,ny)

def rounded_rect(w,d,r,n=256):
    # Uniform parameter edge sampling; exact circle and rectangle junctions.
    return boundary(cross_grid(w,d,r,n//4,n//4)).tolist()

def nozzle_profile(z,gap=6.,length=120.):
    a0=math.pi*23**2;alpha=1-math.pi/4;start=25.;end=start+length;h=end+35+8
    if z<=start:return 46.,46.,23.
    if z<=end:
        w=46+104*float(smooth((z-start)/length));d=2*a0/(w+math.sqrt(w*w-4*alpha*a0));return w,d,d/2
    t=float(smooth((z-end)/35));d0=2*a0/(150+math.sqrt(150**2-4*alpha*a0));r=d0/2+(.8-d0/2)*t
    target=a0+(150*gap-(4-math.pi)*.8**2-a0)*t;d=(target+(4-math.pi)*r*r)/150
    return 150.,d,r

def nozzle_height(length=120.):return 25+length+35+8

def nozzle_wall(z,length=120.):return 2. if z<=25 or z>=nozzle_height(length)-8 else 2.4

def split_bounds(z):
    thick=.8+1.2*float(smooth((z-10)/20));return [(-41.,-14-thick/2),(-14+thick/2,14-thick/2),(14+thick/2,41.)]

def root_grid(k,z=30,nx=16,ny=28,offset=0.):
    x0,x1=split_bounds(z)[k];rr=[[3,0,0,3],[0,0,0,0],[0,3,3,0]][k]
    return rect_grid(x0-offset,x1+offset,-44-offset,44+offset,[r+offset for r in rr],nx,ny)

def port(k,height=120.):
    side=k-1;angle=math.radians(25*side);direction=np.array([math.sin(angle),0,math.cos(angle)])
    tip=np.array([60.*side,0,height if side==0 else height-12]);return tip-25*direction,direction

def branch_grid(k,t,height=120.,nx=16,ny=28,wall=0.,neck=46.):
    root=root_grid(k,30,nx,ny,wall);center0=np.array([(-28.,0.,28.)[k],0,30.]);local=root-center0[:2]
    endpoint,direction=port(k,height);rise=endpoint[2]-30
    p1=center0+np.array([0,0,.35*rise]);p2=endpoint-direction*.35*rise
    C=(1-t)**3*center0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*endpoint
    dC=3*(1-t)**2*(p1-center0)+6*(1-t)*t*(p2-p1)+3*t*t*(endpoint-p2);angle=math.atan2(dC[0],dC[2])
    radius=23.+wall
    circ=cross_grid(2*radius,2*radius,radius,nx,ny)
    q=float(smooth(t));xy=local*(1-q)+circ*q
    area0=signed_area(boundary(local));area1=signed_area(boundary(circ));target=area0+(area1-area0)*q
    xy*=math.sqrt(target/signed_area(boundary(xy)))
    if k==1 and neck<46:
        # Smooth compact throat near the end; ends still return to ID46.
        squeeze=(46-neck)/46*math.sin(math.pi*float(np.clip((t-.45)/.55,0,1)))**2
        xy*=1-squeeze
    out=np.empty((*xy.shape[:2],3));out[:,:,0]=C[0]+xy[:,:,0]*math.cos(angle);out[:,:,1]=xy[:,:,1];out[:,:,2]=C[2]-xy[:,:,0]*math.sin(angle)
    return out

def port_grid(k,s,height=120.,nx=16,ny=28,radius=23.):
    E,D=port(k,height);a=math.atan2(D[0],D[2]);xy=cross_grid(2*radius,2*radius,radius,nx,ny)
    out=np.zeros((*xy.shape[:2],3));out[:,:,0]=E[0]+s*D[0]+xy[:,:,0]*math.cos(a);out[:,:,1]=xy[:,:,1];out[:,:,2]=E[2]+s*D[2]-xy[:,:,0]*math.sin(a)
    return out
