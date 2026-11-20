"""Millimetres; X=slot gap, Y=clear span, Z=flow. Defaults match H320/W252."""
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WALL=2.4
SPAN=252.
BODY_HEIGHT=200.
HEIGHT=320.
GAP=12.
HOLES=[{'x':2+dx,'y':y,'d':6.4 if abs(y)==51 and abs(dx)==50 else 4.4}
       for y,dx in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),
                    (-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]]
def smooth(t):
    t=max(0.,min(1.,t));return t**3*(10-15*t+6*t*t)
def ease(t):
    t=max(0.,min(1.,t));b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)
def section(z,height=HEIGHT,gap=GAP,span=SPAN,body=BODY_HEIGHT):
    if z<=body:
        q=ease((z-12)/(body-12))
        return 88+128*q,82-112*q+50*q*q,3*(1-q)
    t=smooth((z-body)/(height-body))
    return 216+(span-216)*t,20+(gap-20)*t,0.
def area(z,height=HEIGHT,gap=GAP,span=SPAN,body=BODY_HEIGHT):
    w,d,r=section(z,height,gap,span,body)
    return w*d-(4-math.pi)*r*r
def rounded_rect(w,d,r,n=256):
    pts=[]
    for j in range(n):
        a=2*math.pi*j/n;xx=math.cos(a);yy=math.sin(a)
        scale=max(abs(xx),abs(yy));x,y=(d/2)*xx/scale,(w/2)*yy/scale
        if r>0 and abs(x)>d/2-r and abs(y)>w/2-r:
            bx,by=abs(x),abs(y);aa=bx*bx+by*by
            bb=-2*(bx*(d/2-r)+by*(w/2-r));cc=(d/2-r)**2+(w/2-r)**2-r*r
            lam=(-bb+math.sqrt(max(0,bb*bb-4*aa*cc)))/(2*aa);x*=lam;y*=lam
        pts.append((x,y))
    return pts
