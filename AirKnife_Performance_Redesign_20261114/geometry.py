"""Low-loss shape study, mm. Same 16 mm gap and 252 mm target clear span."""
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WALL=2.4
HOLES=[{'x':2+dx,'y':y,'d':6.4 if abs(y)==51 and abs(dx)==50 else 4.4}
    for y,dx in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]]
DESIGNS={
 'ref216':dict(kind='legacy',height=260,body=200,span=216,gap=16,mouth=20,power=1,land=0,body_wall=2.4),
 'ref252':dict(kind='legacy',height=320,body=200,span=252,gap=16,mouth=20,power=1,land=0,body_wall=2.4),
 'retro80':dict(kind='retrofit',height=280,body=200,span=252,gap=16,mouth=20,power=1,land=6,body_wall=2.4),
 'area200d22':dict(kind='area',height=260,body=200,span=252,gap=16,mouth=22,power=2,land=6,body_wall=3.),
 'area220d22':dict(kind='area',height=280,body=220,span=252,gap=16,mouth=22,power=2,land=6,body_wall=3.),
 'area200d24':dict(kind='area',height=260,body=200,span=252,gap=16,mouth=24,power=2,land=6,body_wall=3.)}
ACTIVE='area200d22'
def activate(name):
    global ACTIVE
    ACTIVE=name
def config():return DESIGNS[ACTIVE]
def smooth(t):
    t=max(0.,min(1.,t));return t**3*(10-15*t+6*t*t)
def ease(t):
    t=max(0.,min(1.,t));b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)
def section(z,height=None,gap=None,span=None,body=None):
    c=config();height=c['height'] if height is None else height;gap=c['gap'] if gap is None else gap
    span=c['span'] if span is None else span;body=c['body'] if body is None else body
    if z<=body:
        q=ease((z-12)/(body-12));r=3*(1-q)
        if c['kind']!='area':return 88+128*q,82-112*q+50*q*q,r
        w=88+(span-88)*q
        ai=82*88-(4-math.pi)*9;ae=span*c['mouth']
        a=ai+(ae-ai)*q**c['power'];d=(a+(4-math.pi)*r*r)/w
        return w,d,r
    t=smooth((z-body)/(height-body-c['land']))
    if c['kind']=='area':return span,c['mouth']+(gap-c['mouth'])*t,0.
    return 216+(span-216)*t,20+(gap-20)*t,0.
def area(z,height=None,gap=None,span=None,body=None):
    w,d,r=section(z,height,gap,span,body);return w*d-(4-math.pi)*r*r
def rounded_rect(w,d,r,n=256):
    pts=[]
    for j in range(n):
        a=2*math.pi*j/n;xx=math.cos(a);yy=math.sin(a);scale=max(abs(xx),abs(yy));x,y=(d/2)*xx/scale,(w/2)*yy/scale
        if r>0 and abs(x)>d/2-r and abs(y)>w/2-r:
            bx,by=abs(x),abs(y);aa=bx*bx+by*by;bb=-2*(bx*(d/2-r)+by*(w/2-r));cc=(d/2-r)**2+(w/2-r)**2-r*r
            lam=(-bb+math.sqrt(max(0,bb*bb-4*aa*cc)))/(2*aa);x*=lam;y*=lam
        pts.append((x,y))
    return pts
